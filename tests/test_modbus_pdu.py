import unittest
from pyomb.packets import ModbusPdu


class TestModbusPdu(unittest.TestCase):
    def test_initialization(self):
        pdu = ModbusPdu(
            fc=1,
            data=(1, 2, 3, 4),
        )
        self.assertEqual(pdu.fc, 1)
        self.assertEqual(pdu.data, (1, 2, 3, 4))

    def test_equality(self):
        pdu1 = ModbusPdu(fc=1, data=(1, 2, 3, 4))
        pdu2 = ModbusPdu(fc=1, data=(1, 2, 3, 4))
        self.assertTrue(pdu2 == pdu1)

    def test_inequality(self):
        pdu1 = ModbusPdu(fc=1, data=(1, 2, 3, 4))
        pdu2 = ModbusPdu(fc=1, data=(1, 2, 3, 5))
        self.assertTrue(pdu2 != pdu1)

    def test_serialization(self):
        expected = b"\x01\x00\x01\x02\x00\x03\x04"
        pdu = ModbusPdu(fc=1, data=(1, 2, 3, 4))
        serialized = pdu.serialize(fmt=">BHBHB")
        self.assertEqual(serialized, expected)

    def test_deserialization(self):
        message = b"\x01\x00\x01\x02\x00\x03\x04"
        pdu = ModbusPdu.deserialize(message, fmt=">BHBHB")
        self.assertEqual(pdu.fc, 1)
        self.assertEqual(pdu.data, (1, 2, 3, 4))


if __name__ == "__main__":
    unittest.main()
