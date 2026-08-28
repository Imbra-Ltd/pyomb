import unittest

from pyomb.packets import ModbusHeader


class TestModbusHeader(unittest.TestCase):
    def test_initialization(self):
        header = ModbusHeader(trans_id=1, prot_id=2, length=3, unit_id=4)
        self.assertEqual(header.trans_id, 1)
        self.assertEqual(header.prot_id, 2)
        self.assertEqual(header.length, 3)
        self.assertEqual(header.unit_id, 4)

    def test_equality(self):
        header1 = ModbusHeader(trans_id=1, prot_id=2, length=3, unit_id=4)
        header2 = ModbusHeader(trans_id=1, prot_id=2, length=3, unit_id=4)
        self.assertTrue(header2 == header1)

    def test_inequality(self):
        header1 = ModbusHeader(trans_id=1, prot_id=2, length=3, unit_id=4)
        header2 = ModbusHeader(trans_id=1, prot_id=2, length=3, unit_id=5)
        self.assertTrue(header2 != header1)

    def test_length_is_the_seven_byte_mbap_header(self):

        # Two bytes of transaction id, two of protocol id, two of length and
        # one of unit id, per the Modbus Messaging Implementation Guide. The
        # length field then counts the unit id plus the PDU, which is why a
        # frame is this size plus length minus one
        header = ModbusHeader(trans_id=1, prot_id=2, length=3, unit_id=4)

        self.assertEqual(len(header), 7)

    def test_serialization(self):
        expected = b"\x00\x01\x00\x02\x00\x03\x04"
        header = ModbusHeader(trans_id=1, prot_id=2, length=3, unit_id=4)
        serialized = header.serialize()
        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        message = b"\x00\x01\x00\x02\x00\x03\x04"
        header = ModbusHeader.deserialize(message)

        self.assertEqual(header.trans_id, 1)
        self.assertEqual(header.prot_id, 2)
        self.assertEqual(header.length, 3)
        self.assertEqual(header.unit_id, 4)


if __name__ == "__main__":
    unittest.main()
