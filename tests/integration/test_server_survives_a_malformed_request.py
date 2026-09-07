"""A frame the server cannot parse must not take the server thread with it.

run() called on_data from the else: branch of the try that reads the socket.
An else: branch is not covered by its own statement's except clauses, so
everything on_data raised left run() and ended the thread. Seven bytes from
any client stopped the server for every other client, and nothing raised in
the caller's thread -- the traceback went to stderr, where a harness does not
look.

Three doors reach that branch, and only two of them raise a ModbusBaseError.
The third is the caller's own data_handler, which on_data invokes above its
try, so a handler that raises is the case a narrowed except would miss.
"""

import socket
import time
import unittest

from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest, ModbusTcpResponse
from pyomb.server_simulator import ModbusServerSimulator

# Transaction 1, protocol 0, length 4, unit 1, then an FC1 body two bytes
# short. The MBAP length agrees with the ADU, so only the PDU is malformed.
SHORT_FC1_REQUEST = bytes.fromhex("000100000004") + bytes([1]) + bytes([1, 0, 0])

# Written out rather than through the library, so the two cannot agree on a
# wrong answer: v1.1b3 section 7, function code plus 0x80, then 0x03.
EXPECTED_EXCEPTION_REPLY = bytes.fromhex("000100000003") + bytes([1]) + bytes([0x81, 0x03])

# How long the loop is given to notice a dropped connection. The server sweeps
# on its own cadence, so this is a settle, not a wait on an event.
SETTLE = 0.5


def read_request(address=0, count=8, trans_id=1):
    """Build a well-formed FC1 request the server is expected to answer.

    Args:
        address (int)   : The starting coil address
        count (int)     : The number of coils to read
        trans_id (int)  : The transaction identifier to carry

    Returns:
        bytes : The serialized Modbus TCP request
    """

    pdu = ModbusRequestFC1(start_addr=address, quantity=count)
    header = ModbusHeader(trans_id=trans_id, prot_id=0, length=len(pdu) + 1, unit_id=1)

    return ModbusTcpRequest(header=header, pdu=pdu).serialize()


class ServerSurvivesABadFrame(unittest.TestCase):
    """The reproduction from the report, and the client that follows it."""

    def setUp(self):
        # The inactivity sweep would otherwise close an idle connection after
        # a second, which these tests would race against. Port 0 per PLAYBOOK 3.1.
        self.server = ModbusServerSimulator(port=0, inactive_timeout=30.0)
        self.server.daemon = True
        self.server.start()

        self.assertTrue(self.server.started_event.wait(5.0), "the server never reached its accept loop")

        self.port = self.server.port

    def tearDown(self):
        self.server.stop()
        self.server.join(5.0)

    def connect(self):
        """Open a client socket to the simulator under test.

        Returns:
            socket.socket : The connected socket
        """

        sock = socket.socket()
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", self.port))

        return sock

    def exchange(self, sock, trans_id=1):
        """Send one well-formed request and return the decoded response.

        Args:
            sock (socket.socket)    : The connected client socket
            trans_id (int)          : The transaction identifier to carry

        Returns:
            ModbusTcpResponse : The decoded response
        """

        sock.sendall(read_request(trans_id=trans_id))
        header = sock.recv(ModbusHeader.SIZE)
        declared = ModbusHeader.deserialize(header).length - 1

        return ModbusTcpResponse.deserialize(header + sock.recv(declared))

    def read_reply(self, sock):
        """Read one complete response ADU off the socket.

        Never treat one recv() as one frame: read the header, then exactly the
        number of bytes its length field declares.

        Args:
            sock (socket.socket) : The connected client socket

        Returns:
            bytes : The serialized response
        """

        header = sock.recv(ModbusHeader.SIZE)
        declared = ModbusHeader.deserialize(header).length - 1

        return header + sock.recv(declared)

    def send_bad_frame(self):
        """Deliver the malformed request and let the loop react to it."""

        sock = self.connect()

        try:
            sock.sendall(SHORT_FC1_REQUEST)
            time.sleep(SETTLE)
        finally:
            sock.close()

    def test_server_answers_before_the_bad_frame(self):
        # Establishes that the fixture works, so a later failure means the
        # malformed frame and not the setup.
        sock = self.connect()

        try:
            self.assertEqual(self.exchange(sock).pdu.fc, 1)
        finally:
            sock.close()

    def test_bad_frame_does_not_kill_the_server(self):
        self.send_bad_frame()

        self.assertTrue(self.server.is_alive(), "the server thread died parsing a malformed request")

    def test_server_keeps_serving_after_a_bad_frame(self):
        # The strongest form: a second client is answered after the first sent
        # nonsense. The thread was previously gone and never accepted it.
        self.send_bad_frame()

        second = self.connect()

        try:
            response = self.exchange(second, trans_id=2)
        finally:
            second.close()

        self.assertEqual(response.pdu.fc, 1)
        self.assertEqual(response.header.trans_id, 2)

    def test_the_sender_of_a_bad_frame_is_answered_and_kept(self):
        # This required the sender to be retired until the server learned to
        # answer: it replies once now, rather than swallowing and spinning.
        sock = self.connect()

        try:
            sock.sendall(SHORT_FC1_REQUEST)
            reply = self.read_reply(sock)

            self.assertEqual(self.server.get_peers(), [sock.getsockname()])
        finally:
            sock.close()

        self.assertEqual(reply, EXPECTED_EXCEPTION_REPLY)


class ServerSurvivesAFailingDataHandler(unittest.TestCase):
    """The door that is not a ModbusBaseError.

    on_data calls the caller's data_handler above its own try, so whatever the
    handler raises travels out untouched. A guard narrowed to the protocol
    error types would let this one through and re-file the same defect.
    """

    def setUp(self):
        self.server = ModbusServerSimulator(port=0, inactive_timeout=30.0)
        self.server.daemon = True
        self.server.data_handler = self.explode
        self.server.start()

        self.assertTrue(self.server.started_event.wait(5.0), "the server never reached its accept loop")

        self.port = self.server.port

    def tearDown(self):
        self.server.stop()
        self.server.join(5.0)

    @staticmethod
    def explode(log, header, request, conn):
        """Fail the way a caller's own handler fails: with anything at all."""

        message = "the handler under test always fails"
        raise ValueError(message)

    def test_a_raising_data_handler_does_not_kill_the_server(self):
        sock = socket.socket()
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", self.port))

        try:
            sock.sendall(read_request())
            time.sleep(SETTLE)
        finally:
            sock.close()

        self.assertTrue(self.server.is_alive(), "the server thread died inside the caller's data handler")


if __name__ == "__main__":
    unittest.main()
