"""A disconnected client refuses socket work by name, and tears down twice.

`disconnect()` closes the socket and clears the attribute, so every operation
that reaches for one afterwards used to fail on `NoneType` -- an AttributeError
raised from inside the library, naming a private attribute rather than the
mistake the caller made. The attribute is optional now, which is what its own
teardown path always implied, and each of those operations reports
`ModbusNetworkError` instead.

Tearing down twice is the ordinary case rather than a fault: a caller that
cannot tell whether it already disconnected has to be able to ask again. So
`disconnect()` returns quietly on a client that holds no socket, while the
operations that need one refuse.
"""

import contextlib
import socket
import struct
import unittest

from pyomb.errors import ModbusNetworkError
from pyomb.omb_client import OmbClientSim


def disconnected_client():
    """A client whose socket has been closed and cleared.

    Returns:
        OmbClientSim : The client, holding no socket
    """

    client = OmbClientSim(host=b"127.0.0.1", port=502)
    client.disconnect()

    return client


class TeardownIsIdempotent(unittest.TestCase):
    """Asking a disconnected client to disconnect is answered, not refused."""

    def test_the_socket_is_cleared_rather_than_left_closed(self):
        client = disconnected_client()

        self.assertIsNone(client.sock)

    def test_disconnecting_twice_raises_nothing(self):
        client = disconnected_client()

        client.disconnect()

        self.assertIsNone(client.sock)

    def test_disconnecting_many_times_raises_nothing(self):
        """Idempotence is the property, not a second call being special."""

        client = disconnected_client()

        for _ in range(3):
            client.disconnect()

        self.assertIsNone(client.sock)


class SocketWorkIsRefusedByName(unittest.TestCase):
    """Each operation needing a live socket reports the library's own error."""

    def setUp(self):
        self.client = disconnected_client()

    def test_send_raw_is_refused(self):
        with self.assertRaises(ModbusNetworkError):
            self.client.send_raw(b"\x00")

    def test_recv_raw_is_refused(self):
        with self.assertRaises(ModbusNetworkError):
            self.client.recv_raw(1)

    def test_set_socket_timeout_is_refused(self):
        with self.assertRaises(ModbusNetworkError):
            self.client.set_socket_timeout(1)

    def test_set_socket_options_is_refused(self):
        with self.assertRaises(ModbusNetworkError):
            self.client.set_socket_options(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)

    def test_reading_the_receive_buffer_size_is_refused(self):
        with self.assertRaises(ModbusNetworkError):
            _ = self.client.recvbuf_size

    def test_setting_the_receive_buffer_size_is_refused(self):
        with self.assertRaises(ModbusNetworkError):
            self.client.recvbuf_size = 4096

    def test_reset_is_refused(self):
        with self.assertRaises(ModbusNetworkError):
            self.client.reset()

    def test_the_message_names_the_remedy_rather_than_the_attribute(self):
        """An AttributeError on a private name tells the caller nothing."""

        with self.assertRaises(ModbusNetworkError) as raised:
            self.client.send_raw(b"\x00")

        self.assertIn("connect", str(raised.exception))


class ConnectingAgainBuildsANewSocket(unittest.TestCase):
    """The cleared attribute is why connect() has to check for one."""

    def setUp(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.accepted = None

    def tearDown(self):
        for handle in (self.accepted, self.listener):
            if handle is not None:
                # A peer that has gone away is the ordinary case on this path
                with contextlib.suppress(OSError):
                    handle.close()

    def test_a_disconnected_client_can_connect_again(self):
        client = disconnected_client()

        client.connect(host="127.0.0.1", port=self.port)
        self.accepted, _ = self.listener.accept()

        try:
            self.assertIsNotNone(client.sock)

            # The new socket carries the client's timeout, which is what says
            # it went through connect() rather than surviving the teardown
            self.assertEqual(client.sock.gettimeout(), client.timeout)

            client.send_raw(struct.pack(">B", 0))
        finally:
            client.disconnect()


if __name__ == "__main__":
    unittest.main()
