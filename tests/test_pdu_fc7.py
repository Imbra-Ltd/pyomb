import unittest
from pyomb.packets import ModbusRequestFC7, ModbusResponseFC7


####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC7(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusRequestFC7()

        # Check the function code, starting address and output_values
        self.assertEqual(request.fc, 0x07)

    def test_equality(self):

        request1 = ModbusRequestFC7()
        request2 = ModbusRequestFC7()

        self.assertTrue(request2 == request1)

    def test_inequality(self):

        request1 = ModbusRequestFC7()
        request2 = ModbusRequestFC7()
        request2.data = 1

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # fc = 7
        expected = b"\x07"

        # Create a request object
        request = ModbusRequestFC7()

        # Serialize the request
        serialized = request.serialize()

        # Check the serialized data
        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        # fc = 7
        message = b"\x07"

        # Deserialize the message
        request = ModbusRequestFC7.deserialize(message)

        # Check the function code
        self.assertEqual(request.fc, 7)


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC7(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusResponseFC7(status=1)

        # Check the function code, starting address and output_values
        self.assertEqual(request.fc, 0x07)
        self.assertEqual(request.status, 1)

    def test_equality(self):

        request1 = ModbusResponseFC7(status=0xFF)
        request2 = ModbusResponseFC7(status=0xFF)

        self.assertTrue(request2 == request1)

    def test_inequality(self):

        request1 = ModbusResponseFC7(status=1)
        request2 = ModbusResponseFC7(status=2)

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # fc = 7
        expected = b"\x07\x01"

        # Create a request object
        request = ModbusResponseFC7(status=1)

        # Serialize the request
        serialized = request.serialize()

        # Check the serialized data
        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        # fc = 7
        message = b"\x07\x01"

        # Deserialize the message
        request = ModbusResponseFC7.deserialize(message)

        self.assertEqual(request.fc, 7)
        self.assertEqual(request.status, 1)


if __name__ == "__main__":
    unittest.main()
