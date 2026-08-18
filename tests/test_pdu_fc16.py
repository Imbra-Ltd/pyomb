import unittest
from pyomb.packets import ModbusRequestFC16, ModbusResponseFC16


####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC16(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusRequestFC16(start_addr=10, quantity=5, byte_count=1, values=(1,))

        # Check the function code, starting address and output_values
        self.assertEqual(request.fc, 0x10)
        self.assertEqual(request.start_addr, 10)
        self.assertEqual(request.quantity, 5)
        self.assertEqual(request.byte_count, 1)
        self.assertEqual(request.values, (1,))

    def test_equality(self):

        request1 = ModbusRequestFC16(start_addr=10, quantity=5, byte_count=1, values=(1,))
        request2 = ModbusRequestFC16(start_addr=10, quantity=5, byte_count=1, values=(1,))

        self.assertTrue(request2 == request1)

    def test_inequality(self):

        request1 = ModbusRequestFC16(start_addr=10, quantity=5, byte_count=1, values=(1,))
        request2 = ModbusRequestFC16(start_addr=20, quantity=3, byte_count=1, values=(1,))

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusRequestFC16(start_addr=10, quantity=5, byte_count=1, values=(1,))

        # Expected message in big-endian order (fc=0x01, start_addr=0x000A, quantity=0x05)
        expected_message = b"\x10\x00\x0a\x00\x05\x01\x00\x01"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x10\x00\x0a\x00\x05\x01"
        deser_req = ModbusRequestFC16.deserialize(message)
        self.assertEqual(deser_req.start_addr, 10)


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC16(unittest.TestCase):
    def test_initialization(self):
        request = ModbusResponseFC16(start_addr=10, quantity=5)
        self.assertEqual(request.fc, 0x10)
        self.assertEqual(request.start_addr, 10)
        self.assertEqual(request.quantity, 5)

    def test_equality(self):

        request1 = ModbusResponseFC16(start_addr=10, quantity=5)
        request2 = ModbusResponseFC16(start_addr=10, quantity=5)

        self.assertTrue(request2 == request1)

    def test_inequality(self):

        request1 = ModbusResponseFC16(start_addr=10, quantity=5)
        request2 = ModbusResponseFC16(start_addr=20, quantity=3)

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusResponseFC16(start_addr=10, quantity=5)

        # Expected message in big-endian order (fc=0x01, start_addr=0x000A, quantity=0x05)
        expected_message = b"\x10\x00\x0a\x00\x05"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):

        message = b"\x10\x00\x0a\x00\x05"
        deser_req = ModbusResponseFC16.deserialize(message)
        self.assertEqual(deser_req.start_addr, 10)


if __name__ == "__main__":
    unittest.main()
