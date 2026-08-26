"""No document gate reports a clean tree when it has read nothing.

Six modules here assert that a list of violations is empty. Each reads its
corpus from a tracked-file listing, and an assertion that nothing was found
passes identically when nothing was examined -- so a gate whose enumeration
breaks goes on reporting success while measuring an empty set.

That is not a hypothetical. Three of the six were measured blind: patching the
enumeration to return nothing left the character-set rule, the readability
limits and the frontmatter schema all green, and those three are the
enforcement mechanisms of three divergences this project recorded. Each now
carries a coverage assertion of its own, and this module is what keeps them
carrying one.

The control it runs is the measurement itself rather than a description of it.
Every gate reads its listing through `subprocess`, so replacing that one call
with an empty result blinds all six at once, whatever each names its own
enumeration. A gate that still passes under that has no coverage assertion.

Two properties make the control honest. It discovers the gates rather than
listing them, so a seventh added later is covered without editing this file.
And the ordinary suite run is the other half: this module proves each gate
fails on an empty corpus, and the run that fails on nothing proves each one
passes on the real one.
"""

import importlib
import io
import pathlib
import subprocess  # nosec B404
import unittest
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parents[1]

TESTS = "tests/"

# What makes a module a document gate: it reads its corpus from git's index
# rather than from the filesystem. Every one of them spells it this way, and
# the string appears in this module too, which is why the discovery below drops
# itself by name rather than by content.
MARKER = "ls-files"

SELF = pathlib.Path(__file__).stem

# The six gates in the tree when this floor was set: the character set, the
# line endings, the Markdown width, and the three over the decision records. A
# floor rather than a non-empty check, for the same reason each of those gates
# now carries one -- a discovery that returns a single module satisfies
# non-emptiness while leaving five gates unmeasured.
GATES_AT_LEAST = 6

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

REMEDY = (
    "A gate that reads a tracked-file listing carries one test asserting the "
    "listing reached a floor its corpus is known to hold, separate from the "
    "tests asserting the rule. A broken enumeration and a violating document "
    "want different fixes, so they are different tests with different "
    "messages. Assert a floor rather than non-emptiness: a listing that comes "
    "back holding one entry passes a non-empty check while measuring nothing."
)


def tracked_test_modules():
    """Every test module git tracks, as importable names.

    Returns:
        list[str] : The module names, in git's own order
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell and cannot
    # become a second command. The checks match on call shape and cannot see
    # that.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", TESTS + "test_*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [pathlib.Path(name).stem for name in listing.split("\0") if name]


def document_gates(modules):
    """Select the modules that read their corpus from a tracked-file listing.

    Args:
        modules (list[str]) : Candidate test module names

    Returns:
        list[str] : The gate module names, this module excluded
    """

    found = []

    for name in modules:
        if name == SELF:
            continue

        source = (REPO / TESTS / f"{name}.py").read_text(encoding="utf-8")

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

    # An empty listing rather than a failing call: a gate whose git call raises
    # would fail for the wrong reason, and what is under test is the gate that
    # reads a successful, empty result and reports a clean tree from it.
    empty = subprocess.CompletedProcess(args=(), returncode=0, stdout="", stderr="")

    # Patching the call rather than each module's own enumeration is what lets
    # this cover a gate nobody has written yet. The patch has to wrap the run
    # rather than the load, because a gate reads its corpus in setUpClass.
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

        cls.gates = document_gates(tracked_test_modules())

    def test_the_discovery_reached_the_gates_in_the_tree(self):
        """A pass below means the gates were run, not that none were found."""

        self.assertGreaterEqual(
            len(self.gates),
            GATES_AT_LEAST,
            f"the discovery found {len(self.gates)} gate(s) where the tree "
            f"holds at least {GATES_AT_LEAST}, so the control below would pass "
            "having run almost nothing. A module that is written but not "
            "staged is invisible here, because the listing reads git's index "
            "rather than the working tree; anything else means the way a gate "
            "reads its corpus has changed and the marker no longer finds it.",
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
