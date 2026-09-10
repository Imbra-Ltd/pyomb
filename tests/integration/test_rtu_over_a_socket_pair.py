"""The RTU stream over a socket's file object: RTU over TCP with no class of its own.

`socketpair()` hands out two connected sockets, and `makefile("rwb",
buffering=0)` turns each into a read/write object. Its `read` returns after one
`recv` rather than filling the size asked for, and raises `socket.timeout`
rather than returning short -- the two port behaviours the stream tolerates
beside pyserial's, and the cheapest second implementation of the port protocol
to hold it to.
"""

import socket
import unittest

from pyomb.errors import ModbusTimeoutError
from pyomb.transport import ModbusRtuStream, RtuSide

# 11 03 00 6B 00 03 -- read three holding registers from 0x006B on slave 17,
# and the three registers coming back. Both are published vectors.
FC3_REQUEST = b"\x11\x03\x00\x6b\x00\x03\x76\x87"
FC3_RESPONSE = b"\x11\x03\x06\xae\x41\x56\x52\x43\x40\x49\xad"

# Seconds either end waits on a read. Short, because the timeout test pays it.
TIMEOUT = 0.5


class TestRtuOverASocketPair(unittest.TestCase):
    def setUp(self):
        self.client_sock, self.server_sock = socket.socketpair()
        self.client_sock.settimeout(TIMEOUT)
        self.server_sock.settimeout(TIMEOUT)
        self.client_port = self.client_sock.makefile("rwb", buffering=0)
        self.server_port = self.server_sock.makefile("rwb", buffering=0)

    def tearDown(self):
        for closing in (self.client_port, self.server_port, self.client_sock, self.server_sock):
            closing.close()

    def test_a_frame_written_on_one_end_is_read_whole_on_the_other(self):
        ModbusRtuStream(port=self.client_port, side=RtuSide.RESPONSE).send(FC3_REQUEST)

        received = ModbusRtuStream(port=self.server_port, side=RtuSide.REQUEST).receive()

        self.assertEqual(received, FC3_REQUEST)

    def test_a_request_and_its_reply_cross_the_pair(self):
        client = ModbusRtuStream(port=self.client_port, side=RtuSide.RESPONSE)
        server = ModbusRtuStream(port=self.server_port, side=RtuSide.REQUEST)

        client.send(FC3_REQUEST)
        self.assertEqual(server.receive(), FC3_REQUEST)

        server.send(FC3_RESPONSE)
        self.assertEqual(client.receive(), FC3_RESPONSE)

    def test_silence_on_the_socket_is_a_timeout(self):
        stream = ModbusRtuStream(port=self.client_port, side=RtuSide.RESPONSE)

        self.assertRaises(ModbusTimeoutError, stream.receive)


if __name__ == "__main__":
    unittest.main()
