import unittest

from pyomb.errors import (
    ModbusAcknowledgeError,
    ModbusBaseError,
    ModbusGatewayPathUnavailableError,
    ModbusGatewayTargetDeviceFailedToRespondError,
    ModbusIllegalDataAddressError,
    ModbusIllegalDataValueError,
    ModbusIllegalFunctionError,
    ModbusMemoryParityError,
    ModbusNetworkError,
    ModbusPacketError,
    ModbusProtocolError,
    ModbusSlaveDeviceBusyError,
    ModbusSlaveDeviceFailureError,
    ModbusTimeoutError,
)


class TestErrors(unittest.TestCase):
    def test_modbus_error(self):
        e = ModbusBaseError("Test error")
        self.assertEqual("Test error", str(e))

    def test_modbus_protocol_error(self):
        e = ModbusProtocolError("Test protocol error", 0x01)
        self.assertEqual("Test protocol error (Protocol Error Code 0x1)", str(e))

    def test_modbus_illegal_function(self):
        e = ModbusIllegalFunctionError(0x01)
        self.assertEqual("The function code 1 is not valid (Protocol Error Code 0x1)", str(e))

    def test_modbus_illegal_data_address(self):
        e = ModbusIllegalDataAddressError(0x02)
        self.assertEqual("The data address 2 is not valid (Protocol Error Code 0x2)", str(e))

    def test_modbus_illegal_data_value(self):
        e = ModbusIllegalDataValueError(0x03)
        self.assertEqual("The data value 3 is not valid (Protocol Error Code 0x3)", str(e))

    def test_modbus_slave_device_failure(self):
        e = ModbusSlaveDeviceFailureError()
        self.assertEqual(
            "The slave device failed to perform the requested action (Protocol Error Code 0x4)",
            str(e),
        )

    def test_modbus_acknowledge(self):
        e = ModbusAcknowledgeError()
        self.assertEqual(
            "The slave device acknowledged the request but is processing it (Protocol Error Code 0x5)", str(e)
        )

    def test_modbus_slave_device_busy(self):
        e = ModbusSlaveDeviceBusyError()
        self.assertEqual(
            "The slave device is busy processing a long-duration command (Protocol Error Code 0x6)", str(e)
        )

    def test_modbus_memory_parity_error(self):
        e = ModbusMemoryParityError()
        self.assertEqual("The slave device detected a parity error in memory (Protocol Error Code 0x8)", str(e))

    def test_modbus_gateway_path_unavailable(self):
        e = ModbusGatewayPathUnavailableError()
        self.assertEqual("The gateway could not find the path to the target device (Protocol Error Code 0xA)", str(e))

    def test_modbus_gateway_target_device_failed_to_respond(self):
        e = ModbusGatewayTargetDeviceFailedToRespondError()
        self.assertEqual("The gateway received no response from the target device (Protocol Error Code 0xB)", str(e))

    def test_modbus_network_error(self):
        e = ModbusNetworkError("Test network error")
        self.assertEqual("Test network error", str(e))

    def test_modbus_packet_error(self):
        e = ModbusPacketError("Test packet error")
        self.assertEqual("Test packet error", str(e))

    def test_modbus_timeout_error_is_a_network_error(self):
        # A caller retrying on the parent still retries a peer that never
        # answered; one catching the child does so without retrying a dead port.
        e = ModbusTimeoutError("Test timeout error")
        self.assertEqual("Test timeout error", str(e))
        self.assertIsInstance(e, ModbusNetworkError)


if __name__ == "__main__":
    unittest.main()
