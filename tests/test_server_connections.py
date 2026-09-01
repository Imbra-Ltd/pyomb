"""The accept path, the connection limit, and the manual-accept mode.

These are the branches of run() that no test reached, and each held a defect.
The connection limit left the run loop instead of refusing the connection, so
any peer could end the server, and every established session with it, by
opening one socket more than the limit. accept() reported the server's own
address as the peer's. reset() raised on the first client that had already
disconnected, because the live-client list was appended to on every accept and
never pruned.
"""

import contextlib
import socket
import threading
import time
import unittest

from pyomb.errors import ModbusModeError, ModbusNetworkError
from pyomb.server_simulator import ModbusServerSimulator


class ServerThreadExceptions:
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
        return ", ".join(f"{type(a.exc_value).__name__}: {a.exc_value}" for a in self.caught)


class ServerFixture(unittest.TestCase):
    """One server per test on its own port, with the sockets cleaned up."""

    def setUp(self):
        # 0 asks the operating system for a free port, so nothing here can
        # collide with a parallel run, a repeated run, or another process. The
        # real port is only known once the listener is up, so start_server
        # reads it back and every caller must start the server before dialling
        # it. A counter cannot do this: the previous one was module-level
        # precisely because `type(self).port_counter += 1` writes the attribute
        # onto each subclass, restarting every subclass from the inherited
        # value, and even the module-level form only made a collision unlikely.
        self.port = 0
        self.sockets = []
        self.server = None

    def tearDown(self):
        for sock in self.sockets:
            with contextlib.suppress(OSError):
                sock.close()

        if self.server is not None:
            self.server.stop()
            self.server.join(5.0)

    def start_server(self, process_connections=True, **options):
        options.setdefault("inactiveTimeout", 30.0)
        self.server = ModbusServerSimulator(port=self.port, **options)
        self.server.daemon = True
        self.server.start(process_connections=process_connections)

        self.assertTrue(self.server.startedEvent.wait(5.0), "the server never reached its accept loop")

        self.port = self.server.port

        return self.server

    def connect(self):
        sock = socket.socket()
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", self.port))
        self.sockets.append(sock)

        return sock

    def occupy_a_port(self):
        """Binds a listener and returns its port, so a server given that port cannot bind."""

        # Taking the port from the operating system and holding it beats naming
        # one: a guessed port is only occupied if nothing else got there first,
        # which is the assumption these tests exist to stop relying on.
        #
        # The empty host binds every interface on purpose. The point is to hold
        # the port rather than to serve on it, and the server under test binds
        # every interface too at its default, so the blocker has to cover the
        # same set for the collision to be guaranteed. Narrowing it to loopback
        # makes the test platform-dependent: Linux refuses a later wildcard bind
        # over a loopback-only holder, Windows allows it, and there the server
        # would start cleanly and the test would prove nothing.
        #
        # CodeQL reports this as py/bind-socket-all-network-interfaces. It is
        # dismissed there as used in tests, and the reason is written here as
        # well so it survives migrating off that platform.
        blocker = socket.socket()
        blocker.bind(("", 0))
        blocker.listen(1)
        self.sockets.append(blocker)

        return blocker.getsockname()[1]

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
                with contextlib.suppress(OSError):
                    self.connect()
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
            with contextlib.suppress(OSError):
                self.connect()
            time.sleep(0.3)

        self.assertTrue(self.exchange(first), "an established session was dropped by the limit")

    def test_the_limit_admits_exactly_its_number_of_clients(self):
        # The comparison counted the listening socket, so the limit tripped one
        # client later than its name.
        self.start_server(connLimit=3)

        for _ in range(5):
            with contextlib.suppress(OSError):
                self.connect()
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


class TestAssignedPort(ServerFixture):
    def test_port_zero_reports_the_port_the_operating_system_assigned(self):
        # run() used to bind whatever it was given and never look at the
        # result, so a server asked for port 0 bound a real port and kept
        # reporting 0. The listener was up and unreachable: no caller could
        # learn where it was, which is what forced every test module here to
        # name a fixed port instead.
        self.start_server()

        self.assertNotEqual(0, self.server.port, "the server still reports the port 0 it was asked for")

    def test_a_client_reaches_a_server_started_on_port_zero(self):
        # A reported port that nothing is listening on would satisfy the test
        # above. This dials it. The reply is not decoded here: what it says is
        # the dispatch suite's subject, and asserting the bytes would pin the
        # frame against this library's own output.
        self.start_server()

        self.assertTrue(self.exchange(self.connect()), "the reported port accepted no connection")


class TestStartup(ServerFixture):
    def test_start_reports_a_port_it_cannot_bind(self):
        # start() used to spin on the started event with no timeout and no
        # liveness check. A port already in use stops run() before it binds, so
        # the event never arrived and the caller hung for good, with the reason
        # on stderr where nothing could act on it.
        self.port = self.occupy_a_port()

        self.server = ModbusServerSimulator(port=self.port)
        self.server.daemon = True

        with self.assertRaises(ModbusNetworkError):
            self.server.start(timeout=3.0)

    def test_start_gives_up_quickly_when_the_thread_is_gone(self):
        # The liveness check should end the wait well inside the timeout.
        self.port = self.occupy_a_port()

        self.server = ModbusServerSimulator(port=self.port)
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

        # Named rather than matched on the message. The class is what a caller
        # catches, so it is what the test pins; the message is free to change.
        with self.assertRaises(ModbusModeError):
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
