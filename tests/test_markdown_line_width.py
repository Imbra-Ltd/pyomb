"""Markdown prose wraps at the width the project declares.

The documents already do this. Every governance and reference file the project
maintains -- the agent context file, the README, CONTRIBUTING, PLAYBOOK,
ONBOARDING, the journal, the audits and the decision records -- holds its prose
to 80 columns, and did so before anything checked. What was missing was the
rule: nothing declared a width for Markdown at all, and CONTRIBUTING states 120
with 80 recommended under a heading that reads Code style. So the convention
was real, unwritten, and held by hand.

It was also already slipping. A 98-column heading reached a green pipeline,
because no gate in the project read the width of a Markdown line.

The width is declared once, in `.editorconfig` under the Markdown section, and
this module reads it from there rather than restating it. A number written in
both places is one fact represented twice, and two copies drift with nothing to
say which one won. A tree that declares no width fails here rather than falling
back to a default, because an unstated width is the defect itself and not a gap
for the check to fill in.

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

# The one place the width is written down. Reading it here rather than
# restating it keeps the number to a single copy, so an edit to the declaration
# moves the gate with it instead of leaving the two disagreeing.
EDITORCONFIG = REPO / ".editorconfig"

# An EditorConfig section header naming Markdown, whether on its own or inside
# a brace list of extensions. Matched against the bracketed line so the closing
# bracket is available as a delimiter, which keeps a section such as [*.cmd]
# from answering to it.
MARKDOWN_SECTION = re.compile(r"[.{,]md[},\]]")

WIDTH_KEY = "max_line_length"

# Imported with the v0.1.0 tree rather than written to this convention, and
# wrapped at about 96 throughout: its prose sits at a median of 35 columns and a
# 90th percentile of 94. It is protocol reference material, internally
# consistent at its own width, and rewrapping 160 lines of it would bury a
# change nobody asked for. The exclusion is the rule's scope, not a suppression
# of findings inside it -- a document this project authored has no such escape.
IMPORTED = {"docs/specs/Open_Modbus_Tutorial.md"}

# A URL survives no line break, so a line carrying one is measured by nothing
# the author can act on. This covers the badge block at the top of the README,
# which is two long links and a label. A relative link is not exempt: it is
# short, and the prose around it wraps like any other.
URL = re.compile(r"https?://")

REMEDY = (
    "Wrap the line at or before the declared column. A heading that will not "
    "fit wants a shorter title rather than a longer line, and a table or a "
    "fenced block does not need wrapping because neither is measured here."
)

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

# What the tree held when this floor was set: 33 documents inside the rule, out
# of 34 tracked. The floor sits at roughly half, because Markdown churns -- a
# retired guide is an ordinary deletion and must not fail a width rule. Every
# way this enumeration breaks returns nothing at all, so the margin costs no
# detection. The stale-exclusion test below happens to fail on an empty listing
# too, but it reports a renamed tutorial rather than a broken enumeration, and
# those are different failures wanting different fixes.
DOCUMENTS_AT_LEAST = 16

UNDECLARED = (
    f"no Markdown width is declared: .editorconfig carries no {WIDTH_KEY} under "
    "a section naming Markdown, so the rule has no number and this check has "
    "nothing to read. An unstated width is the defect rather than a gap for "
    "the check to fill in with a default, so declare one there."
)


def configured_width():
    """Read the Markdown width the project declares in .editorconfig.

    Returns:
        int | None : The declared width, or None when the file is absent or
            no section naming Markdown declares one
    """

    if not EDITORCONFIG.is_file():
        return None

    in_markdown = False

    for line in EDITORCONFIG.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            in_markdown = bool(MARKDOWN_SECTION.search(stripped))
            continue

        # EditorConfig has no continuations and no interpolation, so a key is
        # whatever precedes the first '=' on its own line. A full parser would
        # be a dependency bought for one integer.
        if in_markdown and stripped.startswith(WIDTH_KEY):
            key, sep, value = stripped.partition("=")

            if sep and key.strip() == WIDTH_KEY and value.strip().isdigit():
                return int(value.strip())

    return None


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


def overlong(text, limit):
    """Locate the lines in one document that exceed the width.

    Args:
        text (str)  : The document's full Markdown source
        limit (int) : The declared width, in characters

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

        if len(line) > limit:
            found.append((number, len(line), line))

    return found


class MarkdownLineWidth(unittest.TestCase):
    """Pins the wrap the documents already keep, at the declared width."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list to read, and a
        # directory walk would pick up scratch files CI never sees. The skip is
        # for that case only; a checkout whose git call fails is a failure.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.limit = configured_width()
        cls.documents = [name for name in tracked_markdown() if name not in IMPORTED]

    def test_the_width_is_declared_in_configuration(self):
        """The rule carries no number of its own; the declaration holds it."""

        self.assertIsNotNone(self.limit, UNDECLARED)

    def test_the_enumeration_reached_the_tracked_documents(self):
        """A pass below means the widths were read, not that none were."""

        self.assertGreaterEqual(
            len(self.documents),
            DOCUMENTS_AT_LEAST,
            f"the enumeration returned {len(self.documents)} document(s) where "
            f"the tree holds at least {DOCUMENTS_AT_LEAST}, so the width rule "
            "below would pass having read almost nothing. A document that is "
            "written but not staged is invisible here, because the listing "
            "reads git's index rather than the working tree; anything else "
            "means the pattern has stopped matching.",
        )

    def test_no_markdown_line_runs_past_the_width(self):
        """Prose, headings and list items stay within the declared width."""

        self.assertIsNotNone(self.limit, UNDECLARED)

        offenders = []

        for name in self.documents:
            text = (REPO / name).read_text(encoding="utf-8")

            for number, width, line in overlong(text, self.limit):
                offenders.append(f"{name}:{number} ({width}) {line[:56]}")

        self.assertEqual(
            offenders,
            [],
            f"Markdown lines past {self.limit} columns, the width .editorconfig "
            "declares and every document in the tree already keeps:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
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
