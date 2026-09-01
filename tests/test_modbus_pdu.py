import struct
import unittest

from pyomb.packets import ModbusError, ModbusPdu


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

    def test_a_pdu_below_the_response_mask_is_a_request(self):

        pdu = ModbusPdu(fc=1, data=(1, 2, 3, 4))

        self.assertTrue(pdu.is_request())

    def test_a_pdu_at_or_above_the_response_mask_is_not(self):

        # ModbusError carries PDU_ID 0x8000, the boundary the check reads
        error = ModbusError(fc=1, exc_code=2)

        self.assertFalse(error.is_request())

    def test_serialization(self):
        expected = b"\x01\x00\x01\x02\x00\x03\x04"

        # This frame mixes 16-bit and 8-bit fields, which is the layout the
        # format string used to express. Bytes express it too, so the
        # assertion is unchanged while the route to it is the supported one.
        pdu = ModbusPdu(fc=1, data=struct.pack(">HBHB", 1, 2, 3, 4))

        self.assertEqual(pdu.serialize(), expected)

    def test_deserialization(self):
        message = b"\x01\x00\x01\x02\x00\x03\x04"

        pdu = ModbusPdu.deserialize(message)

        self.assertEqual(pdu.fc, 1)

        # Read back without a format string, the payload is its six byte
        # values rather than the four mixed-width fields the sender meant.
        # The frame is what survives the round trip; the widths were never
        # in the bytes.
        self.assertEqual(pdu.data, (0, 1, 2, 0, 3, 4))
        self.assertEqual(pdu.serialize(), message)


if __name__ == "__main__":
    unittest.main()
