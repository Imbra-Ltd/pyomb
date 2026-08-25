"""The package exports what it names, and names the simulators without loading them.

`__all__` is the project's statement of its public API, and nothing checked it.
A name can sit in that list with nothing bound to it -- the list is a literal,
not a reference -- so `from pyomb import X` fails for a name the package
advertises, and no gate reports it. The first check here closes that: every
name in the list is resolved against the package.

The simulators make the gap live rather than theoretical. They are bound
through the module's `__getattr__` rather than imported at the top, because
importing them costs every caller the ssl import for a transport most callers
never open. That keeps them in the flat public API at no cost to a codec-only
caller, and it means their entries in `__all__` are backed by a function rather
than by an import statement -- exactly the shape whose failure the first check
would otherwise miss.

The deferral is a property of the package, not of the classes, so the last
check runs a fresh interpreter and asks it what got imported. It reads
`sys.modules`, which is the import system's own record of that answer and the
only place it is observable; in-process the suite has already imported both
submodules for other reasons, so asking here would always say yes.
"""

import subprocess  # nosec B404
import sys
import unittest

import pyomb


def imported_names(statement):
    """Report which of the watched modules a fresh interpreter loads.

    Args:
        statement (str) : The import statement the interpreter runs first

    Returns:
        set[str] : The watched module names present after it runs
    """

    watched = ("ssl", "pyomb.omb_client", "pyomb.omb_server")

    program = "import sys\n" + statement + f"\nprint(' '.join(name for name in {watched!r} if name in sys.modules))"

    # The argument vector is a list, so it reaches the operating system
    # directly rather than through a shell and nothing in it can become a
    # second command. The interpreter is this process's own, and the program
    # is a literal built above with no caller input in it. The checks match on
    # call shape and see neither.
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        check=True,
    )

    return set(completed.stdout.split())


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

        from pyomb.omb_client import OmbClientSim
        from pyomb.omb_server import OmbServerSim

        self.assertIs(pyomb.OmbClientSim, OmbClientSim)
        self.assertIs(pyomb.OmbServerSim, OmbServerSim)

    def test_an_unknown_name_still_raises(self):
        """__getattr__ answers for two names and must not swallow the rest."""

        self.assertRaises(AttributeError, getattr, pyomb, "NoSuchName")


class ImportingThePackageDoesNotOpenTheTransport(unittest.TestCase):
    """Pins the deferral the re-export rests on."""

    def test_the_plain_import_loads_neither_simulator_nor_ssl(self):
        """A codec-only caller pays nothing for a transport it never opens."""

        self.assertEqual(imported_names("import pyomb"), set())

    def test_naming_a_simulator_loads_it(self):
        """The deferral has to end when someone asks, or the name is useless."""

        self.assertIn("pyomb.omb_server", imported_names("import pyomb; pyomb.OmbServerSim"))


if __name__ == "__main__":
    unittest.main()
