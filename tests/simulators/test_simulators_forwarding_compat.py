"""The old pyomb.client_simulator and pyomb.server_simulator paths still resolve.

Both modules became forwarding shims when the simulators moved into
pyomb.simulators. Each name they used to define is pinned here: the
shim must hand back the exact class or function the new location
defines, not a copy, and must warn once per access naming both paths.
Deleted alongside the shims in 0.9.0, per the decision that ships them.
"""

import unittest
import warnings

import pyomb.client_simulator as old_client
import pyomb.server_simulator as old_server
import pyomb.simulators as new_simulators


class TheOldClientModuleStillResolves(unittest.TestCase):
    """Pins the per-name forwarding pyomb.client_simulator now does."""

    def test_every_name_it_used_to_define_still_resolves(self):
        """A name missing here breaks an import nothing else would catch."""

        missing = [name for name in old_client.__all__ if not hasattr(old_client, name)]

        self.assertEqual(missing, [], f"pyomb.client_simulator advertises names it does not bind: {missing}")

    def test_each_name_is_the_object_the_new_module_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in old_client.__all__:
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_client, name), getattr(new_simulators, name))

    def test_reading_a_name_warns_and_names_both_paths(self):
        """A caller who never reads the changelog meets the move here."""

        name = "ModbusClientSimulator"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(old_client, name)

        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)
        self.assertIn("pyomb.client_simulator.ModbusClientSimulator", str(caught[0].message))
        self.assertIn("pyomb.simulators.client_simulator.ModbusClientSimulator", str(caught[0].message))

    def test_an_unknown_name_still_raises(self):
        """The forwarding table answers for its own names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, old_client, "NoSuchName")


class TheOldServerModuleStillResolves(unittest.TestCase):
    """Pins the per-name forwarding pyomb.server_simulator now does."""

    def test_every_name_it_used_to_define_still_resolves(self):
        """A name missing here breaks an import nothing else would catch."""

        missing = [name for name in old_server.__all__ if not hasattr(old_server, name)]

        self.assertEqual(missing, [], f"pyomb.server_simulator advertises names it does not bind: {missing}")

    def test_each_name_is_the_object_the_new_module_defines(self):
        """A copy would break isinstance and identity checks a caller relies on."""

        for name in old_server.__all__:
            with self.subTest(name=name), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(old_server, name), getattr(new_simulators, name))

    def test_reading_a_name_warns_and_names_both_paths(self):
        """A caller who never reads the changelog meets the move here."""

        name = "ModbusServerSimulator"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(old_server, name)

        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, DeprecationWarning)
        self.assertIn("pyomb.server_simulator.ModbusServerSimulator", str(caught[0].message))
        self.assertIn("pyomb.simulators.server_simulator.ModbusServerSimulator", str(caught[0].message))

    def test_an_unknown_name_still_raises(self):
        """The forwarding table answers for its own names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, old_server, "NoSuchName")


if __name__ == "__main__":
    unittest.main()
