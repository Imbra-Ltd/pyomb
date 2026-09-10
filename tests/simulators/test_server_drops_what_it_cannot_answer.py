"""The other half of the answer-or-drop split, driven without a socket.

The server answers a frame whose MBAP header parsed and whose PDU did not, and
drops one where nothing survived to echo. Proving the second over a socket
does not work: the transport waits for all seven header bytes before it reads
anything else, so a peer sending fewer never reaches on_data. An earlier
version of this drove a four-byte send over a real socket, passed on Windows
where the client's own close retired the peer first, and failed on Linux.

The fault is injected against a connection double instead. What a peer can
genuinely deliver is a length field contradicting the ADU.
"""

import unittest

from pyomb.errors import ModbusPacketError, ModbusPduParseError
from pyomb.simulators.server_simulator import ModbusServerSimulator

# Length 9 against three PDU bytes: the field claims six more than arrived, so
# the frame boundary is unknown and nothing after the header is trustworthy.
LYING_LENGTH_REQUEST = bytes.fromhex("000100000009") + bytes([1]) + bytes([1, 0, 0])

# The same header telling the truth, with an FC1 body two bytes short. The
# header is intact, so this one earns an answer.
SHORT_FC1_REQUEST = bytes.fromhex("000100000004") + bytes([1]) + bytes([1, 0, 0])


class RecordingConnection:
    """Stands in for a client socket and keeps what the server wrote."""

    def __init__(self):
        self.sent = []

    def send(self, data):
        """Record one write and report it as fully sent.

        Args:
            data (bytes) : The bytes the server is sending

        Returns:
            int : The number of bytes accepted
        """

        self.sent.append(data)

        return len(data)


class TheServerDropsWhatItCannotEcho(unittest.TestCase):
    """A frame with no trustworthy header leaves on_data by raising.

    The read loop catches that and retires the connection. These assert the
    raise, which is the part on_data decides; the retiring is the loop's and is
    covered where the loop is exercised.
    """

    def setUp(self):
        # No listener thread: on_data is called directly.
        self.server = ModbusServerSimulator()
        self.conn = RecordingConnection()

    def test_a_length_field_contradicting_the_adu_raises(self):
        with self.assertRaises(ModbusPacketError):
            self.server.on_data(LYING_LENGTH_REQUEST, self.conn)

    def test_it_is_not_the_answerable_error(self):
        # The distinction the split exists for. Raising the subclass here
        # would have the server answer on a header it cannot trust.
        with self.assertRaises(ModbusPacketError) as caught:
            self.server.on_data(LYING_LENGTH_REQUEST, self.conn)

        self.assertNotIsInstance(caught.exception, ModbusPduParseError)

    def test_nothing_is_written_back(self):
        with self.assertRaises(ModbusPacketError):
            self.server.on_data(LYING_LENGTH_REQUEST, self.conn)

        self.assertEqual(self.conn.sent, [])


class TheServerAnswersWhatItCanEcho(unittest.TestCase):
    """The control. Without it both assertions above pass against an on_data
    that raises on every frame."""

    def setUp(self):
        self.server = ModbusServerSimulator()
        self.conn = RecordingConnection()

    def test_a_short_pdu_is_answered_rather_than_raised(self):
        self.server.on_data(SHORT_FC1_REQUEST, self.conn)

        self.assertEqual(len(self.conn.sent), 1)

    def test_the_answer_is_the_exception_response(self):
        self.server.on_data(SHORT_FC1_REQUEST, self.conn)

        # Function code 1 with the error mask, then illegal data value.
        self.assertEqual(self.conn.sent[0][-2:], bytes([0x81, 0x03]))


if __name__ == "__main__":
    unittest.main()
