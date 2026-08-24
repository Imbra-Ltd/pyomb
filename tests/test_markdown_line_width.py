"""Markdown prose wraps at 80 columns.

The documents already do this. Every governance and reference file the project
maintains -- the agent context file, the README, CONTRIBUTING, PLAYBOOK,
ONBOARDING, the journal, the audits and the decision records -- holds its prose
to 80 columns, and did so before anything checked. What was missing is the
rule: `.editorconfig` sets a maximum width for Python and says nothing about
Markdown, and CONTRIBUTING states 120 with 80 recommended under a heading that
reads Code style. So the convention was real, unwritten, and held by hand.

It was also already slipping. A 98-column heading reached a green pipeline,
because no gate in the project reads the width of a Markdown line.

Three kinds of line are exempt, and each is exempt because it cannot be wrapped
rather than because it is inconvenient:

A table row carries its columns on one line; a newline inside it ends the row.
A fenced block holds commands and output, where a break changes what the reader
is meant to copy or would misrepresent what a tool printed. A line carrying a
URL cannot be split at all, since no Markdown break survives inside one, and a
badge line is two long URLs and almost no prose.

The width is counted in characters, not bytes. The em dash the prose rule
permits is three bytes in UTF-8, and counting bytes would charge a document
three columns for one glyph and shorten every line that uses one.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# The width the documents already keep. It is the recommendation CONTRIBUTING
# makes for code, applied to the prose that surrounds it, and the measurement
# that introduced this module found the whole tree already inside it but for
# three lines.
MAX_COLUMNS = 80

# Imported with the v0.1.0 tree rather than written to this convention, and
# wrapped at about 96 throughout: its prose sits at a median of 35 columns and a
# 90th percentile of 94. It is protocol reference material, internally
# consistent at its own width, and rewrapping 160 lines of it would bury a
# change nobody asked for. The exclusion is the rule's scope, not a suppression
# of findings inside it -- a document this project authored has no such escape.
IMPORTED = {"docs/Open_Modbus_Tutorial.md"}

# A URL survives no line break, so a line carrying one is measured by nothing
# the author can act on. This covers the badge block at the top of the README,
# which is two long links and a label. A relative link is not exempt: it is
# short, and the prose around it wraps like any other.
URL = re.compile(r"https?://")

REMEDY = (
    "Wrap the line at or before column 80. A heading that will not fit wants a "
    "shorter title rather than a longer line, and a table or a fenced block "
    "does not need wrapping because neither is measured here."
)

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"


def tracked_markdown():
    """Every Markdown file git tracks, excluding the templates submodule.

    Returns:
        list[str] : The tracked Markdown paths, in git's own order
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell and cannot
    # become a second command. The checks match on call shape and cannot see
    # that.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", "*.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    # A submodule is tracked as a gitlink, so its own files never appear here.
    # The prefix guard is for the day one is vendored in as ordinary files.
    return [name for name in listing.split("\0") if name and not name.startswith("docs/solid-ai-templates/")]


def overlong(text):
    """Locate the lines in one document that exceed the width.

    Args:
        text (str) : The document's full Markdown source

    Returns:
        list[tuple[int, int, str]] : One (line, width, content) triple per
            offending line, with the exempt kinds already removed
    """

    found = []
    fenced = False

    for number, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()

        # A fence toggles rather than nests, so a block between a pair of them
        # is skipped whatever it holds. The fence line itself is short.
        if stripped.startswith("```"):
            fenced = not fenced
            continue

        if fenced or stripped.startswith("|") or URL.search(line):
            continue

        if len(line) > MAX_COLUMNS:
            found.append((number, len(line), line))

    return found


class MarkdownLineWidth(unittest.TestCase):
    """Pins the 80-column wrap the documents already keep."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list to read, and a
        # directory walk would pick up scratch files CI never sees. The skip is
        # for that case only; a checkout whose git call fails is a failure.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.documents = [name for name in tracked_markdown() if name not in IMPORTED]

    def test_no_markdown_line_runs_past_the_width(self):
        """Prose, headings and list items stay within 80 columns."""

        offenders = []

        for name in self.documents:
            text = (REPO / name).read_text(encoding="utf-8")

            for number, width, line in overlong(text):
                offenders.append(f"{name}:{number} ({width}) {line[:56]}")

        self.assertEqual(
            offenders,
            [],
            f"Markdown lines past {MAX_COLUMNS} columns, the width every "
            "document in the tree already keeps:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )

    def test_the_imported_tutorial_is_the_only_document_outside_the_rule(self):
        """The exclusion names a file that exists and is still the only one."""

        tracked = set(tracked_markdown())

        missing = sorted(IMPORTED - tracked)

        self.assertEqual(
            missing,
            [],
            "the width exclusion names a document that is no longer tracked, so "
            "it is either renamed or deleted and the entry is stale:\n  " + "\n  ".join(missing),
        )


if __name__ == "__main__":
    unittest.main()
