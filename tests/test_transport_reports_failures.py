"""The transport says what went wrong, and says it where the caller chose.

`stream.py` is where a frame is read off a socket in pieces and where a
length-driven read decides how many more bytes to wait for. Every failure
there was raised as a `ModbusError` carrying a formatted message, and nothing
else: no log line, and no link to the exception that caused it. A short read, a
checksum mismatch and a peer that goes away mid-frame all reached the caller as
the same sentence with the original traceback discarded.

Two properties are pinned here, and they fail independently.

The cause travels with the error. `raise X(...) from e` is what puts the
socket error underneath the transport error, so a handler three frames up can
still see what the operating system said. Without it the chain stops at the
message, and the message is a string someone wrote.

The logger is the caller's. A library that installs a handler decides where
its host's output goes, so the module's own logger carries a null handler and
writes nothing until an application asks for it. The simulators construct a
stdout logger instead, because an application is what they are; that split is
the point, so the silence of the default is asserted rather than assumed.
"""

import logging
import subprocess  # nosec B404
import sys
import unittest

from pyomb.errors import ModbusNetworkError
from pyomb.stream import ModbusTcpStream

# A frame with a recognisable payload, so a test can assert the bytes did not
# reach a log line rather than trusting that nobody wrote them there.
FRAME = b"\x00\x00\x00\x00\x00\x04\x01\xde\xad\xbe"

PAYLOAD_MARKERS = ("dead", "beef", "\\xde", "de ad")

REFUSED = "connection refused by the peer"


class ExplodingSocket:
    """A socket double whose every send fails the way a dead peer does."""

    def __init__(self):
        self.attempts = 0

    def setsockopt(self, *args):
        """Accept the burst-mode option without applying it."""

    def send(self, data):
        """Fail the way a peer that has gone away fails.

        Args:
            data (bytes) : The fragment the transport tried to write

        Raises:
            OSError : Always, carrying a recognisable reason
        """

        self.attempts += 1

        raise OSError(REFUSED)

    def close(self):
        """Accept the teardown without doing anything."""


class QuietSocket:
    """A socket double that accepts every write and reports it sent."""

    def __init__(self):
        self.sent = []

    def setsockopt(self, *args):
        """Accept the burst-mode option without applying it."""

    def send(self, data):
        """Accept one fragment.

        Args:
            data (bytes) : The fragment written

        Returns:
            int : The number of bytes accepted
        """

        self.sent.append(data)

        return len(data)

    def close(self):
        """Accept the teardown without doing anything."""


class Recorder(logging.Handler):
    """A handler that keeps the records rather than rendering them."""

    def __init__(self):
        super().__init__()

        self.records = []

    def emit(self, record):
        """Keep one record.

        Args:
            record (logging.LogRecord) : The record being emitted
        """

        self.records.append(record)

    def messages(self):
        """Render every record kept so far.

        Returns:
            list[str] : One formatted message per record, in arrival order
        """

        return [record.getMessage() for record in self.records]

    def at(self, level):
        """Render the records emitted at one level.

        Args:
            level (int) : The logging level to select

        Returns:
            list[str] : The formatted messages at that level
        """

        return [r.getMessage() for r in self.records if r.levelno == level]


def recording_logger():
    """Build a logger that keeps its records and reaches nothing else.

    Returns:
        tuple[logging.Logger, Recorder] : The logger and its handler
    """

    handler = Recorder()

    # A unique name per call, so one test's records cannot reach another's.
    logger = logging.getLogger(f"pyomb.test.{id(handler)}")
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)

    # Nothing propagates to the root, whose handlers belong to whoever is
    # running the suite.
    logger.propagate = False

    return logger, handler


