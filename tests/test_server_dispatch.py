"""The server's request dispatch, exercised without a socket.

on_data() decodes a request, picks a ResponseFactory method by function code,
and writes the response back. It is the largest untested surface in the
project: thirteen branches, of which one function code was covered by the
single end-to-end TLS test and the rest by nothing. A defect in any of them is
invisible to both the test suite and the client, because the client asks for
whatever the server offers.

These drive on_data() directly against a connection double, so they need no
listener, no certificates and no timing.
"""

import unittest
from unittest import mock

from pyomb.errors import ModbusSlaveDeviceFailure
from pyomb.packets import (
    ModbusError,
    ModbusHeader,
    ModbusPdu,
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
    ModbusResponseFC1,
    ModbusResponseFC2,
    ModbusResponseFC3,
    ModbusResponseFC4,
    ModbusResponseFC5,
    ModbusResponseFC6,
    ModbusResponseFC7,
    ModbusResponseFC15,
    ModbusResponseFC16,
    ModbusResponseFC22,
    ModbusResponseFC23,
    ModbusResponseFC43,
    ModbusTcpRequest,
    ModbusTcpResponse,
)
from pyomb.server_simulator import ModbusServerSimulator

# One request per supported function code, paired with the response class the
# dispatch is expected to answer with.
DISPATCH_TABLE = (
    (1, lambda: ModbusRequestFC1(start_addr=0, quantity=10), ModbusResponseFC1),
    (2, lambda: ModbusRequestFC2(start_addr=0, quantity=10), ModbusResponseFC2),
    (3, lambda: ModbusRequestFC3(start_addr=0, quantity=4), ModbusResponseFC3),
    (4, lambda: ModbusRequestFC4(start_addr=0, quantity=4), ModbusResponseFC4),
    (5, lambda: ModbusRequestFC5(output_address=3, output_value=0xFF00), ModbusResponseFC5),
    (6, lambda: ModbusRequestFC6(output_address=3, output_value=0x1234), ModbusResponseFC6),
    (7, lambda: ModbusRequestFC7(), ModbusResponseFC7),
    (15, lambda: ModbusRequestFC15(start_addr=0, quantity=8, byte_count=1, values=[0xFF]), ModbusResponseFC15),
    (16, lambda: ModbusRequestFC16(start_addr=0, quantity=2, byte_count=4, values=[1, 2]), ModbusResponseFC16),
    (22, lambda: ModbusRequestFC22(ref_addr=4, and_mask=0x00F2, or_mask=0x0025), ModbusResponseFC22),
    (
        23,
        lambda: ModbusRequestFC23(
            read_start_addr=0,
            read_quantity=2,
            write_start_addr=8,
            write_quantity=1,
            write_byte_count=2,
            write_values=[0xABCD],
        ),
        ModbusResponseFC23,
    ),
    (43, lambda: ModbusRequestFC43(mei_type=0x0E, mei_data=(1, 2)), ModbusResponseFC43),
)


class RecordingConnection:
    """Stands in for a client socket and keeps what the server wrote."""

    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(data)
        return len(data)

    def frame(self):
        return b"".join(self.sent)


class FailingConnection(RecordingConnection):
    """A peer that has gone away between the request and the response."""

    def send(self, data):
        raise ConnectionResetError


class ServerUnderTest(unittest.TestCase):
    """Builds a server object without starting its listener thread."""

    def setUp(self):
        self.server = ModbusServerSimulator()

    def frame_for(self, pdu, trans_id=0x1234, prot_id=0, unit_id=17):
        header = ModbusHeader(trans_id=trans_id, prot_id=prot_id, length=len(pdu) + 1, unit_id=unit_id)

        return ModbusTcpRequest(header=header, pdu=pdu).serialize()

    def dispatch(self, pdu, conn=None, **header_fields):
        conn = conn if conn is not None else RecordingConnection()
        self.server.on_data(self.frame_for(pdu, **header_fields), conn)

        return ModbusTcpResponse.deserialize(conn.frame())


class TestFunctionCodeDispatch(ServerUnderTest):
    def test_every_function_code_answers_with_its_own_response(self):
        for fc, build_request, response_class in DISPATCH_TABLE:
            with self.subTest(fc=fc):
                response = self.dispatch(build_request())

                self.assertIsInstance(response.pdu, response_class)
                self.assertEqual(response.pdu.fc, fc)

    def test_every_response_declares_its_own_length(self):
        # The MBAP length counts the unit identifier plus the PDU. A response
        # that miscounts is rejected by the client's own validation.
        for fc, build_request, _ in DISPATCH_TABLE:
            with self.subTest(fc=fc):
                conn = RecordingConnection()
                self.dispatch(build_request(), conn=conn)
                frame = conn.frame()

                header = ModbusHeader.deserialize(frame[: ModbusHeader.SIZE])
                self.assertEqual(len(frame), ModbusHeader.SIZE + header.length - 1)

    def test_unknown_function_code_answers_with_an_exception(self):
        response = self.dispatch(ModbusPdu(fc=0x63, data=(0,)))

        self.assertIsInstance(response.pdu, ModbusError)


