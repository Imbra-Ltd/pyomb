import unittest

from pyomb.packets import ModbusPduParser, ModbusRequestFC1, ModbusResponseFC1, ModbusRtuRequest, ModbusRtuResponse


class TestModbusRtuRequest(unittest.TestCase):
    def setUp(self):
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)

    def test_initialization(self):
        request = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        self.assertEqual(request.slave_id, 1)
        self.assertEqual(request.pdu.fc, 1)
        self.assertEqual(request.pdu.data, (1, 2))
        self.assertEqual(request.crc, 0xFFFF)

    def test_equality(self):
        request1 = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        request2 = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        self.assertTrue(request2 == request1)

    def test_inequality(self):
        request1 = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        request2 = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=3))

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Slave ID=0x01, Function Code=0x01, Starting Address=0x01
        # Quantity=0x02, CRC=0x0BEC sent low byte first
        expected = b"\x01\x01\x00\x01\x00\x02\xec\x0b"

        request = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        serialized = request.serialize()

        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        # Slave ID=0x01, Function Code=0x01, Starting Address=0x01
        # Quantity=0x02, CRC=0x0BEC sent low byte first
        message = b"\x01\x01\x00\x01\x00\x02\xec\x0b"

        request = ModbusRtuRequest.deserialize(message)

        self.assertIsInstance(request.pdu, ModbusRequestFC1)
        self.assertEqual(request.slave_id, 1)
        self.assertEqual(request.pdu.fc, 1)
        self.assertEqual(request.pdu.start_addr, 1)
        self.assertEqual(request.pdu.quantity, 2)
        self.assertEqual(request.crc, 0x0BEC)

    def test_set_parser(self):

        # Clear the pdu parser
        ModbusRtuRequest._pdu_parser = None

        # Set the pdu parser
        ModbusRtuRequest.set_parser(ModbusPduParser)

        # Get the pdu parser
        parser = ModbusRtuRequest.get_parser()

        # Check the parser
        self.assertEqual(parser, ModbusPduParser)

    def test_crc_calc(self):

        # For manual calculation, refer to the following link:
        # - https://www.lammertbies.nl/comm/info/crc-calculation.html
        # - https://crccalc.com/

        request = ModbusRtuRequest(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        crc = request.calc_crc()

        self.assertEqual(crc, 0x0BEC)


class TestModbusRtuResponse(unittest.TestCase):
    def setUp(self):
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)

    def test_initialization(self):
        response = ModbusRtuResponse(slave_id=1, pdu=ModbusResponseFC1(byte_count=1, output_status=(1, 2)))

        self.assertEqual(response.slave_id, 1)
        self.assertEqual(response.pdu.fc, 1)
        self.assertEqual(response.pdu.data, (1, 1, 2))
        self.assertEqual(response.crc, 0xFFFF)

    def test_equality(self):
        response1 = ModbusRtuResponse(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        response2 = ModbusRtuResponse(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        self.assertTrue(response2 == response1)

    def test_inequality(self):
        response1 = ModbusRtuResponse(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=2))

        response2 = ModbusRtuResponse(slave_id=1, pdu=ModbusRequestFC1(start_addr=1, quantity=3))

        self.assertTrue(response2 != response1)

    def test_serialization(self):

        # Slave ID=0x01, Function Code=0x01, Byte Count=0x02
        # Output Status=(0x01, 0x02), CRC=0xAD39 sent low byte first
        expected = b"\x01\x01\x02\x01\x02\x39\xad"

        response = ModbusRtuResponse(slave_id=1, pdu=ModbusResponseFC1(byte_count=2, output_status=(1, 2)))

        serialized = response.serialize()

        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        # Slave ID=0x01, Function Code=0x01, Byte Count=0x01
        # Output Status=(0x01, 0x02), CRC=0xAD39 sent low byte first
        message = b"\x01\x01\x02\x01\x02\x39\xad"

        response = ModbusRtuResponse.deserialize(message)

        self.assertIsInstance(response.pdu, ModbusResponseFC1)
        self.assertEqual(response.slave_id, 1)
        self.assertEqual(response.pdu.fc, 1)
        self.assertEqual(response.pdu.byte_count, 2)
        self.assertEqual(response.pdu.output_status, (1, 2))
        self.assertEqual(response.crc, 0xAD39)

    def test_set_parser(self):

        # Clear the pdu parser
        ModbusRtuResponse._pdu_parser = None

        # Set the pdu parser
        ModbusRtuResponse.set_parser(ModbusPduParser)

        # Get the pdu parser
        parser = ModbusRtuResponse.get_parser()

        # Check the parser
        self.assertEqual(parser, ModbusPduParser)

    def test_crc_calc(self):

        # For manual calculation, refer to the following link:
        # - https://www.lammertbies.nl/comm/info/crc-calculation.html
        # - https://crccalc.com/

        response = ModbusRtuResponse(slave_id=1, pdu=ModbusResponseFC1(byte_count=2, output_status=(1, 2)))

        crc = response.calc_crc()

        self.assertEqual(crc, 0xAD39)


if __name__ == "__main__":
    unittest.main()
