"""The package exports what it names, and names the deferred ones without loading them.

`__all__` is the project's statement of its public API, and nothing checked
it. A name can sit in that list with nothing bound to it -- the list is a
literal, not a reference -- so `from pyomb import X` fails for a name the
package advertises. The first check resolves every name against the package.

The simulators make that live rather than theoretical: they are bound through
the module's `__getattr__`, so their entries are backed by a function rather
than an import statement. The deferral is a property of the package, so the
last check runs a fresh interpreter and reads `sys.modules` -- in-process the
suite has already imported both submodules and would always say yes.
"""

import subprocess  # nosec B404
import sys
import unittest
import warnings

import pyomb


def imported_names(statement):
    """Report which of the watched modules a fresh interpreter loads.

    Args:
        statement (str) : The import statement the interpreter runs first

    Returns:
        set[str] : The watched module names present after it runs
    """

    watched = ("ssl", "pyomb.client_simulator", "pyomb.server_simulator", "pyomb.tls")

    program = "import sys\n" + statement + f"\nprint(' '.join(name for name in {watched!r} if name in sys.modules))"

    # The argument vector is a list holding this interpreter and a literal, so
    # nothing reaches a shell. The checks match on call shape only.
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        check=True,
    )

    return set(completed.stdout.split())


def import_failure(statement):
    """Report what a fresh interpreter writes to stderr running an import.

    Args:
        statement (str) : The import statement the interpreter runs

    Returns:
        str : Everything written to stderr, empty when the import succeeded
    """

    # Same call shape as the helper above, and safe for the same reasons.
    # check is off because a failing import is the subject here.
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", statement],
        capture_output=True,
        text=True,
        check=False,
    )

    return "" if completed.returncode == 0 else completed.stderr


class PackageExportsWhatItNames(unittest.TestCase):
    """Pins every advertised name to something the package actually binds."""

    def test_every_advertised_name_resolves(self):
        """A name in __all__ with nothing behind it breaks a documented import."""

        missing = sorted(name for name in pyomb.__all__ if not hasattr(pyomb, name))

        self.assertEqual(
            missing,
            [],
            "__all__ advertises names the package does not bind, so importing "
            "any of them from pyomb raises ImportError:\n  " + "\n  ".join(missing),
        )

    def test_the_simulators_are_the_classes_the_submodules_define(self):
        """A deferred binding must hand back the same class, not a copy of it."""

        from pyomb.client_simulator import ModbusClientSimulator
        from pyomb.server_simulator import ModbusServerSimulator

        self.assertIs(pyomb.ModbusClientSimulator, ModbusClientSimulator)
        self.assertIs(pyomb.ModbusServerSimulator, ModbusServerSimulator)

    def test_an_unknown_name_still_raises(self):
        """__getattr__ answers for two names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, pyomb, "NoSuchName")


class TheRenamedProtocolErrorsStillResolve(unittest.TestCase):
    """Pins the alias table the Error-suffix rename left behind.

    The eight names below were dropped from `__all__` when they took the
    suffix, so the walk above cannot see them and nothing else would fail if
    the alias branch were deleted before 2.0. Both halves are pinned: that the
    old spelling hands back the very class the new one names, and that reading
    it says so out loud rather than resolving silently.
    """

    def test_each_retired_spelling_is_the_class_it_was_renamed_to(self):
        """An alias returning a copy would break `except` on the new name."""

        for old, new in pyomb._RENAMED.items():
            with self.subTest(old=old), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)

                self.assertIs(getattr(pyomb, old), getattr(pyomb, new))

    def test_reading_a_retired_spelling_warns_and_names_both(self):
        """A caller who never reads the changelog meets the rename here."""

        for old, new in pyomb._RENAMED.items():
            with self.subTest(old=old):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    getattr(pyomb, old)

                self.assertEqual(len(caught), 1)
                self.assertIs(caught[0].category, DeprecationWarning)
                self.assertIn(old, str(caught[0].message))
                self.assertIn(new, str(caught[0].message))


class TheRetiredSpellingsAreGone(unittest.TestCase):
    """Pins the removal of the two names the rename left resolving.

    The check above walks `__all__`, and these two names were never in it, so
    nothing there can see them go. This class replaces the one that pinned them
    while they still resolved: restoring the alias branch turns both assertions
    below red, which is what stops the removal being quietly reverted.

    The first test asks in a fresh interpreter because `from pyomb import X` is
    what a consumer wrote, and the failure it raises is not the one the
    resolver raises -- the import system turns the resolver's AttributeError
    into ImportError on the way out. Both are pinned, since only the second
    says the name is gone rather than merely unimportable.
    """

    def test_importing_a_retired_name_fails(self):
        """The consumer-facing form is `from pyomb import X`, so pin that."""

        for retired in ("OmbClientSim", "OmbServerSim"):
            with self.subTest(retired=retired):
                stderr = import_failure("from pyomb import " + retired)

                self.assertIn("ImportError", stderr)
                self.assertIn(retired, stderr)

    def test_reading_a_retired_name_off_the_package_raises(self):
        """Underneath the import, the resolver no longer answers for the name."""

        for retired in ("OmbClientSim", "OmbServerSim"):
            with self.subTest(retired=retired):
                self.assertRaises(AttributeError, getattr, pyomb, retired)


class ImportingThePackageDoesNotOpenTheTransport(unittest.TestCase):
    """Pins the deferral the re-export rests on."""

    def test_the_plain_import_loads_neither_simulator_nor_ssl(self):
        """A codec-only caller pays nothing for a transport it never opens."""

        self.assertEqual(imported_names("import pyomb"), set())

    def test_naming_the_tls_settings_loads_them(self):
        """The settings reach ssl too, so they are deferred on the same terms."""

        loaded = imported_names("import pyomb; pyomb.TlsSettings")

        self.assertIn("pyomb.tls", loaded)
        self.assertIn("ssl", loaded)

    def test_naming_a_simulator_loads_it(self):
        """The deferral has to end when someone asks, or the name is useless."""

        self.assertIn("pyomb.server_simulator", imported_names("import pyomb; pyomb.ModbusServerSimulator"))


if __name__ == "__main__":
    unittest.main()
