"""The transport says what went wrong, and says it where the caller chose.

Every failure in `stream.py` was raised as a `ModbusError` carrying a
formatted message and nothing else: no log line, and no link to the exception
that caused it. A short read, a checksum mismatch and a peer going away
mid-frame all reached the caller as the same sentence.

Two properties are pinned here and they fail independently. The cause travels
with the error, through `raise X(...) from e`, so a handler three frames up
still sees what the operating system said. And the logger is the caller's: the
module's own carries a null handler, where the simulators construct a stdout
logger because an application is what they are.
"""

import logging
import subprocess  # nosec B404
import sys
import unittest

from pyomb.errors import ModbusNetworkError
from pyomb.transport import ModbusTcpStream

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
        # level. A socket that accepts, or the boundary line is never reached.
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
        # A fresh interpreter: the runner installs a root handler, so logging's
        # last resort never fires here and the check would pass either way.
        program = (
            "import sys\n"
            "from pyomb.transport import ModbusTcpStream\n"
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

        # The argument vector is a list holding this interpreter and a literal,
        # so nothing reaches a shell. The checks match on call shape only.
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
