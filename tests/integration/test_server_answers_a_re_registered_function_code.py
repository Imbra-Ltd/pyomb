"""Replacing a built-in PDU class must not cost the caller their connection.

ModbusPduParser.register is public and documented as the way to model a PDU
shape this library does not carry. Registering against a function code the
server already answers is therefore supported, and it used to drop the
connection: the server dispatched on the function code field, the factory
behind that branch read a field only the built-in class declares, and the
registry is what a caller had just retied.

The AttributeError became a slave-device failure, which retires the
connection. The peer got a closed socket for a request the server had
understood well enough to route.
"""

import socket
import struct
import unittest

from pyomb.packets import (
    ModbusHeader,
    ModbusPdu,
    ModbusPduParser,
    ModbusRequestFC1,
    ModbusTcpRequest,
    ModbusTcpResponse,
)
from pyomb.server_simulator import ModbusServerSimulator


class CoilRequestWithoutQuantity(ModbusPdu):
    """A caller's own shape for function code 1, carrying no quantity field.

    It reads the same five bytes off the wire as the built-in class, so the
    frame parses and the server routes it. What it does not have is the
    quantity field the FC1 response factory reads.
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x0001
    PDU_FIELDS = ("start_addr", "spare")

    def __init__(self, start_addr: int, spare: int) -> None:
        """Keep the address and whatever the last two bytes carried."""
        self.start_addr = start_addr
        self.spare = spare

        super().__init__(fc=0x01)

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the PDU to a stream of bytes.

        Returns:
            bytes : The serialized PDU
        """

        return self._pack(self.PDU_FORMAT)

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the PDU from a stream of bytes.

        Args:
            stream (bytes) : The stream of bytes to deserialize

        Returns:
            CoilRequestWithoutQuantity : The deserialized PDU
        """

        pdu = struct.unpack(cls.PDU_FORMAT, stream)

        return cls(start_addr=pdu[1], spare=pdu[2])


class ServerAnswersARegisteredClassItCannotSatisfy(unittest.TestCase):
    """One connection, one FC1 request, and a registry the caller has retied."""

    def setUp(self):
        # The registry is class state shared by every test in the process, so
        # the built-in class is put back in tearDown whatever happens here.
        ModbusPduParser.register(CoilRequestWithoutQuantity)

        self.server = ModbusServerSimulator(port=0, inactive_timeout=30.0)
        self.server.daemon = True
        self.server.start()

        self.assertTrue(self.server.started_event.wait(5.0), "the server never reached its accept loop")

        self.sock = socket.socket()
        self.sock.settimeout(5.0)
        self.sock.connect(("127.0.0.1", self.server.port))

    def tearDown(self):
        ModbusPduParser.register(ModbusRequestFC1)

        self.sock.close()
        self.server.stop()
        self.server.join(5.0)

    def send_fc1_request(self):
        """Send a well-formed FC1 request, whatever class is registered for it."""

        body = struct.pack(">BHH", 0x01, 0, 8)
        header = ModbusHeader(trans_id=3, prot_id=0, length=len(body) + 1, unit_id=1)

        self.sock.sendall(header.serialize() + body)

    def read_reply(self):
        """Read one complete response ADU off the socket.

        Returns:
            bytes : The serialized response
        """

        header = self.sock.recv(ModbusHeader.SIZE)
        declared = ModbusHeader.deserialize(header).length - 1

        return header + self.sock.recv(declared)

    def test_the_registry_is_what_the_parser_reads(self):
        # The control. Without it every assertion below passes against a
        # register() that silently did nothing.
        parsed = ModbusPduParser.parse_request(struct.pack(">BHH", 0x01, 0, 8))

        self.assertIsInstance(parsed, CoilRequestWithoutQuantity)

    def test_a_request_it_cannot_satisfy_gets_an_exception_response(self):
        self.send_fc1_request()

        response = ModbusTcpResponse.deserialize(self.read_reply())

        # 0x81 is function code 1 with the error mask, and 0x04 says the
        # server understood the request and could not perform it.
        self.assertEqual(response.pdu.fc, 0x01)
        self.assertEqual(response.pdu.exc_code, 0x04)

    def test_the_exception_response_echoes_the_transaction(self):
        self.send_fc1_request()

        response = ModbusTcpResponse.deserialize(self.read_reply())

        self.assertEqual(response.header.trans_id, 3)
        self.assertEqual(response.header.unit_id, 1)

    def test_the_connection_survives_it(self):
        self.send_fc1_request()
        self.read_reply()

        self.assertEqual(self.server.get_peers(), [self.sock.getsockname()])

    def test_the_built_in_class_is_answered_normally_once_restored(self):
        # The other side of the control: the same bytes earn a real response
        # once the built-in class is back, so the registry is what did it.
        ModbusPduParser.register(ModbusRequestFC1)

        pdu = ModbusRequestFC1(start_addr=0, quantity=8)
        header = ModbusHeader(trans_id=3, prot_id=0, length=len(pdu) + 1, unit_id=1)
        self.sock.sendall(ModbusTcpRequest(header=header, pdu=pdu).serialize())

        response = ModbusTcpResponse.deserialize(self.read_reply())

        self.assertEqual(response.pdu.fc, 0x01)
        self.assertFalse(hasattr(response.pdu, "exc_code"))


if __name__ == "__main__":
    unittest.main()
