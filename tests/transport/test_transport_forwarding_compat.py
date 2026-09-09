"""The old pyomb.stream and pyomb.tls paths still resolve.

Both modules became forwarding shims when the transport moved into
pyomb.transport. Each name they used to define is pinned here: the shim
must hand back the exact class or value the new location defines, not a
copy, and must warn once per access naming both paths. Deleted alongside
the shims in 0.9.0, per the decision that ships them.
"""

import unittest
import warnings

import pyomb.stream as old_stream
import pyomb.tls as old_tls
import pyomb.transport as new_transport


class TheOldStreamModuleStillResolves(unittest.TestCase):
    """Pins the per-name forwarding pyomb.stream now does."""

    def test_every_name_it_used_to_define_still_resolves(self):
        """A name missing here breaks an import nothing else would catch."""

        missing = [name for name in old_stream.__all__ if not hasattr(old_stream, name)]

        self.assertEqual(missing, [], f"pyomb.stream advertises names it does not bind: {missing}")

    def test_each_name_is_the_class_the_new_module_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in old_stream.__all__:
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_stream, name), getattr(new_transport, name))

    def test_reading_a_name_warns_and_names_both_paths(self):
        """A caller who never reads the changelog meets the move here."""

        name = "ModbusTcpStream"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(old_stream, name)

        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)
        self.assertIn("pyomb.stream.ModbusTcpStream", str(caught[0].message))
        self.assertIn("pyomb.transport.stream.ModbusTcpStream", str(caught[0].message))

    def test_an_unknown_name_still_raises(self):
        """The forwarding table answers for its own names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, old_stream, "NoSuchName")


class TheOldTlsModuleStillResolves(unittest.TestCase):
    """Pins the forwarding pyomb.tls now does."""

    def test_every_name_it_used_to_define_still_resolves(self):
        """A name missing here breaks an import nothing else would catch."""

        missing = [name for name in old_tls.__all__ if not hasattr(old_tls, name)]

        self.assertEqual(missing, [], f"pyomb.tls advertises names it does not bind: {missing}")

    def test_each_name_is_the_object_the_new_module_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in old_tls.__all__:
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_tls, name), getattr(new_transport, name))

    def test_reading_a_name_warns_and_names_both_paths(self):
        """A caller who never reads the changelog meets the move here."""

        name = "TlsSettings"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(old_tls, name)

        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)
        self.assertIn("pyomb.tls.TlsSettings", str(caught[0].message))
        self.assertIn("pyomb.transport.tls.TlsSettings", str(caught[0].message))

    def test_an_unknown_name_still_raises(self):
        """The forwarding table answers for its own names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, old_tls, "NoSuchName")


if __name__ == "__main__":
    unittest.main()
