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
import warnings
from unittest import mock

from pyomb import client_simulator, server_simulator
from pyomb.client_simulator import ModbusClientSimulator
from pyomb.packets import ModbusPduParser, ModbusRequestFC1, ModbusResponseFC1
from pyomb.server_simulator import ModbusServerSimulator

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


class WeakPlatformContext(ssl.SSLContext):
    """An SSLContext that starts at the TLS 1.0 floor, with cert loading stubbed.

    Stands in for an OpenSSL build, or a security level, whose default floor
    sits below what the Modbus security specification requires. The platform
    this suite normally runs on already defaults to TLS 1.2, so a context that
    declares no floor of its own still reads as 1.2 there and an assertion
    against it would pass on the unfixed code. Injecting the permissive default
    is what makes the assertion a statement about this library rather than
    about whichever OpenSSL happens to be linked.
    """

    def __init__(self, *args, **kwargs):
        # TLSVersion.TLSv1 is deprecated, which is the point of using it here:
        # this is the permissive platform the library has to override.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.minimum_version = ssl.TLSVersion.TLSv1

    def load_cert_chain(self, *args, **kwargs):
        """Accept the certificate and key paths without reading them."""

    def load_verify_locations(self, *args, **kwargs):
        """Accept the CA chain path without reading it."""


class WeakPlatformSsl:
    """A stand-in for the ssl module whose SSLContext is the permissive double.

    Replacing ssl.SSLContext on the module itself is not an option: the
    standard library's own minimum_version setter looks that name up on the
    module, so a double installed there makes the setter recurse into itself.
    Redirecting only the name the module under test reads leaves the real class
    where the standard library expects to find it, and every other attribute
    falls through untouched.
    """

    SSLContext = WeakPlatformContext

    def __getattr__(self, name):
        return getattr(ssl, name)


class TestSecureDefaults(unittest.TestCase):
    """The hardened defaults are the regression this guards; no certs needed."""

    def test_client_requires_and_verifies_peer(self):
        import inspect

        defaults = inspect.signature(ModbusClientSimulator.__init__).parameters

        self.assertIs(defaults["verify_hostname"].default, True)
        self.assertEqual(defaults["verify_mode"].default, ssl.CERT_REQUIRED)
        self.assertEqual(defaults["protocol"].default, ssl.PROTOCOL_TLS_CLIENT)

    def test_server_requires_client_certificate(self):
        import inspect

        defaults = inspect.signature(ModbusServerSimulator.__init__).parameters

        self.assertEqual(defaults["verify_mode"].default, ssl.CERT_REQUIRED)
        self.assertEqual(defaults["protocol"].default, ssl.PROTOCOL_TLS_SERVER)

    def test_no_custom_cipher_string_is_imposed(self):
        # None means the interpreter's secure default suite. The previous
        # values enabled null encryption and anonymous key exchange.
        self.assertIsNone(ModbusClientSimulator.DEFAULT_CIPHERS)
        self.assertIsNone(ModbusServerSimulator.DEFAULT_CIPHERS)

    def _secure_client(self, **kwargs):
        """Build a secure client whose context came from the permissive double."""
        with mock.patch.object(client_simulator, "ssl", WeakPlatformSsl()):
            client = ModbusClientSimulator(secure=True, **kwargs)

        self.addCleanup(client.sock.close)
        return client

    def _secure_server(self, **kwargs):
        """Build a secure server whose context came from the permissive double."""
        with mock.patch.object(server_simulator, "ssl", WeakPlatformSsl()):
            return ModbusServerSimulator(secure=True, **kwargs)

    def test_client_declares_the_tls_floor_rather_than_inheriting_it(self):
        # MB-TCP-Security v21, R-32 and R-34: an mbaps device provides TLS 1.2
        # or better and never negotiates down to 1.1, 1.0 or SSL 3.0.
        self.assertEqual(self._secure_client().crypto.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_server_declares_the_tls_floor_rather_than_inheriting_it(self):
        self.assertEqual(self._secure_server().ssl_context.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_ssl_options_cannot_lower_the_floor_by_omission(self):
        # The parameter is a bitmask the caller ORs in, so it can add a
        # restriction and never remove one. Passing none at all must still
        # leave the declared floor standing.
        self.assertEqual(self._secure_client(ssl_options=0).crypto.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_ssl_options_still_restricts_above_the_floor(self):
        # A caller pinning the session to TLS 1.3 passes the 1.2 switch. The
        # declared floor must not quietly clear the bit they set, or the
        # parameter would stop working for what it is for.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            no_tls12 = ssl.OP_NO_TLSv1_2

        client = self._secure_client(ssl_options=ssl.OP_ALL | no_tls12)

        self.assertTrue(client.crypto.options & no_tls12)


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
        self.server = ModbusServerSimulator(port=0, secure=True, cert=SERVER_CRT, key=SERVER_KEY, ca_chain=CA)

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
            "secure": True,
            "cert": CLIENT_CRT,
            "key": CLIENT_KEY,
            "ca_chain": CA,
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
