"""A command in the documentation reads the same tree as its pipeline step.

Which directories the checkers open is one fact written in two places: the
path list inside each `ci.yml` step, and the commands a contributor copies out
of `CLAUDE.md`, the playbook and the onboarding guide. A sibling module gates
the pipeline's half. Nothing gated the documented half, so it drifted.

It drifted silently, and it had to. Both halves exit zero -- a checker reports
on the paths it is given, never on the one it was not -- so the only signal is
a pipeline going red on a change that looked clean locally. `CLAUDE.md` is the
worst of the three to leave stale: it is the command list an agent works from
every session.
"""

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Read as text rather than parsed as YAML: the only YAML dependency in the test
# extra's closure is a transitive one, which no manifest here declares.
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

# The documents a contributor or an agent copies a command out of.
DOCUMENTS = ("CLAUDE.md", "docs/PLAYBOOK.md", "docs/ONBOARDING.md")

# The pipeline step each documented tool is measured against. The noqa sweep
# has no step of its own and reads the corpus the linter reads.
TOOLS = {
    "ruff check": "Lint",
    "ruff format": "Format",
    "bandit": "Static analysis",
    "# noqa": "Lint",
}

# Every top-level directory a scanning command may name. A fixed vocabulary is
# what keeps a flag or a config file from counting as a path.
DIRECTORIES = ("src", "tests", "checks", "scripts", "examples", "docs", "assets")

# The steps whose path list the documented commands are compared against.
SCOPED_STEPS = ("Lint", "Format", "Static analysis")

# Measured at nine when this floor was set: three in CLAUDE.md, four in the
# playbook, two in the onboarding guide. A broken enumeration returns none.
MINIMUM_DOCUMENTED = 7

STEP = re.compile(r"^\s*- name: (?P<name>.+?)\s*$")
RUN = re.compile(r"^\s*run:\s*(?P<command>.*)$")
FENCE = re.compile(r"^\s*```")

REMEDY = (
    "Edit the documented command so it names the same directories as its "
    "pipeline step. A contributor who follows the documentation otherwise "
    "runs the checker over less of the repository than CI does, and both "
    "runs exit zero -- a checker reports on the paths it is given and cannot "
    "report on the one it was not."
)


def paths_in(command):
    """The directories a command names, as a set.

    Args:
        command (str) : One command line, with or without a shell prefix

    Returns:
        set : The members of DIRECTORIES the command passes as arguments
    """

    tokens = {token.strip("'\"") for token in command.split()}

    return tokens & set(DIRECTORIES)


def pipeline_scopes():
    """The path set each scoped pipeline step passes.

    Returns:
        dict[str, set] : Step name to the directories its command names
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
                found[pending] = paths_in(running.group("command"))

            pending = None

    return found


def documented_commands():
    """Every command in the documents that scans the tree with a named tool.

    Only fenced lines are read. A tool named in running prose is being
    discussed rather than offered for copying, and reading those would report
    on sentences.

    Returns:
        list[tuple] : Document, line number, step name and the command text
    """

    found = []

    for name in DOCUMENTS:
        path = REPO / name
        fenced = False

        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE.match(line):
                fenced = not fenced
                continue

            if not fenced:
                continue

            for tool, step in TOOLS.items():
                if tool in line and paths_in(line):
                    found.append((name, number, step, line.strip()))
                    break

    return found


class TheDocumentedCommandsMatchThePipeline(unittest.TestCase):
    """Pins the two copies of which directories the checkers open."""

    @classmethod
    def setUpClass(cls):
        cls.scopes = pipeline_scopes()
        cls.commands = documented_commands()

    def test_every_pipeline_step_was_read(self):
        """A comparison against a step that was not read establishes nothing."""

        missing = [name for name in SCOPED_STEPS if not self.scopes.get(name)]

        self.assertEqual(
            missing,
            [],
            f"{len(self.scopes)} of {len(SCOPED_STEPS)} scoped steps were read "
            "from the workflow, so the assertion below would compare against "
            "an empty set. A step was renamed, removed, or changed to a "
            "folded run block:\n  " + "\n  ".join(missing),
        )

    def test_enough_documented_commands_were_found(self):
        """A pass below means the documents were read, not that none exist."""

        self.assertGreaterEqual(
            len(self.commands),
            MINIMUM_DOCUMENTED,
            f"only {len(self.commands)} documented command(s) were found "
            f"across {len(DOCUMENTS)} document(s), below the floor of "
            f"{MINIMUM_DOCUMENTED}. The fence pattern, the tool names or the "
            "document list has drifted, so the assertion below would pass "
            "having read almost nothing.",
        )

    def test_every_documented_command_names_the_pipeline_scope(self):
        """A command reading less of the tree than CI reports a clean run."""

        offenders = []

        for name, number, step, command in self.commands:
            expected = self.scopes[step]
            actual = paths_in(command)

            if actual != expected:
                offenders.append(
                    f"{name}:{number} names {sorted(actual)}, "
                    f"where the {step} step names {sorted(expected)}\n    {command}"
                )

        self.assertEqual(
            offenders,
            [],
            f"{len(offenders)} documented command(s) scan a different tree "
            "than the pipeline does:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
