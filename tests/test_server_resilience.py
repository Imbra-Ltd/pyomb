"""A client that vanishes must not take the server thread with it.

The receive branch of the server loop caught socket.error. ModbusTcpStream
wraps every transport failure in a ModbusBaseError, which is not a
socket.error, so the handler could not fire for the errors that actually reach
it: a reset connection propagated out of run() and ended the thread, leaving
every other client stranded. Had it fired, the first statement inside it was
Python 2 tuple unpacking of the exception object, which raises TypeError on
Python 3 -- so the recovery path was unreachable and broken behind that.

Nothing caught it because nothing had ever disconnected a client abruptly in a
test; every existing case closes politely.
"""

import socket
import struct
import time
import unittest

from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest, ModbusTcpResponse
from pyomb.server_simulator import ModbusServerSimulator


def read_request(address=0, count=8, trans_id=1):
    pdu = ModbusRequestFC1(start_addr=address, quantity=count)
    header = ModbusHeader(trans_id=trans_id, prot_id=0, length=len(pdu) + 1, unit_id=1)

    return ModbusTcpRequest(header=header, pdu=pdu).serialize()


class DeadSocket:
    """A socket whose shutdown fails, as a reset connection's does on Linux.

    Windows stays silent for the same call, so the platform that first ran
    these tests could not produce this and the fault reached CI instead.
    """

    def __init__(self):
        self.closed = False

    def shutdown(self, how):
        raise OSError(107, "Transport endpoint is not connected")

    def close(self):
        self.closed = True


class TestDisconnectToleratesADeadSocket(unittest.TestCase):
    """disconnect() is called on connections that have already gone away.

    It is reached from the error path, so if it raises there is no recovery
    left: the exception leaves forget(), leaves the loop, and ends the thread.
    Its own shutdown() must therefore be allowed to fail.
    """

    def test_disconnect_does_not_raise_when_shutdown_fails(self):
        ModbusServerSimulator().disconnect(DeadSocket())

    def test_socket_is_closed_even_when_shutdown_fails(self):
        # The close is the part that matters; the orderly shutdown is a
        # courtesy to a peer that is no longer listening.
        sock = DeadSocket()

        ModbusServerSimulator().disconnect(sock)

        self.assertTrue(sock.closed)


class TestAbruptDisconnect(unittest.TestCase):
    def setUp(self):
        # The inactivity sweep would otherwise close an idle connection after
        # a second, which these tests would race against.
        #
        # Port 0 asks the operating system for a free one, so a listener the
        # previous test has not finished releasing cannot collide with this
        # one. The port is read back below, once the listener is up.
        self.server = ModbusServerSimulator(port=0, inactiveTimeout=30.0)
        self.server.daemon = True
        self.server.start()

        self.assertTrue(self.server.startedEvent.wait(5.0), "the server never reached its accept loop")

        self.port = self.server.port

    def tearDown(self):
        self.server.stop()
        self.server.join(5.0)

    def connect(self):
        sock = socket.socket()
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", self.port))

        return sock

    def exchange(self, sock, trans_id=1):
        """Sends one request and returns the decoded response."""

        sock.sendall(read_request(trans_id=trans_id))
        header = sock.recv(ModbusHeader.SIZE)
        declared = ModbusHeader.deserialize(header).length - 1

        return ModbusTcpResponse.deserialize(header + sock.recv(declared))

    @staticmethod
    def reset(sock):
        """Closes a socket so the peer sees RST rather than an orderly FIN."""

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        sock.close()

    def test_server_answers_before_the_reset(self):
        # Establishes that the fixture works, so a later failure means the
        # reset and not the setup.
        sock = self.connect()

        try:
            self.assertEqual(self.exchange(sock).pdu.fc, 1)
        finally:
            sock.close()

    def test_reset_connection_does_not_kill_the_server(self):
        sock = self.connect()
        self.exchange(sock)
        self.reset(sock)

        # Give the loop a moment to notice the dead socket.
        time.sleep(0.5)

        self.assertTrue(self.server.is_alive(), "the server thread died handling a reset connection")

    def test_server_keeps_serving_after_a_reset(self):
        # The strongest form: a second client gets a correct answer after the
        # first one vanished. Previously the thread was already gone and this
        # connection was never accepted.
        first = self.connect()
        self.exchange(first)
        self.reset(first)
        time.sleep(0.5)

        second = self.connect()

        try:
            response = self.exchange(second, trans_id=2)

            self.assertEqual(response.pdu.fc, 1)
            self.assertEqual(response.header.trans_id, 2)
        finally:
            second.close()

    def test_reset_before_any_request_does_not_kill_the_server(self):
        # No bytes ever sent, so the loop meets the dead socket on its first
        # read rather than its second.
        sock = self.connect()
        time.sleep(0.2)
        self.reset(sock)
        time.sleep(0.5)

        self.assertTrue(self.server.is_alive())


if __name__ == "__main__":
    unittest.main()
