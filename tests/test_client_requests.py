"""The client's request builder, one function code at a time.

send_request() is a thirteen-branch dispatch that turns a function code and a
bag of loosely typed arguments into a PDU. Nothing exercised those branches:
the end-to-end test sends FC1 and the rest were reached only by the manual
test() helper, which asserts nothing. The argument handling at the top is the
subtle part, because the same `values` parameter means a scalar for some
function codes and a sequence for others, and it is normalised by catching a
TypeError from iter().
"""

import unittest

from pyomb.client_simulator import ModbusClientSimulator
from pyomb.errors import ModbusIllegalFunction
from pyomb.packets import (
    ModbusHeader,
    ModbusRequestFC1,
    ModbusRequestFC2,
    ModbusRequestFC3,
    ModbusRequestFC4,
    ModbusRequestFC5,
    ModbusRequestFC6,
    ModbusRequestFC7,
    ModbusRequestFC15,
    ModbusRequestFC16,
    ModbusRequestFC22,
    ModbusRequestFC23,
    ModbusRequestFC43,
    ModbusTcpRequest,
)
from tests.helpers.stub_socket import LoopbackSocket

# One call per supported function code, paired with the PDU class it must
# build. The keyword arguments are the ones that function code actually reads.
REQUEST_TABLE = (
    (1, {"read_address": 4, "read_count": 8}, ModbusRequestFC1),
    (2, {"read_address": 4, "read_count": 8}, ModbusRequestFC2),
    (3, {"read_address": 4, "read_count": 2}, ModbusRequestFC3),
    (4, {"read_address": 4, "read_count": 2}, ModbusRequestFC4),
    (5, {"write_address": 3, "values": [0xFF00]}, ModbusRequestFC5),
    (6, {"write_address": 3, "values": [0xABCD]}, ModbusRequestFC6),
    (7, {}, ModbusRequestFC7),
    (15, {"write_address": 0, "write_count": 8, "values": [0xFF]}, ModbusRequestFC15),
    (16, {"write_address": 0, "write_count": 2, "values": [1, 2]}, ModbusRequestFC16),
    (22, {"write_address": 4, "and_mask": 0x00F2, "or_mask": 0x0025}, ModbusRequestFC22),
    (
        23,
        {"read_address": 0, "read_count": 2, "write_address": 8, "write_count": 1, "values": [0xABCD]},
        ModbusRequestFC23,
    ),
    (43, {}, ModbusRequestFC43),
)


class ClientOnAStubSocket(unittest.TestCase):
    """Builds a client whose socket is a stub rather than a real connection."""

    def make_client(self, **options):
        client = ModbusClientSimulator(**options)

        # The constructor opens a real socket that is never connected here.
        client.sock.close()
        client.sock = LoopbackSocket()

        return client

    def send(self, fc, **kwargs):
        """Sends one request and returns it decoded from the wire."""

        client = self.make_client()
        client.send_request(fc=fc, **kwargs)

        return ModbusTcpRequest.deserialize(client.sock.frame())


class TestFunctionCodeCoverage(ClientOnAStubSocket):
    def test_every_function_code_builds_its_own_request(self):
        for fc, kwargs, pdu_class in REQUEST_TABLE:
            with self.subTest(fc=fc):
                request = self.send(fc, **kwargs)

                self.assertIsInstance(request.pdu, pdu_class)
                self.assertEqual(request.pdu.fc, fc)

    def test_every_request_declares_its_own_length(self):
        # The MBAP length counts the unit identifier plus the PDU. A request
        # that miscounts is rejected by the server's validation.
        for fc, kwargs, _ in REQUEST_TABLE:
            with self.subTest(fc=fc):
                client = self.make_client()
                client.send_request(fc=fc, **kwargs)
                frame = client.sock.frame()

                header = ModbusHeader.deserialize(frame[: ModbusHeader.SIZE])
                self.assertEqual(len(frame), ModbusHeader.SIZE + header.length - 1)

    def test_unsupported_function_code_is_refused(self):
        with self.assertRaises(ModbusIllegalFunction):
            self.send(99, read_address=0, read_count=1)


class TestRequestFields(ClientOnAStubSocket):
    def test_read_requests_carry_the_address_and_the_count(self):
        for fc in (1, 2, 3, 4):
            with self.subTest(fc=fc):
                request = self.send(fc, read_address=0x0013, read_count=7)

                self.assertEqual(request.pdu.start_addr, 0x0013)
                self.assertEqual(request.pdu.quantity, 7)

    def test_fc5_carries_the_address_and_the_value(self):
        request = self.send(5, write_address=0x0003, values=[0xFF00])

        self.assertEqual(request.pdu.output_address, 0x0003)
        self.assertEqual(request.pdu.output_value, 0xFF00)

    def test_fc6_carries_the_address_and_the_value(self):
        request = self.send(6, write_address=0x0003, values=[0xABCD])

        self.assertEqual(request.pdu.output_address, 0x0003)
        self.assertEqual(request.pdu.output_value, 0xABCD)

    def test_fc22_carries_both_masks(self):
        request = self.send(22, write_address=4, and_mask=0x00F2, or_mask=0x0025)

        self.assertEqual(request.pdu.ref_addr, 4)
        self.assertEqual(request.pdu.and_mask, 0x00F2)
        self.assertEqual(request.pdu.or_mask, 0x0025)

    def test_fc23_carries_both_halves_of_the_transaction(self):
        request = self.send(
            23, read_address=3, read_count=6, write_address=14, write_count=3, values=[0x00FF, 0x00FF, 0x00FF]
        )

        self.assertEqual(request.pdu.read_start_addr, 3)
        self.assertEqual(request.pdu.read_quantity, 6)
        self.assertEqual(request.pdu.write_start_addr, 14)
        self.assertEqual(request.pdu.write_quantity, 3)


class TestValueNormalisation(ClientOnAStubSocket):
    """The same parameter means a scalar to some codes and a sequence to others."""

    def test_single_write_takes_the_first_element_of_a_sequence(self):
        # FC5 and FC6 write one value, so a sequence is narrowed rather than
        # rejected.
        for fc in (5, 6):
            with self.subTest(fc=fc):
                request = self.send(fc, write_address=1, values=[0x1234, 0x5678])

                self.assertEqual(request.pdu.output_value, 0x1234)

    def test_single_write_accepts_a_bare_scalar(self):
        for fc in (5, 6):
            with self.subTest(fc=fc):
                request = self.send(fc, write_address=1, values=0x1234)

                self.assertEqual(request.pdu.output_value, 0x1234)

    def test_multiple_write_wraps_a_bare_scalar(self):
        # iter() raises TypeError on a scalar, which is how the wrapping is
        # triggered for the codes that need a sequence.
        request = self.send(16, write_address=0, write_count=1, values=0x00FF)

        self.assertEqual(tuple(request.pdu.values), (0x00FF,))

    def test_multiple_write_keeps_a_sequence(self):
        request = self.send(16, write_address=0, write_count=3, values=[1, 2, 3])

        self.assertEqual(tuple(request.pdu.values), (1, 2, 3))


if __name__ == "__main__":
    unittest.main()
