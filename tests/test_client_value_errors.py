"""Bad write values are refused as Modbus errors, not as IndexError.

FC5 and FC6 write a single value, so sendRequest() narrows a sequence to its
first element. An empty sequence reached the subscript and raised IndexError
from inside the argument normalisation -- an exception naming neither the
argument nor the caller, and the only place in the library reporting bad input
as something other than a ModbusProtocolError.
"""

import unittest

from stub_socket import LoopbackSocket

from pyomb.client_simulator import ModbusClientSimulator
from pyomb.errors import ModbusIllegalDataValue, ModbusProtocolError
from pyomb.packets import ModbusTcpRequest

# The function codes that narrow a sequence to one value.
SINGLE_WRITE_CODES = (5, 6)


class ClientOnAStubSocket(unittest.TestCase):
    def make_client(self, **options):
        client = ModbusClientSimulator(**options)

        # The constructor opens a real socket that is never connected here.
        client.sock.close()
        client.sock = LoopbackSocket()

        return client


class TestEmptyWriteValues(ClientOnAStubSocket):
    def test_empty_sequence_is_a_modbus_error(self):
        for fc in SINGLE_WRITE_CODES:
            for empty in ((), [], ""):
                with self.subTest(fc=fc, empty=type(empty).__name__):
                    client = self.make_client()

                    with self.assertRaises(ModbusIllegalDataValue):
                        client.sendRequest(fc=fc, writeAddress=0, values=empty)

    def test_the_error_is_a_protocol_error(self):
        # Callers catch the family, not the leaf.
        client = self.make_client()

        with self.assertRaises(ModbusProtocolError):
            client.sendRequest(fc=5, writeAddress=0, values=())

    def test_nothing_is_sent_when_the_value_is_refused(self):
        client = self.make_client()

        with self.assertRaises(ModbusIllegalDataValue):
            client.sendRequest(fc=6, writeAddress=0, values=[])

        self.assertEqual(client.sock.sent, [])

    def test_the_transaction_id_is_not_consumed(self):
        # A refused request never reached the wire, so the next one that does
        # should still be the first identifier.
        client = self.make_client()

        with self.assertRaises(ModbusIllegalDataValue):
            client.sendRequest(fc=5, writeAddress=0, values=())

        client.sendRequest(fc=1, readAddress=0, readCount=1)
        request = ModbusTcpRequest.deserialize(client.sock.frame())

        self.assertEqual(request.header.trans_id, 0)


class TestValuesStillAccepted(ClientOnAStubSocket):
    """The guard must not narrow what already worked."""

    def test_populated_sequence_still_takes_the_first_element(self):
        for fc in SINGLE_WRITE_CODES:
            with self.subTest(fc=fc):
                client = self.make_client()
                client.sendRequest(fc=fc, writeAddress=1, values=[0x1234, 0x5678])
                request = ModbusTcpRequest.deserialize(client.sock.frame())

                self.assertEqual(request.pdu.output_value, 0x1234)

    def test_bare_scalar_is_still_accepted(self):
        for fc in SINGLE_WRITE_CODES:
            with self.subTest(fc=fc):
                client = self.make_client()
                client.sendRequest(fc=fc, writeAddress=1, values=0x1234)
                request = ModbusTcpRequest.deserialize(client.sock.frame())

                self.assertEqual(request.pdu.output_value, 0x1234)

    def test_generator_is_still_accepted(self):
        # len() would have raised TypeError here, and the handler below the
        # normalisation would have swallowed it and treated the generator as a
        # scalar.
        client = self.make_client()
        client.sendRequest(fc=6, writeAddress=1, values=(v for v in [0x0042]))
        request = ModbusTcpRequest.deserialize(client.sock.frame())

        self.assertEqual(request.pdu.output_value, 0x0042)

    def test_empty_generator_is_refused_like_an_empty_sequence(self):
        client = self.make_client()

        with self.assertRaises(ModbusIllegalDataValue):
            client.sendRequest(fc=6, writeAddress=1, values=(v for v in []))

    def test_multiple_write_codes_are_untouched(self):
        # Only FC5 and FC6 narrow, so the guard must not reach the codes that
        # legitimately take a sequence.
        client = self.make_client()
        client.sendRequest(fc=16, writeAddress=0, writeCount=2, values=[1, 2])
        request = ModbusTcpRequest.deserialize(client.sock.frame())

        self.assertEqual(tuple(request.pdu.values), (1, 2))


if __name__ == "__main__":
    unittest.main()