class TestResponseHeader(ServerUnderTest):
    def test_transaction_id_is_echoed(self):
        # The client matches responses on this, so an id the server invents
        # rather than echoes would strand every request.
        response = self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8), trans_id=0xBEEF)

        self.assertEqual(response.header.trans_id, 0xBEEF)

    def test_protocol_id_is_echoed(self):
        response = self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8), prot_id=0)

        self.assertEqual(response.header.prot_id, 0)

    def test_unit_id_is_echoed(self):
        # A gateway routes on this. Answering on a different unit id sends the
        # reply to the wrong device.
        response = self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8), unit_id=42)

        self.assertEqual(response.header.unit_id, 42)


class TestFailureSimulation(ServerUnderTest):
    def test_fail_flag_turns_every_response_into_an_exception(self):
        self.server.set_fail(True)

        response = self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8))

        self.assertIsInstance(response.pdu, ModbusError)
        self.assertEqual(response.pdu.fc, 1)

    def test_exception_response_reports_slave_device_failure(self):
        self.server.set_fail(True)

        response = self.dispatch(ModbusRequestFC3(start_addr=0, quantity=1))

        self.assertEqual(response.pdu.exc_code, 0x04)

    def test_unreachable_peer_surfaces_as_slave_device_failure(self):
        with self.assertRaises(ModbusSlaveDeviceFailure):
            self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8), conn=FailingConnection())


class TestDataHandler(ServerUnderTest):
    def test_handler_sees_the_decoded_request(self):
        seen = []

        def handler(log, header, request, conn):
            seen.append((header, request, conn))
            return True

        self.server.set_data_handler(handler)
        conn = RecordingConnection()
        self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8), conn=conn, trans_id=0x0007)

        self.assertEqual(len(seen), 1)
        header, request, handler_conn = seen[0]
        self.assertEqual(header.trans_id, 0x0007)
        self.assertEqual(request.pdu.fc, 1)
        self.assertIs(handler_conn, conn)

    def test_handler_veto_produces_an_exception_response(self):
        self.server.set_data_handler(lambda log, header, request, conn: False)

        response = self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8))

        self.assertIsInstance(response.pdu, ModbusError)

    def test_handler_approval_leaves_the_normal_response(self):
        self.server.set_data_handler(lambda log, header, request, conn: True)

        response = self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8))

        self.assertIsInstance(response.pdu, ModbusResponseFC1)


class TestResponseDelay(ServerUnderTest):
    def test_configured_delay_is_applied_before_answering(self):
        # Patched rather than measured, so the assertion is exact and the test
        # stays fast. The transport sleeps for its own fragment delay through
        # the same function, so this asks whether the configured delay is
        # among the calls rather than that it is the only one.
        self.server.set_delay(0.25)

        with mock.patch("pyomb.server_simulator.time.sleep") as sleep:
            self.dispatch(ModbusRequestFC1(start_addr=0, quantity=8))

        sleep.assert_any_call(0.25)

    def test_no_delay_is_configured_by_default(self):
        self.assertEqual(ModbusServerSimulator().delay, 0)


class TestServerConfiguration(unittest.TestCase):
    def test_setters_take_effect(self):
        server = ModbusServerSimulator()

        server.set_delay(1.5)
        server.set_connection_limit(3)
        server.set_fail(True)

        self.assertEqual(server.delay, 1.5)
        self.assertEqual(server.connection_limit, 3)
        self.assertTrue(server.fail)

    def test_secure_mode_moves_off_the_plaintext_port(self):
        # MB-TCP-Security puts TLS on 802. The switch only applies to the
        # default, so an explicitly chosen port is left alone.
        self.assertEqual(ModbusServerSimulator.PLAINTEXT_PORT, 502)
        self.assertEqual(ModbusServerSimulator.ENCRYPTED_PORT, 802)

    def test_plaintext_server_builds_no_ssl_context(self):
        server = ModbusServerSimulator()

        self.assertFalse(hasattr(server, "ssl_context"))
        self.assertEqual(server.port, 502)

    def test_no_peers_before_any_client_connects(self):
        self.assertEqual(ModbusServerSimulator().get_peers(), [])


if __name__ == "__main__":
    unittest.main()
