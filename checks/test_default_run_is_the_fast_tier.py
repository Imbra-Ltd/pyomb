"""A bare pytest runs the fast tier, and the pipeline runs the other one.

The suite is tiered by directory. `tests/conftest.py` marks every item under
`tests/integration/`, the manifest deselects that marker, and a bare `pytest`
therefore opens no socket. Two halves of that arrangement fail silently, in
opposite directions, and neither is visible in a passing run.

**The filter can stop excluding.** A hook that stops marking, a marker renamed
on one side only, a `-m` dropped from `addopts` -- each puts the heavy tier
back into every editor save and every pre-commit run. Nothing goes red,
because the tests pass either way; the suite just costs seven times what it
should and binds loopback sockets to do it.

**The filter can stop including.** This is the worse one. A `-m` expression
that matches nothing leaves the default run collecting the fast tier and the
pipeline's integration step collecting zero -- and 57 tests that no longer run
anywhere report exactly what 57 passing tests report. So the two collections
are asserted against floors rather than against each other: an assertion that
the default run excludes the heavy tier passes just as well when the default
run reaches nothing at all.

The third assertion is about the pipeline. A tier the default run deselects is
a tier something else has to select, and the only thing that does is a step in
`ci.yml`. Delete that step and the integration tests stop running where a
merge is decided, with no local signal of any kind: a contributor's `pytest`
was never going to run them, which is the whole point of the tier.

This is the sibling of `checks/test_ci_collects_the_doctests.py`, which asks
whether the pipeline's own test step reaches the docstring examples and the
repository gates. That one is about a step passing no path; this one is about
a step that must exist at all.

The workflow is read as text rather than parsed as YAML, for the reason
`checks/test_workflow_downloads_retry.py` gives: the only YAML dependency in
the test extra's closure is a transitive one, so parsing would stake this
module on a dependency no manifest here declares.
"""

import pathlib
import subprocess  # nosec B404
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

# The directory whose contents are the heavy tier, spelled as a collected item
# reports it. pytest prints POSIX separators on every platform.
TIER = "tests/integration/"

# The selection the pipeline has to make somewhere. Matched on the expression
# rather than on a step name, so renaming the step is not a failure and
# deleting it is.
SELECTS_THE_TIER = "-m integration"

# What each collection held when these floors were set: 575 in the fast tier
# and 57 in the heavy one, on 2026-09-05. Both corpora churn -- retiring a test
# is an ordinary deletion -- so each floor takes a stated margin below the
# measured count rather than the count itself. The margin costs no detection:
# every way a selection breaks returns nothing at all rather than a fraction,
# so any floor above zero catches all of them.
FAST_TIER_AT_LEAST = 400

HEAVY_TIER_AT_LEAST = 30


def collect(arguments):
    """Collect with the given arguments and report the items pytest found.

    Args:
        arguments (list[str]) : Arguments after the pytest invocation

    Returns:
        list[str] : One line per collected item, in collection order
    """

    # The argument vector is a list, so it reaches the operating system
    # without a shell. The interpreter is this process's own and every
    # argument is a literal from this module.
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *arguments],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )

    return [line for line in completed.stdout.splitlines() if "::" in line]


class TheDefaultRunIsTheFastTier(unittest.TestCase):
    """Pins both directions of the tier filter, and the step that needs it."""

    @classmethod
    def setUpClass(cls):
        cls.default = collect([])
        cls.heavy = collect(["-m", "integration"])

    def test_the_default_collection_reached_the_suite(self):
        """A pass below means the tier was excluded, not that nothing was read."""

        self.assertGreaterEqual(
            len(self.default),
            FAST_TIER_AT_LEAST,
            f"a bare pytest collected {len(self.default)} item(s) where the "
            f"floor is {FAST_TIER_AT_LEAST}. The assertion below asks whether "
            "any of them is in the heavy tier, and a collection that reached "
            "almost nothing satisfies it while measuring almost nothing -- so "
            "this is the failure to fix first.",
        )

    def test_a_bare_pytest_selects_no_test_that_opens_a_socket(self):
        """The heavy tier is what a bare run must not pay for."""

        leaked = sorted({line.split("::")[0] for line in self.default if line.startswith(TIER)})

        self.assertEqual(
            leaked,
            [],
            f"a bare pytest collects {len(leaked)} module(s) from {TIER}, so "
            "every editor save and every pre-commit run binds loopback "
            "sockets and starts server threads:\n  "
            + "\n  ".join(leaked)
            + "\n\nThe tier is deselected by the -m entry in the manifest's "
            "addopts and marked by pytest_collection_modifyitems in "
            "tests/conftest.py. Both have to name the same marker.",
        )

    def test_the_heavy_tier_is_still_reachable(self):
        """A filter that matches nothing deselects the tier out of existence."""

        self.assertGreaterEqual(
            len(self.heavy),
            HEAVY_TIER_AT_LEAST,
            f"`pytest -m integration` collects {len(self.heavy)} item(s) where "
            f"the floor is {HEAVY_TIER_AT_LEAST}. The tier is deselected from "
            "the default run, so this selection is the only one that reaches "
            "it -- a hook that stopped marking, or a marker renamed on one "
            "side, leaves those tests running nowhere while every suite in "
            "the project still reports green.",
        )

    def test_the_pipeline_runs_the_tier_the_default_run_deselects(self):
        """Nothing local fails when the only step that selects the tier goes."""

        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            SELECTS_THE_TIER,
            workflow,
            f"no step in {WORKFLOW.name} selects the heavy tier with "
            f"`{SELECTS_THE_TIER}`. A bare pytest deselects it by design, so "
            "removing that step stops the integration tests running anywhere "
            "a merge is decided -- and no contributor's suite can report it, "
            "because a contributor's suite was never going to run them.\n\n"
            "That path is off-limits, so restoring the step needs a proposal "
            "carrying a rollback strategy before the change is made.",
        )


if __name__ == "__main__":
    unittest.main()
