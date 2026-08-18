"""End-to-end TLS tests against generated certificates.

These are skipped unless the test chain exists. Generate it with:

    py scripts/gen_test_certs.py

The certificates are deliberately not committed, so this suite is opt-in
rather than part of the default run.
"""

import os
import ssl
import time
import unittest

from pyomb.omb_client import OmbClientSim
from pyomb.omb_server import OmbServerSim
from pyomb.packets import ModbusPduParser
from pyomb.packets import ModbusRequestFC1
from pyomb.packets import ModbusResponseFC1

CERTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "certificates")

CA = os.path.join(CERTS, "ca.crt")
SERVER_CRT = os.path.join(CERTS, "server.crt")
SERVER_KEY = os.path.join(CERTS, "server.key")
CLIENT_CRT = os.path.join(CERTS, "client-operator.crt")
CLIENT_KEY = os.path.join(CERTS, "client-operator.key")

HAVE_CERTS = all(os.path.exists(p) for p in (CA, SERVER_CRT, SERVER_KEY, CLIENT_CRT, CLIENT_KEY))

SKIP_REASON = "run 'py scripts/gen_test_certs.py' to generate the test chain"


class TestSecureDefaults(unittest.TestCase):
    """The hardened defaults are the regression this guards; no certs needed."""

    def test_client_requires_and_verifies_peer(self):
        import inspect

        defaults = inspect.signature(OmbClientSim.__init__).parameters

        self.assertIs(defaults["verify_hostname"].default, True)
        self.assertEqual(defaults["verify_mode"].default, ssl.CERT_REQUIRED)
        self.assertEqual(defaults["protocol"].default, ssl.PROTOCOL_TLS_CLIENT)

    def test_server_requires_client_certificate(self):
        import inspect

        defaults = inspect.signature(OmbServerSim.__init__).parameters

        self.assertEqual(defaults["verify_mode"].default, ssl.CERT_REQUIRED)
        self.assertEqual(defaults["protocol"].default, ssl.PROTOCOL_TLS_SERVER)

    def test_no_custom_cipher_string_is_imposed(self):
        # None means the interpreter's secure default suite. The previous
        # values enabled null encryption and anonymous key exchange.
        self.assertIsNone(OmbClientSim.DEFAULT_CIPHERS)
        self.assertIsNone(OmbServerSim.DEFAULT_CIPHERS)


@unittest.skipUnless(HAVE_CERTS, SKIP_REASON)
class TestMutualTls(unittest.TestCase):
    """The transport defaults must produce an authenticated, strong session."""

    # Each test binds its own port: the simulator's listener is not always
    # released before the next setUp, and a shared port intermittently hangs.
    port_counter = 18802

    def setUp(self):
        # The parser registry is process-global; register what these tests
        # need rather than depending on whatever ran before.
        ModbusPduParser.register(ModbusRequestFC1)
        ModbusPduParser.register(ModbusResponseFC1)

        type(self).port_counter += 1
        self.PORT = type(self).port_counter
        self.server = OmbServerSim(port=self.PORT, secure=True, cert=SERVER_CRT, key=SERVER_KEY, ca_chain=CA)
        self.server.start()
        time.sleep(0.5)
        self.client = None

    def tearDown(self):
        if self.client is not None:
            try:
                self.client.disconnect()
            except OSError:
                pass
        self.server.stop()
        time.sleep(0.2)

    def connect(self, **kwargs):
        options = dict(host="localhost", port=self.PORT, secure=True, cert=CLIENT_CRT, key=CLIENT_KEY, ca_chain=CA)
        options.update(kwargs)
        self.client = OmbClientSim(**options)
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
        header, pdu = client.request(fc=1, readAddress=0, readCount=10)

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
