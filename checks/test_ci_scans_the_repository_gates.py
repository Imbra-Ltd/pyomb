"""The pipeline's path-listing steps name the directory holding the gates.

Three steps in `ci.yml` enumerate the directories they read: the linter, the
formatter and the static analyser. Each takes its scope from a path list
written into the step, so a directory absent from that list is a directory the
step never opens.

The gates moved from `tests/` to `checks/` so the source archive stops carrying
them. `tests` was already in all three lists; `checks` had to be added, and
nothing about a missing entry is visible afterwards. The step runs, exits zero
and reports on the paths it was given, which is the collapsed-scope failure --
a gate that ran, went green, and covered less than it claims.

This is the sibling of `checks/test_ci_collects_the_doctests.py`, which covers
the fourth step. That one passes no path at all, deliberately, so its subject
is the absence of an argument and a collection is what settles it. These three
pass paths on purpose, so their subject is the presence of one, and reading the
list is what settles it.

Neither module can be derived from the other, and the two failures are
independent: the test step can collect every gate while the linter never reads
the directory, and the linter can read it while the collection misses it.

The workflow is read as text rather than parsed as YAML, for the reason
`checks/test_workflow_downloads_retry.py` gives: the only YAML dependency in
the test extra's closure is a transitive one, so parsing would stake this
module on a dependency no manifest here declares.
"""

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

# The directory the gates live in, as the steps spell it.
GATES = "checks"

# The steps that take their scope from a path list. Named rather than
# discovered: a step that stops naming paths is exactly the change this module
# exists to fail on, so discovering the set from the file would let the subject
# delete itself and report a clean run.
SCOPED_STEPS = ("Lint", "Format", "Static analysis")

STEP = re.compile(r"^\s*- name: (?P<name>.+?)\s*$")

RUN = re.compile(r"^\s*run:\s*(?P<command>.*)$")

REMEDY = (
    "Add the directory to the step's path list in .github/workflows/ci.yml. "
    "That path is off-limits, so the change needs a proposal carrying a "
    "rollback strategy before it is made. A step whose list has lost the "
    "directory still exits zero -- it reports on the paths it was given, and "
    "the gates it no longer reads cannot report that they were skipped."
)


def step_commands():
    """The command each named step runs, keyed by step name.

    Only the steps this module governs are returned. A step whose `run:` key
    opens a folded block yields an empty command rather than being skipped, so
    a step that changed shape fails the coverage assertion instead of silently
    leaving the scope unread.

    Returns:
        dict[str, str] : Step name to the command text following its run key
    """

    found = {}
    pending = None

    for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
        opened = STEP.match(line)

        if opened:
            pending = opened.group("name")
            continue

        if pending is None:
            continue

        running = RUN.match(line)

        if running:
            if pending in SCOPED_STEPS:
                found[pending] = running.group("command").strip()

            pending = None

    return found


class ThePipelineScansTheRepositoryGates(unittest.TestCase):
    """Pins the scope of every step that reads a path list."""

    @classmethod
    def setUpClass(cls):
        cls.commands = step_commands()

    def test_every_step_this_rule_governs_was_found(self):
        """A pass below means the steps were read, not that none were found."""

        missing = [name for name in SCOPED_STEPS if not self.commands.get(name)]

        self.assertEqual(
            missing,
            [],
            f"{len(self.commands)} of {len(SCOPED_STEPS)} scoped steps were "
            "read from the workflow, so the assertion below would pass having "
            "checked almost nothing. A step was renamed, removed, or changed "
            "to a folded run block, which yields an empty command here:\n  " + "\n  ".join(missing),
        )

    def test_every_scoped_step_reads_the_gate_directory(self):
        """A step that never opens the directory cannot check what is in it."""

        offenders = [name for name, command in sorted(self.commands.items()) if GATES not in command.split()]

        self.assertEqual(
            offenders,
            [],
            f"these pipeline steps do not name {GATES} among their paths, so "
            "the repository gates are linted, formatted or scanned nowhere "
            "but a contributor's machine:\n  "
            + "\n  ".join(f"{name}: {self.commands[name]}" for name in offenders)
            + "\n"
            + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
