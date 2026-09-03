"""The TLS settings object: role defaults, the floor, and what it reports.

These need no certificate chain. Certificate loading is stubbed out, because
what is under test is which values reach the context, not whether a file
parses -- the end-to-end handshake is tests/test_tls_integration.py.
"""

import ssl
import unittest
import warnings
from unittest import mock

import pyomb
from pyomb import tls
from pyomb.tls import UNSET, TlsRole, TlsSettings

# Paths that are never opened: every context in this module is built through
# the double below, whose certificate loading accepts anything.
CERT = "cert.pem"
KEY = "key.pem"
CA = "ca.pem"


class WeakPlatformContext(ssl.SSLContext):
    """An SSLContext that starts at the TLS 1.0 floor, with cert loading stubbed.

    Stands in for an OpenSSL build, or a security level, whose default floor
    sits below what the Modbus security specification requires. The platform
    this suite normally runs on already defaults to TLS 1.2, so a context that
    declares no floor of its own still reads as 1.2 there and an assertion
    against it would pass on code that declares nothing. Injecting the
    permissive default is what makes the assertion a statement about this
    library rather than about whichever OpenSSL happens to be linked.
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
        """Accept the CA chain path without reading them."""


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


def build(role, **fields):
    """Build a context for one role through the permissive platform double.

    Args:
        role (TlsRole) : The side to build for
        **fields       : Overrides passed to TlsSettings

    Returns:
        ssl.SSLContext : The context the settings produced
    """
    settings = TlsSettings(cert=CERT, key=KEY, ca_chain=CA, **fields)

    with mock.patch.object(tls, "ssl", WeakPlatformSsl()):
        return settings.context(role)


class TestRoleDefaults(unittest.TestCase):
    """One object serves both sides, and each side takes its own baseline."""

    def test_the_client_verifies_the_name_it_dialled(self):
        self.assertTrue(build(TlsRole.CLIENT).check_hostname)

    def test_the_server_checks_no_hostname(self):
        # A server has no name to check, and the ssl module refuses hostname
        # checking on a server context at all.
        self.assertFalse(build(TlsRole.SERVER).check_hostname)

    def test_both_sides_require_a_peer_certificate(self):
        # MB-TCP-Security is built on mutual TLS, so neither side accepts an
        # unauthenticated peer by default.
        for role in TlsRole:
            with self.subTest(role=role):
                self.assertEqual(build(role).verify_mode, ssl.CERT_REQUIRED)

    def test_no_cipher_string_is_imposed_by_default(self):
        # None means the interpreter's secure default suite. The values this
        # replaced enabled null encryption and anonymous key exchange, so the
        # regression is that the library imposes no string of its own rather
        # than that it imposes a particular one.
        with mock.patch.object(WeakPlatformContext, "set_ciphers") as spy:
            build(TlsRole.CLIENT)
            build(TlsRole.SERVER)

        spy.assert_not_called()

    def test_a_cipher_string_reaches_the_context_verbatim(self):
        # The counterpart to the test above: the parameter still works, and it
        # is passed through in the OpenSSL format the caller wrote it in.
        with mock.patch.object(WeakPlatformContext, "set_ciphers") as spy:
            build(TlsRole.CLIENT, ciphers="AES128-SHA")

        spy.assert_called_once_with("AES128-SHA")


class TestUnsetIsNotTheDefaultValue(unittest.TestCase):
    """Saying nothing and asking for the default are different calls.

    A single default value cannot carry both, and two settings prove it: the
    protocol constant and hostname checking differ per role, so an object that
    stored the resolved value would be wrong for one of the two sides.
    """

    def test_unset_hostname_checking_follows_the_role(self):
        settings = TlsSettings(cert=CERT, key=KEY, ca_chain=CA)

        self.assertIs(settings.verify_hostname, UNSET)

        with mock.patch.object(tls, "ssl", WeakPlatformSsl()):
            self.assertTrue(settings.context(TlsRole.CLIENT).check_hostname)
            self.assertFalse(settings.context(TlsRole.SERVER).check_hostname)

    def test_explicit_hostname_checking_overrides_the_role(self):
        # The same object, now carrying a choice rather than an absence, gives
        # both roles the same answer. That difference is what UNSET buys.
        settings = TlsSettings(cert=CERT, key=KEY, ca_chain=CA, verify_hostname=True)

        with mock.patch.object(tls, "ssl", WeakPlatformSsl()):
            self.assertTrue(settings.context(TlsRole.CLIENT).check_hostname)
            self.assertTrue(settings.context(TlsRole.SERVER).check_hostname)

    def test_unset_protocol_follows_the_role(self):
        settings = TlsSettings(cert=CERT, key=KEY, ca_chain=CA)

        self.assertIs(settings.protocol, UNSET)

        chosen = []

        class Recording(WeakPlatformContext):
            def __init__(self, protocol, *args, **kwargs):
                chosen.append(protocol)
                super().__init__(protocol, *args, **kwargs)

        fake = WeakPlatformSsl()
        fake.SSLContext = Recording

        with mock.patch.object(tls, "ssl", fake):
            settings.context(TlsRole.CLIENT)
            settings.context(TlsRole.SERVER)

        self.assertEqual(chosen, [ssl.PROTOCOL_TLS_CLIENT, ssl.PROTOCOL_TLS_SERVER])

    def test_an_unset_field_reads_as_unset_when_the_object_is_printed(self):
        # Inspectability is the point of grouping these, so printing one has
        # to show which fields carry a choice. Without the sentinel's own
        # repr the absence renders as an object address.
        settings = TlsSettings(cert=CERT, key=KEY, ca_chain=CA)

        self.assertIn("verify_hostname=UNSET", repr(settings))

    def test_none_is_a_value_for_ciphers_and_not_an_absence(self):
        # None is legal and means the interpreter's own suite, which is why
        # the sentinel cannot be None: the two would collide on this field.
        explicit = TlsSettings(cert=CERT, key=KEY, ca_chain=CA, ciphers=None)

        self.assertIsNone(explicit.ciphers)
        self.assertIsNot(explicit.ciphers, UNSET)


class TestUnsetIsPublic(unittest.TestCase):
    """The sentinel a caller compares against is reachable and stable.

    Grouping the settings was justified on inspectability, and relaxations()
    answers for the object as a whole. What it does not answer is whether one
    named field carries a choice, which a caller handed an object they did not
    build has to ask. That reads as `settings.protocol is UNSET` and needs the
    name on the supported surface rather than reached for inside pyomb.tls,
    which the package docstring does not list as public.
    """

    def test_the_sentinel_is_reachable_from_the_package_root(self):
        self.assertIs(pyomb.UNSET, UNSET)

    def test_the_root_and_the_submodule_hand_back_one_object(self):
        # Identity is the entire mechanism. Two spellings returning equal but
        # distinct objects would make `is` answer False for a caller who
        # imported from the root, and no assertion on value would catch it.
        self.assertIs(pyomb.UNSET, tls.UNSET)

    def test_the_sentinel_is_advertised_and_not_merely_reachable(self):
        # hasattr alone passes for a name the package binds incidentally. The
        # export list is what makes it supported.
        self.assertIn("UNSET", pyomb.__all__)

    def test_a_caller_can_tell_a_choice_from_a_default_per_field(self):
        # One object carrying both states: nothing but the sentinel separates
        # the field the caller set from the one they left alone.
        settings = TlsSettings(cert=CERT, key=KEY, ca_chain=CA, verify_hostname=False)

        self.assertIs(settings.protocol, pyomb.UNSET)
        self.assertIsNot(settings.verify_hostname, pyomb.UNSET)

    def test_both_spellings_render_as_the_name_a_caller_writes(self):
        # An enum defines its own __str__, where the plain class this replaced
        # fell back to __repr__. Letting the two disagree leaks the private
        # type name into any message that formats the value.
        self.assertEqual(repr(pyomb.UNSET), "UNSET")
        self.assertEqual(str(pyomb.UNSET), "UNSET")
        self.assertEqual(f"{pyomb.UNSET}", "UNSET")


class TestTheFloorIsNotRelaxable(unittest.TestCase):
    """The minimum version is applied last and survives every option mask."""

    def test_the_floor_is_declared_rather_than_inherited(self):
        # MB-TCP-Security v21, R-32 and R-34: an mbaps device provides TLS 1.2
        # or better and never negotiates down to 1.1, 1.0 or SSL 3.0.
        for role in TlsRole:
            with self.subTest(role=role):
                self.assertEqual(build(role).minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_options_cannot_lower_the_floor_by_omission(self):
        # The parameter is a bitmask the caller ORs in, so it can add a
        # restriction and never remove one. Passing none at all must still
        # leave the declared floor standing.
        context = build(TlsRole.CLIENT, options=ssl.Options(0))

        self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_the_floor_is_set_after_the_caller_options(self):
        # No value distinguishes the two orderings, because OR only ever adds
        # a bit and the floor's setter touches only the switches below the
        # version it names -- a reordered pair passes every assertion above.
        # The ordering is a rule this project binds, so the order of the two
        # writes is what the test has to reach.
        written = []

        class Recording(WeakPlatformContext):
            @property
            def options(self):
                return ssl.Options(0)

            @options.setter
            def options(self, value):
                written.append("options")

            @property
            def minimum_version(self):
                return ssl.TLSVersion.TLSv1_2

            @minimum_version.setter
            def minimum_version(self, value):
                written.append("minimum_version")

        fake = WeakPlatformSsl()
        fake.SSLContext = Recording

        with mock.patch.object(tls, "ssl", fake):
            TlsSettings(cert=CERT, key=KEY, ca_chain=CA).context(TlsRole.CLIENT)

        self.assertEqual(written[-2:], ["options", "minimum_version"])

    def test_options_still_restricts_above_the_floor(self):
        # A caller pinning the session to TLS 1.3 passes the 1.2 switch. The
        # declared floor must not quietly clear the bit they set, or the
        # parameter would stop working for what it is for.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            no_tls12 = ssl.OP_NO_TLSv1_2

        context = build(TlsRole.CLIENT, options=ssl.OP_ALL | no_tls12)

        self.assertTrue(context.options & no_tls12)


class TestRelaxationsAreReported(unittest.TestCase):
    """What the settings weaken is answerable, which loose arguments were not."""

    def settings(self, **fields):
        return TlsSettings(cert=CERT, key=KEY, ca_chain=CA, **fields)

    def test_the_secure_baseline_reports_nothing(self):
        for role in TlsRole:
            with self.subTest(role=role):
                self.assertEqual(self.settings().relaxations(role), ())

    def test_a_cipher_string_is_reported_with_the_string(self):
        reported = self.settings(ciphers="ALL:eNULL").relaxations(TlsRole.CLIENT)

        self.assertEqual(len(reported), 1)
        self.assertIn("ALL:eNULL", reported[0])

    def test_dropping_the_peer_certificate_is_reported_by_name(self):
        reported = self.settings(verify_mode=ssl.CERT_NONE).relaxations(TlsRole.SERVER)

        self.assertEqual(len(reported), 1)
        self.assertIn("CERT_NONE", reported[0])

    def test_hostname_checking_off_is_a_relaxation_only_where_it_was_on(self):
        # False is what a server context always carries, so reporting it there
        # would bury the client's real weakening under a permanent one.
        weakened = self.settings(verify_hostname=False)

        self.assertEqual(len(weakened.relaxations(TlsRole.CLIENT)), 1)
        self.assertEqual(weakened.relaxations(TlsRole.SERVER), ())

    def test_every_weakening_is_listed_rather_than_the_first(self):
        # The defect the object exists to prevent is a caller weakening one
        # setting while believing they weakened another, so a report naming
        # one of three would recreate it.
        weakened = self.settings(
            ciphers="ALL:eNULL",
            verify_mode=ssl.CERT_NONE,
            verify_hostname=False,
        )

        self.assertEqual(len(weakened.relaxations(TlsRole.CLIENT)), 3)


class TestTheSimulatorsConsumeTheSettings(unittest.TestCase):
    """The seam between the settings and the two simulators.

    These sit here rather than beside the simulator tests because what they
    assert is the settings object arriving intact, and the platform double
    that lets a context be built without a certificate chain is in this file.
    """

    def build(self, factory, **fields):
        """Construct a simulator through the permissive platform double."""
        settings = TlsSettings(cert=CERT, key=KEY, ca_chain=CA, **fields)

        with mock.patch.object(tls, "ssl", WeakPlatformSsl()):
            return factory(tls=settings)

    def test_the_client_takes_its_context_from_the_settings(self):
        from pyomb.client_simulator import ModbusClientSimulator

        client = self.build(ModbusClientSimulator)
        self.addCleanup(client.sock.close)

        self.assertTrue(client.crypto.check_hostname)
        self.assertEqual(client.crypto.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_the_server_takes_its_context_from_the_settings(self):
        from pyomb.server_simulator import ModbusServerSimulator

        server = self.build(ModbusServerSimulator)

        self.assertFalse(server.ssl_context.check_hostname)
        self.assertEqual(server.ssl_context.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_a_secure_client_moves_off_the_plaintext_port(self):
        from pyomb.client_simulator import ModbusClientSimulator

        client = self.build(ModbusClientSimulator)
        self.addCleanup(client.sock.close)

        self.assertEqual(client.port, ModbusClientSimulator.ENCRYPTED_PORT)

    def test_a_plaintext_client_builds_no_context(self):
        from pyomb.client_simulator import ModbusClientSimulator

        client = ModbusClientSimulator()
        self.addCleanup(client.sock.close)

        self.assertFalse(hasattr(client, "crypto"))
        self.assertEqual(client.port, ModbusClientSimulator.PLAINTEXT_PORT)

    def test_each_simulator_logs_the_weakenings_it_was_handed(self):
        # The report exists so a caller sees what the session will carry. It
        # is worth nothing sitting on the settings object unread, so both
        # simulators say it at construction.
        from pyomb.client_simulator import ModbusClientSimulator
        from pyomb.server_simulator import ModbusServerSimulator

        for factory in (ModbusClientSimulator, ModbusServerSimulator):
            with self.subTest(factory=factory.__name__):
                log = mock.MagicMock()
                settings = TlsSettings(
                    cert=CERT,
                    key=KEY,
                    ca_chain=CA,
                    ciphers="ALL:eNULL",
                    verify_mode=ssl.CERT_NONE,
                )

                with mock.patch.object(tls, "ssl", WeakPlatformSsl()):
                    built = factory(log=log, tls=settings)

                if hasattr(built, "sock"):
                    self.addCleanup(built.sock.close)

                warned = " ".join(str(call) for call in log.warning.call_args_list)

                self.assertIn("ALL:eNULL", warned)
                self.assertIn("CERT_NONE", warned)


if __name__ == "__main__":
    unittest.main()
