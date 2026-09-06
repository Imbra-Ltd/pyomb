"""A bare pytest runs the fast tier, and the pipeline runs the other one.

Two halves of the arrangement fail silently, in opposite directions. The filter
can stop excluding, which puts the heavy tier back into every editor save with
nothing going red. Or it can stop including, which is worse: 57 tests that no
longer run anywhere report exactly what 57 passing tests report.

So both collections are asserted against floors rather than against each other,
and the third assertion is the pipeline step that selects the tier -- deleting
it stops those tests running where a merge is decided, with no local signal.
PLAYBOOK 3.25 carries how the two test directories are packaged.
"""

import pathlib
import subprocess  # nosec B404
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Read as text rather than parsed as YAML: the only YAML dependency in the test
# extra's closure is a transitive one, which no manifest here declares.
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

# The directory whose contents are the heavy tier, spelled as a collected item
# reports it. pytest prints POSIX separators on every platform.
TIER = "tests/integration/"

# The selection the pipeline has to make somewhere. Matched on the expression
# rather than the step name, so renaming the step is not a failure.
SELECTS_THE_TIER = "-m integration"

# What each collection held when these floors were set on 2026-09-05: 575 fast
# and 57 heavy. Tests churn, so each floor takes a margin below its count.
FAST_TIER_AT_LEAST = 400

HEAVY_TIER_AT_LEAST = 30


def collect(arguments):
    """Collect with the given arguments and report the items pytest found.

    Args:
        arguments (list[str]) : Arguments after the pytest invocation

    Returns:
        list[str] : One line per collected item, in collection order
    """

    # The argument vector is a list, so it reaches the operating system without
    # a shell, and every argument in it is a literal from this module.
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
