import unittest
from pyomb.packets import ModbusRequestFC1, ModbusResponseFC1
from pyomb.packets import ModbusTcpRequest, ModbusTcpResponse
from pyomb.packets import ModbusPduParser, ModbusHeader


class TestModbusTcpRequest(unittest.TestCase):
    def setUp(self):
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)

    def test_initialization(self):
        header = ModbusHeader(trans_id=1, prot_id=2, length=6, unit_id=4)
        pdu = ModbusRequestFC1(start_addr=1, quantity=2)
        request = ModbusTcpRequest(header=header, pdu=pdu)

        self.assertEqual(request.header.trans_id, 1)
        self.assertEqual(request.header.prot_id, 2)
        self.assertEqual(request.header.length, 6)
        self.assertEqual(request.header.unit_id, 4)
        self.assertEqual(request.pdu.fc, 1)
        self.assertEqual(request.pdu.data, (1, 2))

    def test_equality(self):
        header = ModbusHeader(trans_id=1, prot_id=2, length=6, unit_id=4)
        pdu = ModbusRequestFC1(start_addr=1, quantity=2)
        request1 = ModbusTcpRequest(header=header, pdu=pdu)
        request2 = ModbusTcpRequest(header=header, pdu=pdu)

        self.assertTrue(request2 == request1)

    def test_inequality(self):
        header = ModbusHeader(trans_id=1, prot_id=2, length=6, unit_id=4)
        pdu1 = ModbusRequestFC1(start_addr=1, quantity=2)
        pdu2 = ModbusRequestFC1(start_addr=1, quantity=3)
        request1 = ModbusTcpRequest(header=header, pdu=pdu1)
        request2 = ModbusTcpRequest(header=header, pdu=pdu2)

        self.assertTrue(request2 != request1)

    def test_serialization(self):

        # Create the packet elements
        header = ModbusHeader(trans_id=1, prot_id=2, length=6, unit_id=4)
        pdu = ModbusRequestFC1(start_addr=1, quantity=2)

        # Trans-ID=0x0001, Prot-ID=0x0002, Length=0x0006, Unit-ID=0x04
        # Function Code=0x01, Starting Address=0x0001, Quantity=0x0002
        expected = b"\x00\x01\x00\x02\x00\x06\x04\x01\x00\x01\x00\x02"

        # Create the packet
        request = ModbusTcpRequest(header=header, pdu=pdu)

        # Serialize the packet
        serialized = request.serialize()

        # Check the result
        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        # Trans-ID=0x0001, Prot-ID=0x0002, Length=0x0006, Unit-ID=0x04
        # Function Code=0x01, Starting Address=0x0001, Quantity=0x0002
        message = b"\x00\x01\x00\x02\x00\x06\x04\x01\x00\x01\x00\x02"

        request = ModbusTcpRequest.deserialize(message)

        self.assertIsInstance(request.pdu, ModbusRequestFC1)
        self.assertEqual(request.header.trans_id, 1)
        self.assertEqual(request.header.prot_id, 2)
        self.assertEqual(request.header.length, 6)
        self.assertEqual(request.header.unit_id, 4)
        self.assertEqual(request.pdu.fc, 1)
        self.assertEqual(request.pdu.start_addr, 1)
        self.assertEqual(request.pdu.quantity, 2)

    def test_set_parser(self):

        # Clear the pdu parser
        ModbusTcpRequest._pdu_parser = None

        # Set the pdu parser
        ModbusTcpRequest.set_parser(ModbusPduParser)

        # Get the pdu parser
        parser = ModbusTcpRequest.get_parser()

        # Check the parser
        self.assertEqual(parser, ModbusPduParser)


class TestModbusTcpResponse(unittest.TestCase):
    def setUp(self):
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)

    def test_initialization(self):

        # Create the packet elements
        header = ModbusHeader(trans_id=1, prot_id=2, length=5, unit_id=4)
        pdu = ModbusResponseFC1(byte_count=1, output_status=(1, 2))

        # Create the packet
        response = ModbusTcpResponse(header=header, pdu=pdu)

        # Check the result
        self.assertEqual(response.header.trans_id, 1)
        self.assertEqual(response.header.prot_id, 2)
        self.assertEqual(response.header.length, 5)
        self.assertEqual(response.header.unit_id, 4)
        self.assertEqual(response.pdu.fc, 1)
        self.assertEqual(response.pdu.data, (1, 1, 2))

    def test_equality(self):

        # Create the packet elements
        header = ModbusHeader(trans_id=1, prot_id=2, length=5, unit_id=4)
        pdu1 = ModbusResponseFC1(byte_count=1, output_status=(1, 2))
        pdu2 = ModbusResponseFC1(byte_count=1, output_status=(1, 2))

        # Create the packets
        response1 = ModbusTcpResponse(header=header, pdu=pdu1)
        response2 = ModbusTcpResponse(header=header, pdu=pdu2)

        # Check the result
        self.assertTrue(response2 == response1)

    def test_inequality(self):

        # Create the packet elements
        header = ModbusHeader(trans_id=1, prot_id=2, length=5, unit_id=4)
        pdu1 = ModbusResponseFC1(byte_count=1, output_status=(1, 2))
        pdu2 = ModbusResponseFC1(byte_count=1, output_status=(1, 3))

        # Create the packets
        response1 = ModbusTcpResponse(header=header, pdu=pdu1)
        response2 = ModbusTcpResponse(header=header, pdu=pdu2)

        # Check the result
        self.assertTrue(response2 != response1)

    def test_serialization(self):

        # Create the packet elements
        header = ModbusHeader(trans_id=1, prot_id=2, length=5, unit_id=4)
        pdu = ModbusResponseFC1(byte_count=2, output_status=(1, 2))

        # Create the packet
        response = ModbusTcpResponse(header=header, pdu=pdu)

        # Serialize the packet
        serialized = response.serialize()

        # Trans-ID=0x0001, Prot-ID=0x0002, Length=0x0005, Unit-ID=0x04
        # Function Code=0x01, Byte Count=0x01, Output Status=(0x01, 0x02)
        expected = b"\x00\x01\x00\x02\x00\x05\x04\x01\x02\x01\x02"

        # Check the result
        self.assertEqual(serialized, expected)

    def test_deserialization(self):

        # Create the byte stream
        message = b"\x00\x01\x00\x02\x00\x05\x04\x01\x02\x01\x02"

        # Deserialize the byte stream
        response = ModbusTcpResponse.deserialize(message)

        # Check the response
        self.assertIsInstance(response.pdu, ModbusResponseFC1)

    def test_set_parser(self):

        # Clear the pdu parser
        ModbusTcpResponse._pdu_parser = None

        # Set the pdu parser
        ModbusTcpResponse.set_parser(ModbusPduParser)

        # Get the pdu parser
        parser = ModbusTcpResponse.get_parser()

        # Check the parser
        self.assertEqual(parser, ModbusPduParser)
