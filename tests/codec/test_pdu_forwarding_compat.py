"""The old pyomb.packets.pdu and pyomb.packets.base paths still resolve.

Both modules became forwarding shims when the codec split into pyomb.pdu.
Each name they used to define is pinned here: the shim must hand back the
exact class the new location defines, not a copy, and must warn once per
access naming where the class moved to. Deleted alongside the shims in
0.9.0, per the decision that ships them.
"""

import unittest
import warnings

import pyomb.packets.base as old_base
import pyomb.packets.pdu as old_pdu
import pyomb.pdu as new_pdu
import pyomb.pdu.common as new_common


class TheOldPduModuleStillResolves(unittest.TestCase):
    """Pins the per-name forwarding pyomb.packets.pdu now does."""

    def test_every_name_it_used_to_define_still_resolves(self):
        """A name missing here breaks an import nothing else would catch."""

        missing = [name for name in old_pdu.__all__ if not hasattr(old_pdu, name)]

        self.assertEqual(missing, [], f"pyomb.packets.pdu advertises names it does not bind: {missing}")

    def test_each_name_is_the_class_the_new_module_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in old_pdu.__all__:
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_pdu, name), getattr(new_pdu, name))

    def test_reading_a_name_warns_and_names_both_paths(self):
        """A caller who never reads the changelog meets the move here."""

        name = "ModbusRequestFC1"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(old_pdu, name)

        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)
        self.assertIn("pyomb.packets.pdu.ModbusRequestFC1", str(caught[0].message))
        self.assertIn("pyomb.pdu.bits.ModbusRequestFC1", str(caught[0].message))

    def test_an_unknown_name_still_raises(self):
        """The forwarding table answers for its own names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, old_pdu, "NoSuchName")


class TheOldBaseModuleStillResolves(unittest.TestCase):
    """Pins the forwarding pyomb.packets.base now does."""

    def test_every_name_it_used_to_define_still_resolves(self):
        """A name missing here breaks an import nothing else would catch."""

        missing = [name for name in old_base.__all__ if not hasattr(old_base, name)]

        self.assertEqual(missing, [], f"pyomb.packets.base advertises names it does not bind: {missing}")

    def test_each_name_is_the_class_the_new_module_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in old_base.__all__:
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_base, name), getattr(new_common, name))

    def test_reading_a_name_warns_and_names_both_paths(self):
        """A caller who never reads the changelog meets the move here."""

        name = "ModbusPacketAbc"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(old_base, name)

        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)
        self.assertIn("pyomb.packets.base.ModbusPacketAbc", str(caught[0].message))
        self.assertIn("pyomb.pdu.common.ModbusPacketAbc", str(caught[0].message))

    def test_an_unknown_name_still_raises(self):
        """The forwarding table answers for its own names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, old_base, "NoSuchName")


if __name__ == "__main__":
    unittest.main()
