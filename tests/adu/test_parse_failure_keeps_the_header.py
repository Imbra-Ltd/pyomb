"""A PDU that will not parse must not cost the caller the header that did.

ModbusTcpRequest.deserialize read the header, checked the MBAP length and
parsed the PDU inside one try, so all three failures reached the caller as the
same ModbusPacketError. A server holding one of those cannot tell a frame it
could answer from a frame it can only drop, and the peer that sent a bad PDU
met a closed socket rather than an exception response.

The split is what these tests pin: a failure behind a header that parsed
raises ModbusPduParseError carrying that header and the function code, and
every failure that leaves nothing to echo keeps raising the plain error.
"""

import unittest

from pyomb.adu import ModbusHeader, ModbusTcpRequest
from pyomb.errors import ModbusPacketError, ModbusPduParseError

# Transaction 1, protocol 0, length 4, unit 1, then an FC1 body two bytes
# short. The MBAP length agrees with the ADU, so only the PDU is malformed.
SHORT_FC1_REQUEST = bytes.fromhex("000100000004") + bytes([1]) + bytes([1, 0, 0])

# The same header with a length field that claims a longer ADU than arrived.
# The frame boundary is then unknown, so nothing after the header is usable.
LYING_LENGTH_REQUEST = bytes.fromhex("000100000009") + bytes([1]) + bytes([1, 0, 0])

# A header and nothing else. Length 1 counts the unit identifier alone, so the
# ADU is the seven bytes that arrived and only the PDU is missing.
HEADERLESS_PDU_REQUEST = bytes.fromhex("000100000001") + bytes([1])

# Four bytes cannot hold the seven-byte MBAP header.
TRUNCATED_HEADER = bytes.fromhex("00010000")


class AParsableHeaderSurvivesTheFailure(unittest.TestCase):
    """The case a caller can answer: the header read, the PDU did not."""

    def test_a_short_pdu_raises_the_answerable_error(self):
        with self.assertRaises(ModbusPduParseError):
            ModbusTcpRequest.deserialize(SHORT_FC1_REQUEST)

    def test_the_error_carries_the_header_to_echo(self):
        with self.assertRaises(ModbusPduParseError) as caught:
            ModbusTcpRequest.deserialize(SHORT_FC1_REQUEST)

        header = caught.exception.header

        self.assertEqual(header.trans_id, 1)
        self.assertEqual(header.prot_id, 0)
        self.assertEqual(header.unit_id, 1)

    def test_the_error_carries_the_function_code_the_request_named(self):
        # The first PDU byte survives whatever made the rest unreadable, and
        # it is what the exception response has to name.
        with self.assertRaises(ModbusPduParseError) as caught:
            ModbusTcpRequest.deserialize(SHORT_FC1_REQUEST)

        self.assertEqual(caught.exception.fc, 1)

    def test_the_answerable_error_is_still_a_packet_error(self):
        # A caller written before the split catches ModbusPacketError and must
        # keep catching this one.
        with self.assertRaises(ModbusPacketError):
            ModbusTcpRequest.deserialize(SHORT_FC1_REQUEST)


class NothingToEchoRaisesThePlainError(unittest.TestCase):
    """The cases a caller can only drop on.

    Each of these leaves no header worth echoing -- either it never parsed, or
    it parsed and disagrees with the bytes that arrived, which puts the frame
    boundary in doubt and desynchronizes the stream.
    """

    def test_a_truncated_header_is_not_answerable(self):
        with self.assertRaises(ModbusPacketError) as caught:
            ModbusTcpRequest.deserialize(TRUNCATED_HEADER)

        self.assertNotIsInstance(caught.exception, ModbusPduParseError)

    def test_a_length_field_contradicting_the_adu_is_not_answerable(self):
        with self.assertRaises(ModbusPacketError) as caught:
            ModbusTcpRequest.deserialize(LYING_LENGTH_REQUEST)

        self.assertNotIsInstance(caught.exception, ModbusPduParseError)

    def test_an_absent_pdu_names_no_function_code(self):
        # The function code is the first PDU byte. With no PDU there is none,
        # so there is nothing for an exception response to name.
        with self.assertRaises(ModbusPacketError) as caught:
            ModbusTcpRequest.deserialize(HEADERLESS_PDU_REQUEST)

        self.assertNotIsInstance(caught.exception, ModbusPduParseError)


class AWellFormedRequestIsUnaffected(unittest.TestCase):
    """The control. Without it the tests above pass against a deserialize
    that raises on everything."""

    def test_a_well_formed_request_still_parses(self):
        stream = bytes.fromhex("000100000006") + bytes([1]) + bytes([1, 0, 0, 0, 8])

        request = ModbusTcpRequest.deserialize(stream)

        self.assertEqual(request.header.trans_id, 1)
        self.assertEqual(request.pdu.fc, 1)

    def test_the_header_size_is_what_the_split_reads(self):
        # The split slices the stream at ModbusHeader.SIZE. A change there
        # would move both halves without failing anything above.
        self.assertEqual(ModbusHeader.SIZE, 7)


if __name__ == "__main__":
    unittest.main()
