"""The client must not block forever on a peer that never replies.

A server that accepts a connection and then goes silent used to hang the
caller indefinitely: the socket carried no timeout, so recv blocked with no
way to recover short of killing the process. These tests hold the finite
default in place and check that the timeout surfaces as a Modbus error.
"""

import contextlib
import socket
import threading
import unittest

from pyomb.client_simulator import ModbusClientSimulator
from pyomb.errors import ModbusNetworkError


class SilentServer:
    """Accepts one connection, reads nothing, answers nothing."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.accepted = None
        self.thread = threading.Thread(target=self._serve)
        self.thread.daemon = True
        self.thread.start()

    def _serve(self):
        with contextlib.suppress(OSError):
            self.accepted, _ = self.sock.accept()

    def close(self):
        for handle in (self.accepted, self.sock):
            if handle is not None:
                with contextlib.suppress(OSError):
                    handle.close()


class TestClientTimeout(unittest.TestCase):
    def setUp(self):
        self.server = SilentServer()

    def tearDown(self):
        self.server.close()

    def test_default_timeout_is_finite(self):
        self.assertIsNotNone(ModbusClientSimulator.DEFAULT_TIMEOUT)
        self.assertGreater(ModbusClientSimulator.DEFAULT_TIMEOUT, 0)

    def test_socket_carries_the_timeout_before_connect(self):
        client = ModbusClientSimulator(timeout=2.5)

        self.assertEqual(client.sock.gettimeout(), 2.5)

    def test_unanswered_request_raises_instead_of_hanging(self):
        client = ModbusClientSimulator(host="127.0.0.1", port=self.server.port, timeout=0.5)
        client.connect()

        try:
            with self.assertRaises(ModbusNetworkError):
                client.request(fc=1, readAddress=0, readCount=1)
        finally:
            client.disconnect()

    def test_timeout_is_configurable(self):
        client = ModbusClientSimulator(host="127.0.0.1", port=self.server.port, timeout=0.25)
        client.connect()

        try:
            self.assertEqual(client.sock.gettimeout(), 0.25)
        finally:
            client.disconnect()

    def test_none_restores_blocking_behaviour(self):
        client = ModbusClientSimulator(timeout=None)

        self.assertIsNone(client.sock.gettimeout())


if __name__ == "__main__":
    unittest.main()
