"""An error the transport did not cause is not re-labeled as one it did.

Every broad `except Exception` in stream.py used to catch anything -- a
framing fault this module already raised, a caller's own mistake, a real
socket failure -- and wrap all three in the same generic ModbusError. A
caller catching for the specific defect saw a network error instead, and a
genuine bug here or in a caller was reported as if the peer had misbehaved.

Each class below pins one of the two properties for one call site: an error
this module already typed keeps that type, and an error nothing here expects
is not caught at all.
"""

import unittest

from pyomb.adu import ModbusHeader, ModbusTcpPacket
from pyomb.errors import ModbusNetworkError, ModbusPacketError
from pyomb.pdu import ModbusPdu
from pyomb.transport import ModbusTcpReceiver, ModbusTcpSender, ModbusTcpStream
from tests.helpers.stub_socket import StubSocket


class _ExplodingSocket:
    """A socket double whose every operation raises one prepared error."""

    def __init__(self, error):
        self.error = error

    def setsockopt(self, *args):
        """Accept the burst-mode option without applying it."""

    def send(self, data):
        """Raise the prepared error instead of writing.

        Args:
            data (bytes) : The fragment the transport tried to write

        Raises:
            Exception : Whatever error the test prepared
        """
        raise self.error

    def recv(self, count):
        """Raise the prepared error instead of reading.

        Args:
            count (int) : The number of bytes requested

        Raises:
            Exception : Whatever error the test prepared
        """
        raise self.error

    def close(self):
        """Accept the teardown without doing anything."""


class _ExplodingStream:
    """A stream double whose send/receive raise one prepared error.

    Stands in for `ModbusTcpStream` so a sender or receiver test can raise a
    specific, already-typed error without driving a real socket failure.
    """

    def __init__(self, error):
        self.error = error
        self.frag_size = 0
        self.frag_delay = 0

    def send(self, message):
        """Raise the prepared error instead of sending."""
        raise self.error

    def receive(self):
        """Raise the prepared error instead of receiving."""
        raise self.error


def _one_packet():
    """A single, minimal request packet a sender can serialize.

    Returns:
        ModbusTcpPacket : A read-coils request for unit 1
    """
    return ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=1, data=(0, 1, 0, 1)))


class TheStreamDoesNotRelabelAFramingFault(unittest.TestCase):
    """send() must not flatten a ModbusPacketError into a network error."""

    def test_a_non_bytes_message_raises_packet_error_not_network_error(self):
        """The fragmenter's own ModbusPacketError must reach the caller unchanged."""
        stream = ModbusTcpStream(sock=StubSocket(), frag_size=4)

        with self.assertRaises(ModbusPacketError):
            stream.send(None)


class AnUnexpectedSocketBugIsNotDisguised(unittest.TestCase):
    """send() and receive() must let an error neither of them expects through."""

    def test_send_does_not_catch_an_unrelated_bug(self):
        stream = ModbusTcpStream(sock=_ExplodingSocket(TypeError("wrong type")))

        with self.assertRaises(TypeError):
            stream.send(b"\x00" * 8)

    def test_receive_does_not_catch_an_unrelated_bug(self):
        stream = ModbusTcpStream(sock=_ExplodingSocket(TypeError("wrong type")))

        with self.assertRaises(TypeError):
            stream.receive()

    def test_send_still_wraps_a_real_socket_error(self):
        """The narrowing must not lose the case it exists to handle."""
        stream = ModbusTcpStream(sock=_ExplodingSocket(OSError("connection refused")))

        with self.assertRaises(ModbusNetworkError):
            stream.send(b"\x00" * 8)


class TheSenderPreservesTheStreamsOwnErrorType(unittest.TestCase):
    """run_once() must not flatten every stream failure to ModbusNetworkError."""

    def test_a_packet_error_from_the_stream_keeps_its_type(self):
        sender = ModbusTcpSender(sock=StubSocket(), packets=[_one_packet()])
        sender.stream = _ExplodingStream(ModbusPacketError("bad frame"))

        with self.assertRaises(ModbusPacketError):
            sender.run_once()

    def test_an_unrelated_bug_is_not_disguised_as_a_network_error(self):
        sender = ModbusTcpSender(sock=StubSocket(), packets=[_one_packet()])
        sender.stream = _ExplodingStream(TypeError("wrong type"))

        with self.assertRaises(TypeError):
            sender.run_once()


class TheReceiverPreservesTheStreamsOwnErrorType(unittest.TestCase):
    """run_once() must not flatten every stream failure to a bare ModbusBaseError."""

    def test_a_network_error_from_the_stream_keeps_its_type(self):
        receiver = ModbusTcpReceiver(sock=StubSocket())
        receiver.stream = _ExplodingStream(ModbusNetworkError(message="peer gone"))

        with self.assertRaises(ModbusNetworkError):
            receiver.run_once()

    def test_an_unrelated_bug_is_not_disguised_as_a_modbus_error(self):
        receiver = ModbusTcpReceiver(sock=StubSocket())
        receiver.stream = _ExplodingStream(TypeError("wrong type"))

        with self.assertRaises(TypeError):
            receiver.run_once()


if __name__ == "__main__":
    unittest.main()