class TheCauseTravelsWithTheError(unittest.TestCase):
    """Pins the chain from the transport error back to what caused it."""

    def test_a_failed_send_carries_the_socket_error_underneath(self):
        stream = ModbusTcpStream(sock=ExplodingSocket())

        with self.assertRaises(ModbusNetworkError) as raised:
            stream.send(FRAME)

        self.assertIsInstance(raised.exception.__cause__, OSError)
        self.assertIn(REFUSED, str(raised.exception.__cause__))

    def test_the_transport_error_still_says_what_happened(self):
        # The chain is added, not substituted: the message a caller already
        # handled has to keep working.
        stream = ModbusTcpStream(sock=ExplodingSocket())

        with self.assertRaises(ModbusNetworkError) as raised:
            stream.send(FRAME)

        self.assertIn(REFUSED, str(raised.exception))


class TheLoggerIsTheCallers(unittest.TestCase):
    """Pins where the transport's output goes, and what reaches it."""

    def test_an_injected_logger_receives_the_failure(self):
        logger, handler = recording_logger()
        stream = ModbusTcpStream(sock=ExplodingSocket(), log=logger)

        with self.assertRaises(ModbusNetworkError):
            stream.send(FRAME)

        self.assertEqual(len(handler.at(logging.WARNING)), 1, handler.messages())
        self.assertIn(REFUSED, handler.at(logging.WARNING)[0])

    def test_a_fragment_boundary_is_debug_and_never_a_warning(self):
        # Routine progress must not compete with a real failure at the default
        # level, or the level stops carrying information. This needs a socket
        # that accepts: the failing one raises on the first write, so the
        # boundary line is never reached and an assertion against it would
        # pass over an empty list.
        logger, handler = recording_logger()
        stream = ModbusTcpStream(sock=QuietSocket(), log=logger, frag_size=4)

        stream.send(FRAME)

        self.assertNotEqual(handler.at(logging.DEBUG), [], handler.messages())
        self.assertEqual(handler.at(logging.WARNING), [], handler.messages())

    def test_a_failure_is_one_warning_and_not_a_debug_line(self):
        logger, handler = recording_logger()
        stream = ModbusTcpStream(sock=ExplodingSocket(), log=logger, frag_size=4)

        with self.assertRaises(ModbusNetworkError):
            stream.send(FRAME)

        self.assertEqual(len(handler.at(logging.WARNING)), 1, handler.messages())

        for message in handler.at(logging.DEBUG):
            self.assertNotIn("failed", message)

    def test_no_frame_byte_reaches_a_log_line(self):
        # The transport carries a peer's data. A byte count is diagnostic; the
        # bytes are the peer's and do not belong in an operator's log.
        logger, handler = recording_logger()
        stream = ModbusTcpStream(sock=ExplodingSocket(), log=logger, frag_size=4)

        with self.assertRaises(ModbusNetworkError):
            stream.send(FRAME)

        rendered = " ".join(handler.messages()).lower()

        for marker in PAYLOAD_MARKERS:
            self.assertNotIn(marker.lower(), rendered, rendered)

    def test_the_default_logger_writes_nothing(self):
        # Run in a fresh interpreter, because in this one the assertion cannot
        # fail. With no handler anywhere, logging's last-resort handler writes
        # a warning to stderr, and the null handler is what stops it -- but
        # the test runner installs a root handler of its own, so last resort
        # never fires here and the check passes whether or not the library
        # attached anything. Only an interpreter the runner has not touched
        # can tell the two apart.
        program = (
            "import sys\n"
            "from pyomb.stream import ModbusTcpStream\n"
            "class Dead:\n"
            "    def setsockopt(self, *a):\n"
            "        pass\n"
            "    def send(self, data):\n"
            "        raise OSError('gone')\n"
            "try:\n"
            "    ModbusTcpStream(sock=Dead()).send(b'\\x00' * 8)\n"
            "except Exception:\n"
            "    pass\n"
        )

        # The argument vector is a list holding this process's own interpreter
        # and a literal built above, so nothing reaches a shell and no caller
        # input is in it. The checks match on call shape and see neither.
        completed = subprocess.run(  # nosec B603
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(completed.stderr, "", completed.stderr)
        self.assertEqual(completed.stdout, "", completed.stdout)


if __name__ == "__main__":
    unittest.main()
