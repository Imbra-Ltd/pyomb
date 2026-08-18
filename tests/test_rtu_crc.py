"""The RTU checksum has to be computed, ordered and verified.

Three defects hid behind each other here. serialize() packed the 0xFFFF
initialisation value because nothing called calc_crc(); it packed the result
big-endian where RTU sends the checksum low byte first; and deserialize()
stored whatever checksum arrived without ever comparing it to the payload.
The first two cancelled out against this library's own deserialiser, so frames
round-tripped cleanly and were rejected by every real device. These tests pin
the wire bytes against published vectors, which no self-consistent pair of
bugs can satisfy.
"""

import unittest

from pyomb.errors import ModbusPacketError
from pyomb.packets import ModbusPduParser
from pyomb.packets import ModbusRequestFC1, ModbusRequestFC3
from pyomb.packets import ModbusResponseFC1, ModbusResponseFC4
from pyomb.packets import ModbusRtuRequest, ModbusRtuResponse
from pyomb.packets import calc_crc16


class TestCrcAlgorithm(unittest.TestCase):
    def test_matches_published_vectors(self):
        # CRC-16/MODBUS check values, as printed by crccalc.com and by the
        # reference implementation in the Modbus over Serial Line specification.
        vectors = (
            (b"", 0xFFFF),
            (b"\x01\x03\x00\x00\x00\x01", 0x0A84),
            (b"\x01\x04\x02\xff\xff", 0x80B8),
            (b"\x11\x03\x00\x00\x00\x02", 0x9BC6),
        )

        for payload, expected in vectors:
            self.assertEqual(calc_crc16(payload), expected, "mismatch for {0}".format(payload.hex()))


class TestRtuRequestFraming(unittest.TestCase):
    def setUp(self):
        self.saved_registry = dict(ModbusPduParser.get_registry())
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusRequestFC3)

    def tearDown(self):
        ModbusPduParser.set_registry(self.saved_registry)

    def test_serialize_computes_the_checksum(self):
        # Previously emitted the 0xFFFF initialisation value.
        request = ModbusRtuRequest(slave_id=17, pdu=ModbusRequestFC3(start_addr=0, quantity=2))

        self.assertEqual(request.serialize(), b"\x11\x03\x00\x00\x00\x02\xc6\x9b")

    def test_checksum_is_sent_low_byte_first(self):
        # The published tail for 01 03 00 00 00 01 is 84 0A, not 0A 84.
        request = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC3(start_addr=0, quantity=1))

        self.assertEqual(request.serialize()[-2:], b"\x84\x0a")

    def test_serialize_overrides_an_assigned_checksum(self):
        # set_crc() describes a frame, it does not get to contradict one.
        request = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))
        request.set_crc(0xDEAD)

        self.assertEqual(request.serialize()[-2:], b"\xec\x0b")
        self.assertEqual(request.crc, 0x0BEC)

    def test_deserialize_rejects_a_corrupt_frame(self):
        # Previously stored 0xDEAD and returned the packet regardless.
        corrupt = b"\x01\x01\x00\x01\x00\x02\xad\xde"

        with self.assertRaises(ModbusPacketError):
            ModbusRtuRequest.deserialize(corrupt)

    def test_deserialize_can_be_told_to_skip_the_check(self):
        corrupt = b"\x01\x01\x00\x01\x00\x02\xad\xde"

        request = ModbusRtuRequest.deserialize(corrupt, verify_crc=False)

        self.assertEqual(request.crc, 0xDEAD)
        self.assertEqual(request.pdu.start_addr, 1)

    def test_deserialize_rejects_a_frame_too_short_to_hold_a_checksum(self):
        with self.assertRaises(ModbusPacketError):
            ModbusRtuRequest.deserialize(b"\x01\x01\x00")

    def test_round_trip(self):
        request = ModbusRtuRequest(slave_id=9, pdu=ModbusRequestFC1(start_addr=4, quantity=8))

        self.assertEqual(ModbusRtuRequest.deserialize(request.serialize()), request)


class TestRtuResponseFraming(unittest.TestCase):
    def setUp(self):
        self.saved_registry = dict(ModbusPduParser.get_registry())
        ModbusPduParser.register(ModbusResponseFC1)
        ModbusPduParser.register(ModbusResponseFC4)

    def tearDown(self):
        ModbusPduParser.set_registry(self.saved_registry)

    def test_checksum_is_sent_low_byte_first(self):
        # The published tail for 01 04 02 FF FF is B8 80, not 80 B8.
        response = ModbusRtuResponse(slave_id=1, pdu=ModbusResponseFC4(byte_count=2, values=(0xFFFF,)))

        self.assertEqual(response.serialize(), b"\x01\x04\x02\xff\xff\xb8\x80")

    def test_deserialize_rejects_a_corrupt_frame(self):
        corrupt = b"\x01\x01\x02\x01\x02\xad\xde"

        with self.assertRaises(ModbusPacketError):
            ModbusRtuResponse.deserialize(corrupt)

    def test_deserialize_can_be_told_to_skip_the_check(self):
        corrupt = b"\x01\x01\x02\x01\x02\xad\xde"

        response = ModbusRtuResponse.deserialize(corrupt, verify_crc=False)

        self.assertEqual(response.crc, 0xDEAD)
        self.assertEqual(response.pdu.output_status, (1, 2))

    def test_round_trip(self):
        response = ModbusRtuResponse(slave_id=9, pdu=ModbusResponseFC1(byte_count=2, output_status=(3, 4)))

        self.assertEqual(ModbusRtuResponse.deserialize(response.serialize()), response)


if __name__ == "__main__":
    unittest.main()
