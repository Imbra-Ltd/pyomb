"""No document gate reports a clean tree when it has read nothing.

Every gate here asserts that a list of violations is empty, reading its corpus
from a tracked-file listing -- and an assertion that nothing was found passes
identically when nothing was examined. Three were measured blind, and those
three enforced three divergences this project recorded.

The control is the measurement rather than a description of it: every gate
reads its listing through `subprocess`, so replacing that one call blinds them
all at once. It discovers the gates rather than listing them, so one added
later is covered without editing this file. PLAYBOOK 3.22 carries the rest.
"""

import importlib
import io
import pathlib
import subprocess  # nosec B404
import unittest
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parents[1]

CHECKS = "checks/"

# What makes a module a document gate: it reads its corpus from git's index.
# The string appears here too, so the discovery drops itself by name.
MARKER = "ls-files"

SELF = pathlib.Path(__file__).stem

# What the tree held when this floor was set: 6 gates. Modules churn, so the
# floor takes a margin below the measured count rather than the count.
GATES_AT_LEAST = 3

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

REMEDY = (
    "A gate that reads a tracked-file listing carries one test asserting the "
    "listing reached a floor its corpus is known to hold, separate from the "
    "tests asserting the rule. A broken enumeration and a violating document "
    "want different fixes, so they are different tests with different "
    "messages. Assert a floor rather than non-emptiness: a listing that comes "
    "back holding one entry passes a non-empty check while measuring nothing."
)


def tracked_gate_modules():
    """Every gate module git tracks, as importable names.

    Returns:
        list[str] : The module names, in git's own order
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", CHECKS + "test_*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [pathlib.Path(name).stem for name in listing.split("\0") if name]


def document_gates(modules):
    """Select the modules that read their corpus from a tracked-file listing.

    Args:
        modules (list[str]) : Candidate gate module names

    Returns:
        list[str] : The gate module names, this module excluded
    """

    found = []

    for name in modules:
        if name == SELF:
            continue

        source = (REPO / CHECKS / f"{name}.py").read_text(encoding="utf-8")

        if MARKER in source:
            found.append(name)

    return found


def blinded(name):
    """Run one gate's tests with every listing it reads coming back empty.

    Args:
        name (str) : The gate module's importable name

    Returns:
        unittest.TestResult : The result of that module's own tests
    """

    module = importlib.import_module(name)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)

    # An empty listing rather than a failing call: what is under test is the
    # gate that reads a successful, empty result and reports a clean tree.
    empty = subprocess.CompletedProcess(args=(), returncode=0, stdout="", stderr="")

    # Patching the call rather than each module's enumeration covers a gate
    # nobody has written yet. It wraps the run, since a gate reads in setUpClass.
    with mock.patch.object(subprocess, "run", return_value=empty):
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)


class DocumentGatesAreNotBlind(unittest.TestCase):
    """Pins every tracked-file gate to failing when it reads nothing."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list to read, and a
        # directory walk would pick up scratch modules CI never sees.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.gates = document_gates(tracked_gate_modules())

    def test_the_discovery_reached_the_gates_in_the_tree(self):
        """A pass below means the gates were run, not that none were found."""

        self.assertGreaterEqual(
            len(self.gates),
            GATES_AT_LEAST,
            f"the discovery found {len(self.gates)} gate(s) where the floor is "
            f"{GATES_AT_LEAST}, so the control below would pass having run "
            "almost nothing. A module that is written but not staged is "
            "invisible here, because the listing reads git's index rather than "
            "the working tree. Otherwise: either the way a gate reads its "
            "corpus has changed and the marker no longer finds it, or enough "
            "gates were retired to eat the margin, in which case re-measure "
            "and lower the floor rather than treating this as a defect.",
        )

    def test_every_document_gate_fails_when_its_listing_comes_back_empty(self):
        """A gate that passes on an empty corpus cannot report having run."""

        offenders = []

        for name in self.gates:
            result = blinded(name)

            if not result.testsRun:
                offenders.append(f"{name}: no tests ran under the control")
                continue

            if not (result.failures or result.errors):
                offenders.append(f"{name}: {result.testsRun} ran, none failed")

        self.assertEqual(
            offenders,
            [],
            "these gates report a clean tree after reading nothing, so a pass "
            "from them says the enumeration ran, not that the rule holds:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
