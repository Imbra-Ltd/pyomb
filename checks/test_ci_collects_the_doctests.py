"""The pipeline's test step collects the package's docstring examples.

`testpaths` applies only when pytest is given no path of its own, so a step
naming one silently replaces it. The pipeline named `tests` for as long as the
doctest configuration existed: locally a bare `pytest` collected 627 items
including 37 doctests, and the step collected 590 and none of them.

So this module asserts on a collection rather than on text -- it takes the
paths the step passes and asks what came back. Reading the step for the absence
of a path argument would be checking the configuration again, one level along.
PLAYBOOK 3.24 carries what each entry reaches.
"""

import pathlib
import re
import subprocess  # nosec B404
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Read as text rather than parsed as YAML: the only YAML dependency in the test
# extra's closure is a transitive one, which no manifest here declares.
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

STEP = re.compile(r"^\s*- name: Test\s*$")

# The key opening the folded command. Indentation is what ends the block: the
# Test step is the last in its job, so scanning for the next runs off the end.
RUN = re.compile(r"^(\s*)run:")

# Everything up to and including the runner invocation, discarded rather than
# asserted on -- the step may change how it reaches the interpreter.
INVOCATION = re.compile(r".*python -m pytest\b")


def step_arguments():
    """The arguments the pipeline's test step passes to pytest.

    Returns:
        list[str] : Every token after the pytest invocation, in order
    """

    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()

    body, indent, found = [], None, False

    for line in lines:
        if not found:
            found = bool(STEP.match(line))
            continue

        if indent is None:
            opened = RUN.match(line)
            if opened:
                indent = len(opened.group(1))
            continue

        if not line.strip():
            continue

        if len(line) - len(line.lstrip()) <= indent:
            break

        body.append(line.strip())

    # A folded block joins its lines with spaces, which is what the runner
    # hands to the shell.
    return INVOCATION.sub("", " ".join(body)).split()


def collect(paths):
    """Collect with the given paths and report what pytest found.

    Args:
        paths (list[str]) : Positional path arguments, empty for none

    Returns:
        tuple[int, int, int] : Items collected, how many are doctests in src,
            and how many are repository gates in checks
    """

    # The argument vector is a list, so it reaches the operating system without
    # a shell, and every path in it comes from the committed workflow.
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *paths],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )

    items = [line for line in completed.stdout.splitlines() if "::" in line]

    return (
        len(items),
        len([line for line in items if line.startswith("src/")]),
        len([line for line in items if line.startswith("checks/")]),
    )


class ThePipelineCollectsTheDocstringExamples(unittest.TestCase):
    """Pins the invocation, which the configuration gate cannot reach."""

    def test_the_step_passes_no_path_that_overrides_testpaths(self):
        """A path argument replaces the declared list rather than adding to it."""

        arguments = step_arguments()

        self.assertTrue(
            arguments,
            "no arguments were read from the test step, so nothing below "
            "establishes anything -- the step's shape changed",
        )

        collected, doctests, gates = collect([token for token in arguments if not token.startswith("-")])

        self.assertGreater(
            collected,
            0,
            "the collection reached nothing, so the counts below establish "
            "nothing either -- check the step still names pytest",
        )

        self.assertGreater(
            doctests,
            0,
            f"the pipeline's test step collects {collected} items and none of "
            "them is a docstring example from src/. A path argument in the "
            "step replaces testpaths rather than adding to it, so the src "
            "entry never applies and the examples run nowhere but a "
            "contributor's machine",
        )

        self.assertGreater(
            gates,
            0,
            f"the pipeline's test step collects {collected} items and none of "
            "them is a repository gate from checks/. The gates enforce this "
            "project's rules about its own documents -- the Markdown width, "
            "the decision-record schema, the changelog, the character set -- "
            "and a collection that misses them leaves every one of those "
            "unchecked while the suite reports green",
        )

    def test_naming_a_path_is_what_would_break_it(self):
        """The control: the failing form must fail, or the test above is blind."""

        collected, doctests, gates = collect(["tests"])

        self.assertGreater(collected, 0, "the control collected nothing")
        self.assertEqual(
            doctests,
            0,
            "collecting from tests/ alone was expected to reach no docstring "
            "example; if it now does, the assertion above no longer "
            "discriminates and this module needs rewriting",
        )
        self.assertEqual(
            gates,
            0,
            "collecting from tests/ alone was expected to reach no repository "
            "gate; if it now does, a gate has moved back under tests/ and the "
            "assertion above no longer discriminates",
        )


if __name__ == "__main__":
    unittest.main()
