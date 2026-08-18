import unittest
from pyomb.packets import ModbusRequestFC4, ModbusResponseFC4


####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC4(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusRequestFC4(start_addr=10, quantity=5)

        # Check the function code, starting address and quantity
        self.assertEqual(request.fc, 0x04)
        self.assertEqual(request.start_addr, 10)
        self.assertEqual(request.quantity, 5)

    def test_equality(self):
        request1 = ModbusRequestFC4(start_addr=10, quantity=5)
        request2 = ModbusRequestFC4(start_addr=10, quantity=5)
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusRequestFC4(start_addr=10, quantity=5)
        request2 = ModbusRequestFC4(start_addr=20, quantity=3)
        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusRequestFC4(start_addr=10, quantity=5)

        # Expected message in big-endian order (fc=0x01, start_addr=0x000A, quantity=0x05)
        expected_message = b"\x04\x00\x0a\x00\x05"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x04\x00\x0a\x00\x05"
        deser_req = ModbusRequestFC4.deserialize(message)
        self.assertEqual(deser_req.start_addr, 10)


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC4(unittest.TestCase):
    def test_initialization(self):
        request = ModbusResponseFC4(byte_count=4, values=(0x01, 0x02))
        self.assertEqual(request.fc, 0x04)
        self.assertEqual(request.byte_count, 4)

    def test_equality(self):
        request1 = ModbusResponseFC4(byte_count=4, values=(0x5555, 0xAAAA))
        request2 = ModbusResponseFC4(byte_count=4, values=(0x5555, 0xAAAA))
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusResponseFC4(byte_count=4, values=(0x5555, 0xAAAA))
        request2 = ModbusResponseFC4(byte_count=4, values=(0x5555, 0xBBBB))
        self.assertTrue(request2 != request1)

    def test_serialization(self):
        request = ModbusResponseFC4(byte_count=4, values=(0x01, 0x02))
        expected_message = b"\x04\x04\x00\x01\x00\x02"

        ser_message = request.serialize()
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x04\x04\x00\x01\x00\x02"
        deser_req = ModbusResponseFC4.deserialize(message)
        self.assertEqual(deser_req.byte_count, 4)


if __name__ == "__main__":
    unittest.main()
