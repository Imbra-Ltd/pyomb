"""The old pyomb.packets.framing and pyomb.packets paths still resolve.

Both modules became forwarding shims when the codec split into pyomb.adu
on top of pyomb.pdu. Each name they used to define is pinned here: the
shim must hand back the exact class or function the new location defines,
not a copy, and must warn once per access naming where it moved to.
Deleted alongside the shims in 0.9.0, per the decision that ships them.
"""

import unittest
import warnings

import pyomb.adu as new_adu
import pyomb.packets as old_packets
import pyomb.packets.framing as old_framing
import pyomb.pdu as new_pdu


class TheOldFramingModuleStillResolves(unittest.TestCase):
    """Pins the per-name forwarding pyomb.packets.framing now does."""

    def test_every_name_it_used_to_define_still_resolves(self):
        """A name missing here breaks an import nothing else would catch."""

        missing = [name for name in old_framing.__all__ if not hasattr(old_framing, name)]

        self.assertEqual(missing, [], f"pyomb.packets.framing advertises names it does not bind: {missing}")

    def test_each_name_is_the_object_the_new_module_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in old_framing.__all__:
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_framing, name), getattr(new_adu, name))

    def test_reading_a_name_warns_and_names_both_paths(self):
        """A caller who never reads the changelog meets the move here."""

        name = "ModbusHeader"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(old_framing, name)

        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)
        self.assertIn("pyomb.packets.framing.ModbusHeader", str(caught[0].message))
        self.assertIn("pyomb.adu.tcp.ModbusHeader", str(caught[0].message))

    def test_an_unknown_name_still_raises(self):
        """The forwarding table answers for its own names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, old_framing, "NoSuchName")


class TheOldPacketsModuleStillResolves(unittest.TestCase):
    """Pins the per-name forwarding the combined pyomb.packets now does."""

    def test_every_name_it_used_to_define_still_resolves(self):
        """A name missing here breaks an import nothing else would catch."""

        missing = [name for name in old_packets.__all__ if not hasattr(old_packets, name)]

        self.assertEqual(missing, [], f"pyomb.packets advertises names it does not bind: {missing}")

    def test_each_pdu_name_is_the_class_pyomb_pdu_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in ("ModbusPdu", "ModbusPduParser", "ModbusError", "ModbusRequestFC1", "ModbusResponseFC43"):
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_packets, name), getattr(new_pdu, name))

    def test_each_adu_name_is_the_class_pyomb_adu_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in ("ModbusHeader", "ModbusTcpRequest", "ModbusRtuPacket", "calc_crc16"):
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_packets, name), getattr(new_adu, name))

    def test_reading_a_name_warns_and_names_both_paths(self):
        """A caller who never reads the changelog meets the move here."""

        name = "ModbusRequestFC1"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(old_packets, name)

        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)
        self.assertIn("pyomb.packets.ModbusRequestFC1", str(caught[0].message))
        self.assertIn("pyomb.pdu.bits.ModbusRequestFC1", str(caught[0].message))

    def test_an_unknown_name_still_raises(self):
        """The forwarding table answers for its own names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, old_packets, "NoSuchName")


if __name__ == "__main__":
    unittest.main()
