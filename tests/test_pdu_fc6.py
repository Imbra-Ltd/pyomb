import unittest
from pyomb.packets import ModbusRequestFC6, ModbusResponseFC6


####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC6(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusRequestFC6(output_address=10, output_value=5)

        # Check the function code, starting address and output_value
        self.assertEqual(request.fc, 0x06)
        self.assertEqual(request.output_address, 10)
        self.assertEqual(request.output_value, 5)

    def test_equality(self):
        request1 = ModbusRequestFC6(output_address=10, output_value=5)
        request2 = ModbusRequestFC6(output_address=10, output_value=5)
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusRequestFC6(output_address=10, output_value=5)
        request2 = ModbusRequestFC6(output_address=20, output_value=3)
        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusRequestFC6(output_address=10, output_value=5)

        # Expected message in big-endian order (fc=0x01, output_address=0x000A, output_value=0x05)
        expected_message = b"\x06\x00\x0a\x00\x05"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x06\x00\x0a\x00\x05"
        deser_req = ModbusRequestFC6.deserialize(message)
        self.assertEqual(deser_req.output_address, 10)


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC6(unittest.TestCase):
    def test_initialization(self):
        request = ModbusResponseFC6(output_address=10, output_value=5)
        self.assertEqual(request.fc, 0x06)
        self.assertEqual(request.output_address, 10)
        self.assertEqual(request.output_value, 5)

    def test_equality(self):
        request1 = ModbusResponseFC6(output_address=10, output_value=5)
        request2 = ModbusResponseFC6(output_address=10, output_value=5)
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusResponseFC6(output_address=10, output_value=5)
        request2 = ModbusResponseFC6(output_address=20, output_value=3)
        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusResponseFC6(output_address=10, output_value=5)

        # Expected message in big-endian order (fc=0x01, output_address=0x000A, output_value=0x05)
        expected_message = b"\x06\x00\x0a\x00\x05"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x06\x00\x0a\x00\x05"
        deser_req = ModbusResponseFC6.deserialize(message)
        self.assertEqual(deser_req.output_address, 10)


if __name__ == "__main__":
    unittest.main()
