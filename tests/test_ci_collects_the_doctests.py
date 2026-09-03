"""The pipeline's test step collects the package's docstring examples.

`pyproject.toml` declares `testpaths = ["tests", "src"]`, and the `src` entry
is the only thing that reaches the docstring examples. That list applies only
when pytest is given no path of its own, so a step naming one silently
replaces it.

The pipeline named `tests` for as long as the doctest configuration existed.
Locally a bare `pytest` collected 627 items including 37 doctests; the step
collected 590 and none of them, so every example ran on a contributor's
machine and none ran where a merge is decided. The configuration that exists
to catch a wrong example was added after exactly that -- an example asserting
something its class does not provide, on main, unnoticed.

`tests/test_doctests_are_gated.py` cannot see this. Its subject is the
configuration, and the configuration was correct throughout: the list named
both directories, the exemption machinery was consistent, and the gate reached
the package. What failed is the invocation, which no test read.

So this module asserts on a collection rather than on text. It takes the paths
the step passes, runs a collection with exactly those, and asks what came
back. A check reading the step for the absence of a path argument would pass
for a step naming the paths some other way and fail for one that is correct in
a form nobody anticipated -- which is checking the configuration again, one
level along.

The workflow is read as text rather than parsed as YAML, for the reason
`tests/test_workflow_downloads_retry.py` gives: the only YAML dependency in
the test extra's closure is a transitive one, so parsing would stake this
module on a dependency no manifest here declares.
"""

import pathlib
import re
import subprocess  # nosec B404
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

STEP = re.compile(r"^\s*- name: Test\s*$")

# The key opening the folded command, with its indentation captured. The block
# is every following line indented deeper than the key, which is what ends it:
# the Test step is the last in its job, so scanning for the next step instead
# runs off the end and swallows the job below.
RUN = re.compile(r"^(\s*)run:")

# Everything up to and including the runner invocation. What matters is what
# follows it, so the prefix is discarded rather than asserted on -- the step
# may reasonably change how it reaches the interpreter.
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
        tuple[int, int] : Items collected, and how many are doctests in src
    """

    # The argument vector is a list, so it reaches the operating system
    # without a shell. The interpreter is this process's own and every path
    # comes from the committed workflow, not from a caller.
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *paths],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )

    items = [line for line in completed.stdout.splitlines() if "::" in line]

    return len(items), len([line for line in items if line.startswith("src/")])


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

        collected, doctests = collect([token for token in arguments if not token.startswith("-")])

        self.assertGreater(
            collected,
            0,
            "the collection reached nothing, so the doctest count below "
            "establishes nothing either -- check the step still names pytest",
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

    def test_naming_a_path_is_what_would_break_it(self):
        """The control: the failing form must fail, or the test above is blind."""

        collected, doctests = collect(["tests"])

        self.assertGreater(collected, 0, "the control collected nothing")
        self.assertEqual(
            doctests,
            0,
            "collecting from tests/ alone was expected to reach no docstring "
            "example; if it now does, the assertion above no longer "
            "discriminates and this module needs rewriting",
        )


if __name__ == "__main__":
    unittest.main()
