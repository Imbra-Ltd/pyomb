import unittest
from pyomb.packets import ModbusRequestFC5, ModbusResponseFC5


####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC5(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusRequestFC5(output_address=10, output_value=5)

        # Check the function code, starting address and output_value
        self.assertEqual(request.fc, 0x05)
        self.assertEqual(request.output_address, 10)
        self.assertEqual(request.output_value, 5)

    def test_equality(self):
        request1 = ModbusRequestFC5(output_address=10, output_value=5)
        request2 = ModbusRequestFC5(output_address=10, output_value=5)
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusRequestFC5(output_address=10, output_value=5)
        request2 = ModbusRequestFC5(output_address=20, output_value=3)
        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusRequestFC5(output_address=10, output_value=5)

        # Expected message in big-endian order (fc=0x01, output_address=0x000A, output_value=0x05)
        expected_message = b"\x05\x00\x0a\x00\x05"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x05\x00\x0a\xff\x00"
        deser_req = ModbusRequestFC5.deserialize(message)
        self.assertEqual(deser_req.output_address, 10)


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC5(unittest.TestCase):
    def test_initialization(self):
        request = ModbusResponseFC5(output_address=2, output_value=0xFF00)
        self.assertEqual(request.fc, 0x05)
        self.assertEqual(request.output_address, 2)
        self.assertEqual(request.output_value, 0xFF00)

    def test_equality(self):
        request1 = ModbusResponseFC5(output_address=2, output_value=0xFF00)
        request2 = ModbusResponseFC5(output_address=2, output_value=0xFF00)
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusResponseFC5(output_address=2, output_value=0xFF00)
        request2 = ModbusResponseFC5(output_address=1, output_value=0xFF00)
        self.assertTrue(request2 != request1)

    def test_serialization(self):
        request = ModbusResponseFC5(output_address=2, output_value=0xFF00)
        expected_message = b"\x05\x00\x02\xff\x00"

        ser_message = request.serialize()
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x05\x00\x02\xff\x00"
        deser_req = ModbusResponseFC5.deserialize(message)
        self.assertEqual(deser_req.output_address, 2)


if __name__ == "__main__":
    unittest.main()
