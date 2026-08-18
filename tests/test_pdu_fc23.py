import unittest
from pyomb.packets import ModbusRequestFC23, ModbusResponseFC23


####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC23(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusRequestFC23(
            read_start_addr=10,
            read_quantity=5,
            write_start_addr=20,
            write_quantity=3,
            write_byte_count=1,
            write_values=(1,),
        )

        # Check the function code, starting address and output_values
        self.assertEqual(request.fc, 0x17)
        self.assertEqual(request.read_start_addr, 10)
        self.assertEqual(request.read_quantity, 5)
        self.assertEqual(request.write_start_addr, 20)
        self.assertEqual(request.write_quantity, 3)
        self.assertEqual(request.write_byte_count, 1)
        self.assertEqual(request.write_values, (1,))

    def test_equality(self):

        request1 = ModbusRequestFC23(
            read_start_addr=10,
            read_quantity=5,
            write_start_addr=20,
            write_quantity=3,
            write_byte_count=1,
            write_values=(1,),
        )
        request2 = ModbusRequestFC23(
            read_start_addr=10,
            read_quantity=5,
            write_start_addr=20,
            write_quantity=3,
            write_byte_count=1,
            write_values=(1,),
        )

        self.assertTrue(request2 == request1)

    def test_inequality(self):

        request1 = ModbusRequestFC23(
            read_start_addr=10,
            read_quantity=5,
            write_start_addr=20,
            write_quantity=3,
            write_byte_count=1,
            write_values=(1,),
        )
        request2 = ModbusRequestFC23(
            read_start_addr=20,
            read_quantity=3,
            write_start_addr=30,
            write_quantity=2,
            write_byte_count=1,
            write_values=(1,),
        )

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusRequestFC23(
            read_start_addr=1,
            read_quantity=2,
            write_start_addr=3,
            write_quantity=4,
            write_byte_count=2,
            write_values=(1,),
        )

        # Expected message in big-endian order (fc=0x17, read_start_addr=0x000A, read_quantity=0x05)
        expected_message = b"\x17\x00\x01\x00\x02\x00\x03\x00\x04\x02\x00\x01"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):

        # fc=0x17, read_start_addr=0x000A, read_quantity=0x0005
        # write_start_addr=0x000F, write_quantity=0x0003,
        # write_byte_count=0x02, write_values=(0x00, 0x01)
        message = b"\x17\x00\x0a\x00\x05\x00\x0f\x00\x03\x02\x00\x01"

        # Deserialize the message
        deser_req = ModbusRequestFC23.deserialize(message)

        self.assertEqual(deser_req.read_start_addr, 10)
        self.assertEqual(deser_req.read_quantity, 5)
        self.assertEqual(deser_req.write_start_addr, 15)
        self.assertEqual(deser_req.write_quantity, 3)
        self.assertEqual(deser_req.write_byte_count, 2)
        self.assertEqual(deser_req.write_values, (1,))


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC23(unittest.TestCase):
    def test_initialization(self):

        # Create a request object
        request = ModbusResponseFC23(byte_count=4, values=(1, 2))

        # Check the function code, starting address and output_values
        self.assertEqual(request.fc, 23)
        self.assertEqual(request.byte_count, 4)
        self.assertEqual(request.values, (1, 2))

    def test_equality(self):

        request1 = ModbusResponseFC23(byte_count=4, values=(0x01, 0x02))

        request2 = ModbusResponseFC23(byte_count=4, values=(0x01, 0x02))

        self.assertTrue(request2 == request1)

    def test_inequality(self):

        request1 = ModbusResponseFC23(byte_count=4, values=(0x01, 0x02))

        request2 = ModbusResponseFC23(byte_count=4, values=(0x01, 0x03))

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create a request object
        request = ModbusResponseFC23(byte_count=4, values=(1, 2))

        # Expected message in big-endian order (fc=0x17, byte_count=0x04, values=(0x01, 0x02))
        expected_message = b"\x17\x04\x00\x01\x00\x02"

        # Serialize the request object
        ser_message = request.serialize()

        # Check if the serialized message is equal to the expected message
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):

        # fc=0x17, byte_count=0x04, values=(0x01, 0x02)
        message = b"\x17\x04\x00\x01\x00\x02"

        # Deserialize the message
        deser_req = ModbusResponseFC23.deserialize(message)

        # Check the function code, starting address and output_values
        self.assertEqual(deser_req.byte_count, 4)
        self.assertEqual(deser_req.values, (1, 2))


if __name__ == "__main__":
    unittest.main()
