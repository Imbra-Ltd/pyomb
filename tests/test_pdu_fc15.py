import unittest

from pyomb.packets import ModbusRequestFC15, ModbusResponseFC15

####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC15(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusRequestFC15(start_addr=10, quantity=4, byte_count=1, values=(1,))

        # Check the function code, starting address and output_values
        self.assertEqual(request.fc, 0x0F)
        self.assertEqual(request.start_addr, 10)
        self.assertEqual(request.quantity, 4)
        self.assertEqual(request.byte_count, 1)
        self.assertEqual(request.values, (1,))

    def test_equality(self):

        request1 = ModbusRequestFC15(start_addr=10, quantity=4, byte_count=1, values=(1,))
        request2 = ModbusRequestFC15(start_addr=10, quantity=4, byte_count=1, values=(1,))

        self.assertTrue(request2 == request1)

    def test_inequality(self):

        request1 = ModbusRequestFC15(start_addr=10, quantity=4, byte_count=1, values=(1,))
        request2 = ModbusRequestFC15(start_addr=20, quantity=3, byte_count=1, values=(1,))

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusRequestFC15(start_addr=10, quantity=4, byte_count=1, values=(1,))

        # Expected message in big-endian order
        # (fc=0x0F, start_addr=0x000A, quantity=0x0004, byte_count=0x01, values=0x01)
        expected_message = b"\x0f\x00\x0a\x00\x04\x01\x01"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):

        message = b"\x0f\x00\x0a\x00\x04\x01\x01"
        deser_req = ModbusRequestFC15.deserialize(message)
        self.assertEqual(deser_req.start_addr, 10)


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC15(unittest.TestCase):
    def test_initialization(self):

        request = ModbusResponseFC15(start_addr=2, quantity=2)
        self.assertEqual(request.fc, 0x0F)
        self.assertEqual(request.start_addr, 2)
        self.assertEqual(request.quantity, 2)

    def test_equality(self):

        request1 = ModbusResponseFC15(start_addr=2, quantity=2)
        request2 = ModbusResponseFC15(start_addr=2, quantity=2)
        self.assertTrue(request2 == request1)

    def test_inequality(self):

        request1 = ModbusResponseFC15(start_addr=2, quantity=2)
        request2 = ModbusResponseFC15(start_addr=1, quantity=2)
        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusResponseFC15(start_addr=2, quantity=2)

        # Expected message in big-endian order (fc=0x0F, start_addr=0x0002, quantity=0x0002)
        expected_message = b"\x0f\x00\x02\x00\x02"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):

        message = b"\x0f\x00\x02\x00\x02"
        deser_req = ModbusResponseFC15.deserialize(message)
        self.assertEqual(deser_req.start_addr, 2)


if __name__ == "__main__":
    unittest.main()
