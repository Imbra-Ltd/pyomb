"""The accept path, the connection limit, and the manual-accept mode.

These are the branches of run() that no test reached, and each held a defect.
The connection limit left the run loop instead of refusing the connection, so
any peer could end the server, and every established session with it, by
opening one socket more than the limit. accept() reported the server's own
address as the peer's. reset() raised on the first client that had already
disconnected, because the live-client list was appended to on every accept and
never pruned.
"""

import itertools
import socket
import threading
import time
import unittest

from pyomb.errors import ModbusNetworkError
from pyomb.omb_server import OmbServerSim


class ServerThreadExceptions(object):
    """Captures anything that escapes a thread while it is installed."""

    def __init__(self):
        self.caught = []
        self._previous = None

    def __enter__(self):
        self._previous = threading.excepthook
        threading.excepthook = self.caught.append

        return self

    def __exit__(self, *exc_info):
        threading.excepthook = self._previous

        return False

    def describe(self):
        return ", ".join("{0}: {1}".format(type(a.exc_value).__name__, a.exc_value) for a in self.caught)


# Ports are handed out from one module-level counter. A counter on the base
# class does not work: `type(self).port_counter += 1` writes the attribute onto
# each subclass, so every subclass restarts from the inherited value and they
# collide. On Linux the second bind then fails while the first port lingers.
_next_port = itertools.count(20200)


class ServerFixture(unittest.TestCase):
    """One server per test on its own port, with the sockets cleaned up."""

    def setUp(self):
        self.port = next(_next_port)
        self.sockets = []
        self.server = None

    def tearDown(self):
        for sock in self.sockets:
            try:
                sock.close()
            except OSError:
                pass

        if self.server is not None:
            self.server.stop()
            self.server.join(5.0)

    def start_server(self, process_connections=True, **options):
        options.setdefault("inactiveTimeout", 30.0)
        self.server = OmbServerSim(port=self.port, **options)
        self.server.daemon = True
        self.server.start(process_connections=process_connections)

        self.assertTrue(self.server.startedEvent.wait(5.0), "the server never reached its accept loop")

        return self.server

    def connect(self):
        sock = socket.socket()
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", self.port))
        self.sockets.append(sock)

        return sock

    @staticmethod
    def exchange(sock):
        """Sends a Report Slave ID request and returns the raw reply."""

        sock.sendall(b"\x00\x01\x00\x00\x00\x02\x01\x07")

        return sock.recv(256)


class TestConnectionLimit(ServerFixture):
    def test_exceeding_the_limit_does_not_stop_the_server(self):
        # Previously the third client ended the run loop.
        with ServerThreadExceptions() as errors:
            self.start_server(connLimit=2)

            for _ in range(4):
                try:
                    self.connect()
                except OSError:
                    pass
                time.sleep(0.3)

            self.assertTrue(self.server.is_alive(), "server died: " + errors.describe())

    def test_established_sessions_survive_a_refused_connection(self):
        # The collateral damage is the point: the limit used to abort the very
        # sessions it exists to protect.
        self.start_server(connLimit=2)
        first = self.connect()
        self.exchange(first)
        self.connect()

        for _ in range(2):
            try:
                self.connect()
            except OSError:
                pass
            time.sleep(0.3)

        self.assertTrue(self.exchange(first), "an established session was dropped by the limit")

    def test_the_limit_admits_exactly_its_number_of_clients(self):
        # The comparison counted the listening socket, so the limit tripped one
        # client later than its name.
        self.start_server(connLimit=3)

        for _ in range(5):
            try:
                self.connect()
            except OSError:
                pass
            time.sleep(0.3)

        self.assertEqual(len(self.server.getPeers()), 3)

    def test_a_refused_client_is_closed_rather_than_left_hanging(self):
        self.start_server(connLimit=1)
        self.connect()
        time.sleep(0.3)

        refused = self.connect()
        time.sleep(0.5)

        # The peer closed it, so the read returns end-of-stream rather than
        # blocking until the socket timeout.
        self.assertEqual(refused.recv(16), b"")


class TestStartup(ServerFixture):
    def test_start_reports_a_port_it_cannot_bind(self):
        # start() used to spin on the started event with no timeout and no
        # liveness check. A port already in use stops run() before it binds, so
        # the event never arrived and the caller hung for good, with the reason
        # on stderr where nothing could act on it.
        blocker = socket.socket()
        blocker.bind(("", self.port))
        blocker.listen(1)
        self.sockets.append(blocker)

        self.server = OmbServerSim(port=self.port)
        self.server.daemon = True

        with self.assertRaises(ModbusNetworkError):
            self.server.start(timeout=3.0)

    def test_start_gives_up_quickly_when_the_thread_is_gone(self):
        # The liveness check should end the wait well inside the timeout.
        blocker = socket.socket()
        blocker.bind(("", self.port))
        blocker.listen(1)
        self.sockets.append(blocker)

        self.server = OmbServerSim(port=self.port)
        self.server.daemon = True
        started = time.time()

        with self.assertRaises(ModbusNetworkError):
            self.server.start(timeout=30.0)

        self.assertLess(time.time() - started, 5.0)


class TestManualAccept(ServerFixture):
    def test_accept_reports_the_peer_address(self):
        # Previously reported the server's own address, identical for every
        # client.
        self.start_server(process_connections=False)
        client = self.connect()
        time.sleep(0.4)

        conn, addr = self.server.accept(2.0)

        self.assertIsNotNone(conn)
        self.assertEqual(addr, client.getsockname())
        self.assertNotEqual(addr, conn.getsockname())

    def test_accept_returns_a_pair_when_nothing_arrives(self):
        # Previously a bare None, so `conn, addr = accept(t)` raised TypeError.
        self.start_server(process_connections=False)

        conn, addr = self.server.accept(0.3)

        self.assertIsNone(conn)
        self.assertIsNone(addr)

    def test_accept_waits_after_an_earlier_connection(self):
        # The event stayed set from the previous accept, so the next wait
        # returned at once and reported no client.
        self.start_server(process_connections=False)
        self.connect()
        time.sleep(0.4)
        self.server.accept(2.0)

        started = time.time()
        self.server.accept(0.5)

        self.assertGreaterEqual(time.time() - started, 0.4)

    def test_accept_is_refused_in_processing_mode(self):
        self.start_server(process_connections=True)

        with self.assertRaises(Exception):
            self.server.accept(0.1)


class TestReset(ServerFixture):
    def test_reset_tolerates_a_client_that_already_left(self):
        # One normal disconnect used to make reset() unusable for the rest.
        self.start_server()
        first = self.connect()
        self.exchange(first)
        first.close()
        time.sleep(0.6)

        self.server.reset()

    def test_reset_clears_the_live_client_list(self):
        self.start_server()
        self.connect()
        time.sleep(0.4)

        self.server.reset()

        self.assertEqual(self.server.clients, [])

    def test_a_departed_client_is_dropped_from_the_live_list(self):
        # forget() now retires a connection from the client list too, so it
        # tracks the live set rather than every connection ever accepted.
        self.start_server()
        client = self.connect()
        self.exchange(client)
        self.assertEqual(len(self.server.clients), 1)

        client.close()
        time.sleep(0.8)

        self.assertEqual(self.server.clients, [])


if __name__ == "__main__":
    unittest.main()
