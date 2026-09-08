import unittest

from pyomb.packets import ModbusRequestFC22, ModbusResponseFC22


class TestModbusRequestFC22(unittest.TestCase):
    def test_initialization(self):

        # Create the pdu instance
        pdu = ModbusRequestFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)

        # Validate the pdu instance
        self.assertEqual(pdu.fc, 0x16)
        self.assertEqual(pdu.ref_addr, 0x01)
        self.assertEqual(pdu.and_mask, 0x02)
        self.assertEqual(pdu.or_mask, 0x03)

    def test_equality(self):

        # Create the pdu instances
        pdu1 = ModbusRequestFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)
        pdu2 = ModbusRequestFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)

        # Validate the pdu instances
        self.assertEqual(pdu1, pdu2)

    def test_inequality(self):

        # Create the pdu instances
        pdu1 = ModbusRequestFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)
        pdu2 = ModbusRequestFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x04)

        # Validate the pdu instances
        self.assertNotEqual(pdu1, pdu2)

    def test_serialization(self):

        # Create the pdu instance
        pdu = ModbusRequestFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)

        # Define the expected output
        expected_output = b"\x16\x00\x01\x00\x02\x00\x03"

        # Validate the pdu instance
        self.assertEqual(expected_output, pdu.serialize())

    def test_deserialization(self):

        # Define the input bytes
        input_bytes = b"\x16\x00\x01\x00\x02\x00\x03"

        # Deserialize the bytes
        pdu = ModbusRequestFC22.deserialize(input_bytes)

        # Validate the pdu instance
        self.assertEqual(pdu.fc, 0x16)
        self.assertEqual(pdu.ref_addr, 0x01)
        self.assertEqual(pdu.and_mask, 0x02)
        self.assertEqual(pdu.or_mask, 0x03)


class TestModbusResponseFC22(unittest.TestCase):
    def test_initialization(self):

        # Create the pdu instance
        pdu = ModbusResponseFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)

        # Validate the pdu instance
        self.assertEqual(pdu.fc, 0x16)
        self.assertEqual(pdu.ref_addr, 0x01)
        self.assertEqual(pdu.and_mask, 0x02)
        self.assertEqual(pdu.or_mask, 0x03)

    def test_equality(self):

        # Create the pdu instances
        pdu1 = ModbusResponseFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)
        pdu2 = ModbusResponseFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)

        # Validate the pdu instances
        self.assertEqual(pdu1, pdu2)

    def test_inequality(self):

        # Create the pdu instances
        pdu1 = ModbusResponseFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)
        pdu2 = ModbusResponseFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x04)

        # Validate the pdu instances
        self.assertNotEqual(pdu1, pdu2)

    def test_serialization(self):

        # Create the pdu instance
        pdu = ModbusResponseFC22(ref_addr=0x01, and_mask=0x02, or_mask=0x03)

        # Define the expected output
        expected_output = b"\x16\x00\x01\x00\x02\x00\x03"

        # Validate the pdu instance
        self.assertEqual(expected_output, pdu.serialize())

    def test_deserialization(self):

        # Define the input bytes
        input_bytes = b"\x16\x00\x01\x00\x02\x00\x03"

        # Deserialize the bytes
        pdu = ModbusResponseFC22.deserialize(input_bytes)

        # Validate the pdu instance
        self.assertEqual(pdu.fc, 0x16)
        self.assertEqual(pdu.ref_addr, 0x01)
        self.assertEqual(pdu.and_mask, 0x02)
        self.assertEqual(pdu.or_mask, 0x03)
