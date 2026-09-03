"""Every tool a workflow downloads is fetched with a retry.

The secrets gate fetches the gitleaks binary from a release asset before it can
scan anything. That download is the one step in the pipeline whose failure says
nothing about the change under review, and it is a required context, so a
transient network fault there blocks a merge on a verdict no one produced.

It has already happened once. The gate failed with
`curl: (35) Recv failure: Connection reset by peer`, which means the archive
never arrived and nothing scanned the diff. A single announced re-run passed.
That re-run is the habit `base-review` warns against -- retry-until-green masks
an infrastructure problem -- and the fix is to make the download survive the
fault rather than to make a person judge each red run.

`--retry` alone does not cover it. curl treats a timeout and an HTTP 408, 429
or 5xx as transient, and a connection reset mid-transfer is none of those;
`--retry-all-errors` is the flag that reaches it. The cost is that a genuine
404 is now attempted three times before failing, which is a few seconds spent
to keep the real fault loud rather than a reason to leave the reset uncovered.

`--fail` is asserted here as well, because it is load-bearing in the same
command and for a reason that is easy to undo by accident: without it curl
reports success on a 404 and writes the response body into the archive, so the
run fails two lines later at tar with a corrupt-archive error standing in for a
release that is not there. A retry flag added while dropping `--fail` would
turn one confusing failure into three.

The workflow is read as text rather than parsed as YAML. A parser would hand
back the same shell string to scan, and the only YAML dependency in the test
extra's closure is a transitive one of bandit -- so the parse would buy nothing
and stake this module on a dependency no manifest here declares.
"""

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

WORKFLOWS = REPO / ".github" / "workflows"

# A shell line continuation, plus the indentation the next line opens with. A
# download URL is long enough that the command is always split across several
# lines, and every flag has to be visible as one string to be checked.
CONTINUATION = re.compile(r"\\\s*\n\s*")

# curl as a command rather than as the word: it opens the line, or follows a
# shell operator, so a mention of curl in prose does not answer to this. The
# leading whitespace is not optional in practice -- a run block's commands are
# indented under the step, so anchoring at the bare start of a line matches
# nothing at all, which is a mistake the coverage test above catches.
CURL = re.compile(r"(?:^\s*|[|&;(]\s*)curl\s")

# The count is required rather than a bare --retry, which curl reads as zero
# attempts and which therefore reads as protection while providing none.
RETRY = re.compile(r"--retry\s+[1-9]")

RETRY_ALL = "--retry-all-errors"

FAIL_FLAGS = ("--fail", "-f")

REMEDY = (
    "Add --retry <n> --retry-all-errors to the command, and keep --fail (or "
    "-f). A reset mid-transfer is not one of the errors --retry alone covers, "
    "and without --fail a 404 body is written into the file as if it were the "
    "download."
)

NO_WORKFLOWS = "no workflow directory, so there are no download commands to read"


def shell_commands(text):
    """Flatten one workflow to the shell commands its run blocks hold.

    Args:
        text (str) : The workflow file's full source

    Returns:
        list[str] : One entry per logical shell line, continuations joined and
            comment lines dropped
    """

    joined = CONTINUATION.sub(" ", text)

    return [line for line in joined.split("\n") if not line.strip().startswith("#")]


def downloads(text):
    """Locate the curl invocations in one workflow.

    Args:
        text (str) : The workflow file's full source

    Returns:
        list[str] : One stripped command per curl invocation found
    """

    return [line.strip() for line in shell_commands(text) if CURL.search(line)]


class WorkflowDownloadsRetry(unittest.TestCase):
    """Pins the retry and the fail-fast flags on every workflow download."""

    @classmethod
    def setUpClass(cls):
        if not WORKFLOWS.is_dir():
            raise unittest.SkipTest(NO_WORKFLOWS)

        cls.commands = []

        for path in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
            for command in downloads(path.read_text(encoding="utf-8")):
                cls.commands.append((path.name, command))

    def test_the_workflows_carry_at_least_one_download(self):
        """A pass means the flags were checked, not that nothing was found."""

        self.assertNotEqual(
            self.commands,
            [],
            "no curl invocation was found in any workflow, so the checks below "
            "would pass without reading anything. Either the download moved to "
            "a form this does not recognise, or the pattern needs widening.",
        )

    def test_every_download_retries(self):
        """A transient fault costs an attempt rather than the pipeline."""

        offenders = [
            f"{name}: {command[:72]}"
            for name, command in self.commands
            if not (RETRY.search(command) and RETRY_ALL in command)
        ]

        self.assertEqual(
            offenders,
            [],
            "workflow downloads with no retry, so a transient network fault "
            "fails a required gate on a verdict nothing produced:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )

    def test_every_download_fails_on_an_error_response(self):
        """An error response is an error, not a file with the body in it."""

        offenders = [
            f"{name}: {command[:72]}"
            for name, command in self.commands
            if not any(flag in command.split() or flag[1:] in _bundled(command) for flag in FAIL_FLAGS)
        ]

        self.assertEqual(
            offenders,
            [],
            "workflow downloads that do not fail on an error response, so a "
            "404 body is saved as though it were the download:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )


def _bundled(command):
    """Collect the short flags written as one bundle, such as -sSfL.

    Args:
        command (str) : One shell command

    Returns:
        str : Every short-flag character appearing in a bundled argument
    """

    found = ""

    for word in command.split():
        if word.startswith("-") and not word.startswith("--"):
            found += word[1:]

    return found


if __name__ == "__main__":
    unittest.main()
