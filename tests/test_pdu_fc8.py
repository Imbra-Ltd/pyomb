import unittest

from pyomb.packets import ModbusRequestFC8, ModbusResponseFC8

####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC8(unittest.TestCase):
    def test_initilization(self):

        request = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 2))

        self.assertEqual(request.fc, 8)
        self.assertEqual(request.sub_func, 1)
        self.assertEqual(request.subfunc_data, (1, 2))

    def test_equality(self):

        request1 = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 2))
        request2 = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 2))

        self.assertEqual(request1, request2)

    def test_inequality(self):

        request1 = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 2))
        request2 = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 3))

        self.assertNotEqual(request1, request2)

    def test_length_grows_with_the_subfunction_data(self):

        # One byte of function code and one two-byte word per field: the
        # subfunction and each subfunction data word, per the Diagnostics
        # function of the Modbus Application Protocol
        request = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 2))
        longer = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 2, 3))

        self.assertEqual(len(request), 7)
        self.assertEqual(len(longer), 9)

    def test_serialization(self):

        expected = b"\x08\x00\x01\x00\x01\x00\x02"

        request = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 2))

        serialized = request.serialize()

        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        message = b"\x08\x00\x01\x00\x01\x00\x02"

        pdu = ModbusRequestFC8.deserialize(message)

        self.assertEqual(pdu.fc, 8)
        self.assertEqual(pdu.sub_func, 1)
        self.assertEqual(pdu.subfunc_data, (1, 2))


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC8(unittest.TestCase):
    def test_initialization(self):

        response = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 2))

        self.assertEqual(response.fc, 8)
        self.assertEqual(response.sub_func, 1)
        self.assertEqual(response.subfunc_data, (1, 2))

    def test_equality(self):

        response1 = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 2))
        response2 = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 2))

        self.assertEqual(response1, response2)

    def test_inequality(self):

        response1 = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 2))
        response2 = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 3))

        self.assertNotEqual(response1, response2)

    def test_length_grows_with_the_subfunction_data(self):

        # One byte of function code and one two-byte word per field: the
        # subfunction and each subfunction data word, per the Diagnostics
        # function of the Modbus Application Protocol
        response = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 2))
        longer = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 2, 3))

        self.assertEqual(len(response), 7)
        self.assertEqual(len(longer), 9)

    def test_serialization(self):

        expected = b"\x08\x00\x01\x00\x01\x00\x02"

        response = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 2))

        serialized = response.serialize()

        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        message = b"\x08\x00\x01\x00\x01\x00\x02"

        pdu = ModbusResponseFC8.deserialize(message)

        self.assertEqual(pdu.fc, 8)
        self.assertEqual(pdu.sub_func, 1)
        self.assertEqual(pdu.subfunc_data, (1, 2))


if __name__ == "__main__":
    unittest.main()
