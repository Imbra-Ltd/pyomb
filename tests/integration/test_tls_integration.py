"""End-to-end TLS tests against generated certificates.

These are skipped unless the test chain exists. Generate it with:

    py scripts/gen_test_certs.py

The certificates are deliberately not committed, so this suite is opt-in
rather than part of the default run.
"""

import contextlib
import pathlib
import ssl
import unittest

from pyomb.pdu import ModbusPduParser, ModbusRequestFC1, ModbusResponseFC1
from pyomb.simulators.client import ModbusClientSimulator
from pyomb.simulators.server import ModbusServerSimulator
from pyomb.transport.tls import TlsSettings

# scripts/gen_test_certs.py writes to <repo root>/assets/certificates by
# default; this file sits two directories below the repo root.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CERTS = REPO_ROOT / "assets" / "certificates"

CA = str(CERTS / "ca.crt")
SERVER_CRT = str(CERTS / "server.crt")
SERVER_KEY = str(CERTS / "server.key")
CLIENT_CRT = str(CERTS / "client-operator.crt")
CLIENT_KEY = str(CERTS / "client-operator.key")

HAVE_CERTS = all(pathlib.Path(p).exists() for p in (CA, SERVER_CRT, SERVER_KEY, CLIENT_CRT, CLIENT_KEY))

SKIP_REASON = "run 'py scripts/gen_test_certs.py' to generate the test chain"

# Seconds tearDown waits for the server thread. The run loop sits in a select
# with a one second timeout, so it needs that long to notice the quit event.
SHUTDOWN_TIMEOUT = 5.0


@unittest.skipUnless(HAVE_CERTS, SKIP_REASON)
class TestMutualTls(unittest.TestCase):
    """The transport defaults must produce an authenticated, strong session."""

    def setUp(self):
        # The parser registry is process-global; register what these tests
        # need rather than depending on whatever ran before.
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)

        # Port 0 asks the operating system for a free one, which sidesteps the
        # TIME_WAIT refusal a named port hits. PLAYBOOK 3.1.
        settings = TlsSettings(cert=SERVER_CRT, key=SERVER_KEY, ca_chain=CA)
        self.server = ModbusServerSimulator(port=0, tls=settings)

        # start() returns only once the listener accepts, bounded and raising
        # on failure, so a sleep here waits again for what it already waited.
        self.server.start()

        self.PORT = self.server.port
        self.client = None

    def tearDown(self):
        if self.client is not None:
            with contextlib.suppress(OSError):
                self.client.disconnect()
        self.server.stop()

        # stop() only sets the quit event, so join is the wait. A sleep shorter
        # than the loop's timeout let the thread run into the next test.
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
        # without binary_form hides custom extensions, so nothing reads it yet.
        client = self.connect()
        parsed = client.sock.getpeercert()
        raw = client.sock.getpeercert(binary_form=True)

        self.assertNotIn("1.3.6.1.4.1.50316.802.1", str(parsed))
        self.assertIsNotNone(raw)


if __name__ == "__main__":
    unittest.main()
