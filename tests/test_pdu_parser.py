import unittest

from pyomb.packets import ModbusError, ModbusPdu, ModbusPduParser, ModbusRequestFC1, ModbusResponseFC1


class TestModbusPduParser(unittest.TestCase):
    def setUp(self):
        # The registry is process-global and several tests below clear it.
        # Snapshot and restore it, so a test leaving it empty cannot break
        # unrelated tests that run afterwards.
        self.saved_registry = dict(ModbusPduParser.get_registry())

        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)
        ModbusPduParser.register(ModbusError)

    def tearDown(self):
        ModbusPduParser.set_registry(self.saved_registry)

    def test_parse_request(self):
        # Create the PDU bytes
        pdu1 = ModbusRequestFC1(start_addr=1, quantity=2)

        # Parse the PDU bytes
        pdu2 = ModbusPduParser.parse_request(pdu1.serialize())

        self.assertIsInstance(pdu2, ModbusRequestFC1)
        self.assertEqual(pdu2.fc, 1)
        self.assertEqual(pdu2.start_addr, 1)
        self.assertEqual(pdu2.quantity, 2)

    def test_parse_response(self):
        # Create the PDU bytes
        pdu1 = ModbusResponseFC1(byte_count=2, output_status=(1, 2))

        # Parse the PDU bytes
        pdu2 = ModbusPduParser.parse_response(pdu1.serialize())

        self.assertIsInstance(pdu2, ModbusResponseFC1)
        self.assertEqual(pdu2.fc, 1)
        self.assertEqual(pdu2.byte_count, 2)
        self.assertEqual(pdu2.output_status, (1, 2))

    def test_parse_error(self):
        # Create the PDU bytes
        pdu1 = ModbusError(fc=1, exc_code=2)

        # Parse the PDU bytes
        pdu2 = ModbusPduParser.parse_response(pdu1.serialize())

        self.assertIsInstance(pdu2, ModbusError)
        self.assertEqual(pdu2.fc, 1)
        self.assertEqual(pdu2.exc_code, 2)

    def test_parse_unknown(self):
        # Create the PDU bytes
        pdu1 = ModbusPdu(fc=0x7F, data=(1, 2, 3))

        # Parse the PDU bytes
        pdu2 = ModbusPduParser.parse_request(pdu1.serialize())

        # Check the pdu
        self.assertIsInstance(pdu2, ModbusPdu)

    def test_clear_registry(self):
        ModbusPduParser.clear_registry()
        self.assertEqual(ModbusPduParser.get_registry(), {})

    def test_get_registry(self):
        ModbusPduParser.clear_registry()
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)
        ModbusPduParser.register(ModbusError)
        registry = ModbusPduParser.get_registry()
        self.assertEqual(len(registry), 3)

    def test_set_registry(self):
        # Get the default registry
        registry = ModbusPduParser.get_registry()

        # Clear the registry
        ModbusPduParser.clear_registry()

        # Set the registry using the default configuration
        ModbusPduParser.set_registry(registry)

        # Check if the registry is set correctly
        self.assertEqual(ModbusPduParser.get_registry(), registry)

    def test_register(self):

        # Clear the registry
        ModbusPduParser.clear_registry()

        # Register the ModbusRequestFC1 class
        ModbusPduParser.register(ModbusRequestFC1)

        # Check the registry
        registry = ModbusPduParser.get_registry()
        self.assertEqual(len(registry), 1)
        self.assertEqual(registry[1], ModbusRequestFC1)

    def test_unregister(self):

        # Clear the registry
        ModbusPduParser.clear_registry()

        # Register the ModbusRequestFC1 class
        ModbusPduParser.register(ModbusRequestFC1)

        # Check the registry
        registry = ModbusPduParser.get_registry()
        self.assertEqual(len(registry), 1)
        self.assertEqual(registry[1], ModbusRequestFC1)

        # Unregister the ModbusRequestFC1 class
        ModbusPduParser.unregister(ModbusRequestFC1)

        # Check the registry
        registry = ModbusPduParser.get_registry()
        self.assertEqual(len(registry), 0)


if __name__ == "__main__":
    unittest.main()
