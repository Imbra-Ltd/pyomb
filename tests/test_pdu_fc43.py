import unittest

from pyomb.packets import ModbusRequestFC43, ModbusResponseFC43

####################################################################################################
# Request Tests
####################################################################################################


class TestPduRequestFC43(unittest.TestCase):
    def test_initilization(self):

        request = ModbusRequestFC43(mei_type=1, mei_data=(1, 2))

        self.assertEqual(request.fc, 43)
        self.assertEqual(request.mei_type, 1)
        self.assertEqual(request.mei_data, (1, 2))

    def test_equality(self):

        request1 = ModbusRequestFC43(mei_type=1, mei_data=(1, 2))
        request2 = ModbusRequestFC43(mei_type=1, mei_data=(1, 2))

        self.assertEqual(request1, request2)

    def test_inequality(self):

        request1 = ModbusRequestFC43(mei_type=1, mei_data=(1, 2))
        request2 = ModbusRequestFC43(mei_type=1, mei_data=(1, 3))

        self.assertNotEqual(request1, request2)

    def test_serialization(self):

        # fc = 2b, mei_type = 1, mei_data = (1, 2)
        expected = b"\x2b\x01\x01\x02"

        request = ModbusRequestFC43(mei_type=1, mei_data=(1, 2))

        serialized = request.serialize()

        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        message = b"\x2b\x01\x01\x02"

        pdu = ModbusRequestFC43.deserialize(message)

        self.assertEqual(pdu.fc, 43)
        self.assertEqual(pdu.mei_type, 1)
        self.assertEqual(pdu.mei_data, (1, 2))


####################################################################################################
# Response Tests
####################################################################################################


class TestPduResponseFC43(unittest.TestCase):
    def test_initialization(self):

        response = ModbusResponseFC43(mei_type=1, mei_data=(1, 2))

        self.assertEqual(response.fc, 43)
        self.assertEqual(response.mei_type, 1)
        self.assertEqual(response.mei_data, (1, 2))

    def test_equality(self):

        response1 = ModbusResponseFC43(mei_type=1, mei_data=(1, 2))
        response2 = ModbusResponseFC43(mei_type=1, mei_data=(1, 2))

        self.assertEqual(response1, response2)

    def test_inequality(self):

        response1 = ModbusResponseFC43(mei_type=1, mei_data=(1, 2))
        response2 = ModbusResponseFC43(mei_type=1, mei_data=(1, 3))

        self.assertNotEqual(response1, response2)

    def test_serialization(self):

        # fc = 2b, mei_type = 1, mei_data = (1, 2)
        expected = b"\x2b\x01\x01\x02"

        response = ModbusResponseFC43(mei_type=1, mei_data=(1, 2))

        serialized = response.serialize()

        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        message = b"\x2b\x01\x01\x02"

        pdu = ModbusResponseFC43.deserialize(message)

        self.assertEqual(pdu.fc, 43)
        self.assertEqual(pdu.mei_type, 1)
        self.assertEqual(pdu.mei_data, (1, 2))


if __name__ == "__main__":
    unittest.main()
