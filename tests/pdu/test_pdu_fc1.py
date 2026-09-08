import unittest

from pyomb.packets import ModbusRequestFC1, ModbusResponseFC1

####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC1(unittest.TestCase):
    def test_initialization(self):
        # Create a request object
        request = ModbusRequestFC1(start_addr=10, quantity=5)

        # Check the function code, starting address and quantity
        self.assertEqual(request.fc, 0x01)
        self.assertEqual(request.start_addr, 10)
        self.assertEqual(request.quantity, 5)

    def test_equality(self):
        request1 = ModbusRequestFC1(start_addr=10, quantity=5)
        request2 = ModbusRequestFC1(start_addr=10, quantity=5)
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusRequestFC1(start_addr=10, quantity=5)
        request2 = ModbusRequestFC1(start_addr=20, quantity=3)
        self.assertTrue(request2 != request1)

    def test_serialization(self):
        # Create a request object
        request = ModbusRequestFC1(start_addr=10, quantity=5)

        # Expected message in big-endian order (fc=0x01, start_addr=0x000A, quantity=0x05)
        expected_message = b"\x01\x00\x0a\x00\x05"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x01\x00\n\x00\x05"
        deser_req = ModbusRequestFC1.deserialize(message)
        self.assertEqual(deser_req.start_addr, 10)


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC1(unittest.TestCase):
    def test_initialization(self):
        request = ModbusResponseFC1(byte_count=2, output_status=(0x01, 0x02))
        self.assertEqual(request.fc, 0x01)
        self.assertEqual(request.byte_count, 2)

    def test_equality(self):
        request1 = ModbusResponseFC1(byte_count=2, output_status=(0x05, 0x0A))
        request2 = ModbusResponseFC1(byte_count=2, output_status=(0x05, 0x0A))
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusResponseFC1(byte_count=2, output_status=(0x05, 0x0A))
        request2 = ModbusResponseFC1(byte_count=2, output_status=(0x05, 0x0B))
        self.assertTrue(request2 != request1)

    def test_serialization(self):
        request = ModbusResponseFC1(byte_count=2, output_status=(0x01, 0x02))
        expected_message = b"\x01\x02\x01\x02"

        ser_message = request.serialize()
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x01\x02\x01\x02"
        deser_req = ModbusResponseFC1.deserialize(message)
        self.assertEqual(deser_req.byte_count, 2)


if __name__ == "__main__":
    unittest.main()
