"""Idle connections have to time out one at a time, not take the server down.

The inactivity map was keyed by conn.getsockname()[0], which on an accepted
socket is the server's own address and therefore identical for every client.
All connections collapsed onto a single entry. The sweep deleted that entry
when it closed the first idle connection, and the second one in the same pass
read it and raised KeyError, which left run() and ended the thread. The
default inactiveTimeout is one second, so two clients pausing together was
enough.

The same loop also mutated the list it was iterating, so it skipped whichever
connection followed a closed one.
"""

import contextlib
import socket
import threading
import time
import unittest

from pyomb.omb_server import OmbServerSim


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


class TestInactivitySweep(unittest.TestCase):
    def setUp(self):
        # 0 asks the operating system for a free port; start_server reads back
        # which one, so dialling the server requires starting it first.
        self.port = 0
        self.sockets = []

    def tearDown(self):
        for sock in self.sockets:
            with contextlib.suppress(OSError):
                sock.close()

        server = getattr(self, "server", None)

        if server is not None:
            server.stop()
            server.join(5.0)

    def start_server(self, **options):
        self.server = OmbServerSim(port=self.port, **options)
        self.server.daemon = True
        self.server.start()

        self.assertTrue(self.server.startedEvent.wait(5.0), "the server never reached its accept loop")

        self.port = self.server.port

        return self.server

    def connect(self):
        sock = socket.socket()
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", self.port))
        self.sockets.append(sock)

        return sock

    def test_two_idle_clients_do_not_kill_the_server(self):
        # The regression. Previously the second connection in the sweep hit a
        # KeyError on the entry the first one had just deleted.
        with ServerThreadExceptions() as thread_errors:
            self.start_server(inactiveTimeout=0.5)
            self.connect()
            self.connect()
            time.sleep(2.5)

            self.assertTrue(self.server.is_alive(), "server died: " + thread_errors.describe())
            self.assertEqual(thread_errors.caught, [])

    def test_several_idle_clients_do_not_kill_the_server(self):
        with ServerThreadExceptions() as thread_errors:
            self.start_server(inactiveTimeout=0.5)

            for _ in range(5):
                self.connect()

            time.sleep(2.5)

            self.assertTrue(self.server.is_alive(), "server died: " + thread_errors.describe())

    def test_every_idle_client_is_closed(self):
        # The list was mutated while being iterated, so a closed connection
        # made the sweep skip the one after it and leave it registered.
        self.start_server(inactiveTimeout=0.5)

        for _ in range(4):
            self.connect()

        time.sleep(2.5)

        self.assertEqual(self.server.getPeers(), [])

    def test_a_client_is_not_closed_while_it_is_still_talking(self):
        # Activity used to be recorded against the shared key, so any one
        # client's traffic kept every other one alive. This holds the opposite
        # property: an idle client goes even though a busy one stays.
        self.start_server(inactiveTimeout=1.0)
        busy = self.connect()
        self.connect()

        deadline = time.time() + 2.5

        while time.time() < deadline:
            busy.sendall(b"\x00\x01\x00\x00\x00\x02\x01\x07")
            busy.recv(256)
            time.sleep(0.2)

        self.assertEqual(len(self.server.getPeers()), 1, "the busy client should be the only one left")

    def test_server_survives_a_full_sweep_and_still_accepts(self):
        with ServerThreadExceptions() as thread_errors:
            self.start_server(inactiveTimeout=0.5)
            self.connect()
            self.connect()
            time.sleep(2.5)

            late = self.connect()
            late.sendall(b"\x00\x09\x00\x00\x00\x02\x01\x07")

            self.assertTrue(late.recv(256), "server stopped answering: " + thread_errors.describe())


if __name__ == "__main__":
    unittest.main()
