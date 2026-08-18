import unittest
from pyomb.packets import ModbusError, ModbusPduParser


####################################################################################################
# Error Tests
####################################################################################################


class TestPduError(unittest.TestCase):
    def setUp(self):
        ModbusPduParser.register(ModbusError)

    def test_initialization(self):
        request = ModbusError(fc=0x01, exc_code=0x01)
        self.assertEqual(request.fc, 0x01)
        self.assertEqual(request.exc_code, 0x01)

    def test_equality(self):
        request1 = ModbusError(fc=0x01, exc_code=0x01)
        request2 = ModbusError(fc=0x01, exc_code=0x01)
        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusError(fc=0x01, exc_code=0x01)
        request2 = ModbusError(fc=0x01, exc_code=0x02)
        self.assertTrue(request2 != request1)

    def test_serialization(self):
        request = ModbusError(fc=1, exc_code=0x01)
        expected_message = b"\x81\x01"

        ser_message = request.serialize()
        self.assertEqual(ser_message, expected_message)

    def test_deserialization(self):
        message = b"\x81\x01"
        deser_req = ModbusError.deserialize(message)

        self.assertEqual(deser_req.fc, 0x01)
        self.assertEqual(deser_req.exc_code, 0x01)

    def test_pdu_parser(self):

        message = b"\x81\x01"
        deser_req = ModbusPduParser.parse_response(message)

        self.assertIsInstance(deser_req, ModbusError)
        self.assertEqual(deser_req.fc, 0x01)
