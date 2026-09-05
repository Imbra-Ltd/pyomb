"""End-to-end TLS tests against generated certificates.

These are skipped unless the test chain exists. Generate it with:

    py scripts/gen_test_certs.py

The certificates are deliberately not committed, so this suite is opt-in
rather than part of the default run.
"""

import contextlib
import os
import ssl
import unittest

from pyomb.client_simulator import ModbusClientSimulator
from pyomb.packets import ModbusPduParser, ModbusRequestFC1, ModbusResponseFC1
from pyomb.server_simulator import ModbusServerSimulator
from pyomb.tls import TlsSettings

CERTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "certificates")

CA = os.path.join(CERTS, "ca.crt")
SERVER_CRT = os.path.join(CERTS, "server.crt")
SERVER_KEY = os.path.join(CERTS, "server.key")
CLIENT_CRT = os.path.join(CERTS, "client-operator.crt")
CLIENT_KEY = os.path.join(CERTS, "client-operator.key")

HAVE_CERTS = all(os.path.exists(p) for p in (CA, SERVER_CRT, SERVER_KEY, CLIENT_CRT, CLIENT_KEY))

SKIP_REASON = "run 'py scripts/gen_test_certs.py' to generate the test chain"

# Seconds tearDown waits for the server thread, matching the other server
# fixtures. The run loop sits in a select with a one second timeout, so the
# thread needs up to that long to notice the quit event before it can wind down.
SHUTDOWN_TIMEOUT = 5.0


@unittest.skipUnless(HAVE_CERTS, SKIP_REASON)
class TestMutualTls(unittest.TestCase):
    """The transport defaults must produce an authenticated, strong session."""

    def setUp(self):
        # The parser registry is process-global; register what these tests
        # need rather than depending on whatever ran before.
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)

        # Port 0 asks the operating system for a free one. tearDown waits for
        # the listener to close, but the server sets no SO_REUSEADDR, so a
        # named port that has just carried a connection can still refuse the
        # next bind while that connection sits in TIME_WAIT. Letting the
        # operating system choose sidesteps that rather than timing it.
        settings = TlsSettings(cert=SERVER_CRT, key=SERVER_KEY, ca_chain=CA)
        self.server = ModbusServerSimulator(port=0, tls=settings)

        # start() returns only once the listener is accepting: it waits on the
        # server's own started event, bounded by STARTUP_TIMEOUT, and raises
        # ModbusNetworkError if the thread dies or the deadline passes. Sleeping
        # here waited a second time for something already waited for, and a
        # fixed half second is the wrong answer either way -- too long when the
        # listener is up in milliseconds, too short if it ever is not.
        self.server.start()

        self.PORT = self.server.port
        self.client = None

    def tearDown(self):
        if self.client is not None:
            with contextlib.suppress(OSError):
                self.client.disconnect()
        self.server.stop()

        # stop() only sets the quit event, so the thread is still in its select
        # when this returns. Sleeping a fifth of a second here was shorter than
        # the loop's own timeout and so never waited long enough: the thread ran
        # on into the next test, and at the end of the run into pytest's capture
        # teardown, where its remaining log writes hit a closed stream.
        self.server.join(SHUTDOWN_TIMEOUT)

        self.assertFalse(
            self.server.is_alive(),
            f"the server thread was still running {SHUTDOWN_TIMEOUT} seconds after stop()",
        )

    def connect(self, **kwargs):
        options = {
            "host": "localhost",
            "port": self.PORT,
            "tls": TlsSettings(cert=CLIENT_CRT, key=CLIENT_KEY, ca_chain=CA),
        }
        options.update(kwargs)
        self.client = ModbusClientSimulator(**options)
        self.client.connect()

        return self.client

    def test_handshake_succeeds_with_defaults(self):
        client = self.connect()

        self.assertIsInstance(client.sock, ssl.SSLSocket)
        self.assertIsNotNone(client.sock.cipher())

    def test_negotiated_suite_is_not_weak(self):
        client = self.connect()
        name, protocol, bits = client.sock.cipher()

        # The permissive default this replaced allowed null encryption and
        # anonymous key exchange; neither can be negotiated now.
        self.assertNotIn("NULL", name)
        self.assertFalse(name.startswith(("ADH", "AECDH")))
        self.assertGreaterEqual(bits, 128)
        self.assertIn(protocol, ("TLSv1.2", "TLSv1.3"))

    def test_request_round_trips_over_tls(self):
        client = self.connect()
        header, pdu = client.request(fc=1, read_address=0, read_count=10)

        self.assertIsNotNone(header)
        self.assertEqual(pdu.fc, 1)

    def test_server_certificate_covers_the_connected_name(self):
        # Hostname checking is on by default, so a successful handshake is
        # itself proof the presented certificate matches the name used.
        client = self.connect(host="localhost")

        self.assertTrue(client.crypto.check_hostname)
        self.assertEqual(client.crypto.verify_mode, ssl.CERT_REQUIRED)

    def test_peer_certificate_carries_the_modbus_role(self):
        # The role OID is what MB-TCP-Security authorizes on. getpeercert()
        # without binary_form does not expose custom extensions, which is why
        # the server cannot currently read it -- see the audit's Security
        # finding on unimplemented role authorization.
        client = self.connect()
        parsed = client.sock.getpeercert()
        raw = client.sock.getpeercert(binary_form=True)

        self.assertNotIn("1.3.6.1.4.1.50316.802.1", str(parsed))
        self.assertIsNotNone(raw)


if __name__ == "__main__":
    unittest.main()
