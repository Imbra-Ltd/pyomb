"""A peer whose MBAP header parsed is told what was wrong with the rest.

The server used to drop any frame it could not parse. A client then saw a
closed socket, which is a network fault, and could not tell a malformed
request from a crashed server -- the one distinction this library exists to
let somebody test.

The header is what decides whether an answer is possible: it carries the
transaction, protocol and unit identifiers a response echoes. These tests pin
the answering half. The dropping half, where nothing survived to echo, stays
with the tests for surviving the frame at all.
"""

import socket
import unittest

from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest, ModbusTcpResponse
from pyomb.server_simulator import ModbusServerSimulator

# Transaction 1, protocol 0, length 4, unit 1, then an FC1 body two bytes
# short. The MBAP length agrees with the ADU, so only the PDU is malformed.
SHORT_FC1_REQUEST = bytes.fromhex("000100000004") + bytes([1]) + bytes([1, 0, 0])

# Written out rather than through the library, so the two cannot agree on a
# wrong answer: v1.1b3 section 7, function code plus 0x80, then 0x03.
EXPECTED_EXCEPTION_REPLY = bytes.fromhex("000100000003") + bytes([1]) + bytes([0x81, 0x03])


class ServerAnswersABadPdu(unittest.TestCase):
    """One connection, one bad frame, and what comes back on it."""

    def setUp(self):
        # The inactivity sweep would otherwise close an idle connection after
        # a second, which these tests would race against. Port 0 per PLAYBOOK 3.1.
        self.server = ModbusServerSimulator(port=0, inactive_timeout=30.0)
        self.server.daemon = True
        self.server.start()

        self.assertTrue(self.server.started_event.wait(5.0), "the server never reached its accept loop")

        self.sock = socket.socket()
        self.sock.settimeout(5.0)
        self.sock.connect(("127.0.0.1", self.server.port))

    def tearDown(self):
        self.sock.close()
        self.server.stop()
        self.server.join(5.0)

    def read_reply(self):
        """Read one complete response ADU off the socket.

        Never treat one recv() as one frame: read the header, then exactly the
        number of bytes its length field declares.

        Returns:
            bytes : The serialized response
        """

        header = self.sock.recv(ModbusHeader.SIZE)
        declared = ModbusHeader.deserialize(header).length - 1

        return header + self.sock.recv(declared)

    def test_the_reply_is_the_exception_response_the_specification_defines(self):
        self.sock.sendall(SHORT_FC1_REQUEST)

        self.assertEqual(self.read_reply(), EXPECTED_EXCEPTION_REPLY)

    def test_the_reply_echoes_the_identifiers_the_request_carried(self):
        # A client matches a response to its request by transaction
        # identifier, so a reply carrying the wrong one is unusable.
        self.sock.sendall(SHORT_FC1_REQUEST)

        response = ModbusTcpResponse.deserialize(self.read_reply())

        self.assertEqual(response.header.trans_id, 1)
        self.assertEqual(response.header.prot_id, 0)
        self.assertEqual(response.header.unit_id, 1)

    def test_the_connection_answers_a_good_request_after_a_bad_one(self):
        # The point of replying rather than dropping: the client is still
        # there afterwards and can carry on.
        self.sock.sendall(SHORT_FC1_REQUEST)
        self.read_reply()

        pdu = ModbusRequestFC1(start_addr=0, quantity=8)
        header = ModbusHeader(trans_id=7, prot_id=0, length=len(pdu) + 1, unit_id=1)
        self.sock.sendall(ModbusTcpRequest(header=header, pdu=pdu).serialize())

        response = ModbusTcpResponse.deserialize(self.read_reply())

        self.assertEqual(response.pdu.fc, 1)
        self.assertEqual(response.header.trans_id, 7)

    def test_a_well_formed_request_is_not_answered_with_an_exception(self):
        # The control. Without it every assertion above passes against a
        # server that answers 0x81 0x03 to everything.
        pdu = ModbusRequestFC1(start_addr=0, quantity=8)
        header = ModbusHeader(trans_id=1, prot_id=0, length=len(pdu) + 1, unit_id=1)
        self.sock.sendall(ModbusTcpRequest(header=header, pdu=pdu).serialize())

        self.assertNotEqual(self.read_reply(), EXPECTED_EXCEPTION_REPLY)


if __name__ == "__main__":
    unittest.main()
