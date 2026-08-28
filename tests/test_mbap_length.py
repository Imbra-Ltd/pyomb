import unittest

from pyomb.errors import ModbusPacketError
from pyomb.packets import (
    ModbusHeader,
    ModbusPduParser,
    ModbusRequestFC1,
    ModbusResponseFC1,
    ModbusTcpRequest,
    ModbusTcpResponse,
    validate_mbap_length,
)


class TestValidateMbapLength(unittest.TestCase):
    """The MBAP length field arrives from the network and is not trusted."""

    def setUp(self):
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)

    @staticmethod
    def build_request(length=None):
        """Serialize an FC1 request, optionally with a wrong length field."""

        pdu = ModbusRequestFC1(start_addr=0, quantity=1)
        header = ModbusHeader(unit_id=1, length=len(pdu) + 1 if length is None else length)

        return ModbusTcpRequest(header=header, pdu=pdu).serialize()

    def test_conformant_frame_round_trips(self):
        stream = self.build_request()
        request = ModbusTcpRequest.deserialize(stream)

        self.assertEqual(request.header.length, len(stream) - ModbusHeader.SIZE + 1)
        self.assertEqual(request.pdu.start_addr, 0)

    def test_over_declared_length_is_rejected(self):
        # The dangerous direction: the field promises far more than was sent.
        stream = self.build_request(length=0xFFFF)

        with self.assertRaises(ModbusPacketError):
            ModbusTcpRequest.deserialize(stream)

    def test_under_declared_length_is_rejected(self):
        stream = self.build_request(length=2)

        with self.assertRaises(ModbusPacketError):
            ModbusTcpRequest.deserialize(stream)

    def test_response_length_is_validated(self):
        pdu = ModbusResponseFC1(byte_count=2, output_status=(0xFF, 0x00))
        header = ModbusHeader(unit_id=1, length=0xFFFF)
        stream = ModbusTcpResponse(header=header, pdu=pdu).serialize()

        with self.assertRaises(ModbusPacketError):
            ModbusTcpResponse.deserialize(stream)

    def test_helper_reports_declared_and_received_sizes(self):
        header = ModbusHeader(unit_id=1, length=99)

        with self.assertRaises(ModbusPacketError) as caught:
            validate_mbap_length(header, b"\x00" * 12)

        message = str(caught.exception)
        self.assertIn("99", message)
        self.assertIn("12", message)


if __name__ == "__main__":
    unittest.main()
