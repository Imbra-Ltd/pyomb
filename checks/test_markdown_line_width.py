"""Markdown prose wraps at the width the project declares.

The documents already did this before anything checked, and what was missing
was the rule: nothing declared a width for Markdown at all. So the convention
was real, unwritten and held by hand -- and already slipping, because a
98-column heading reached a green pipeline.

The width is declared once, in `.editorconfig`, and read from there rather than
restated. A tree declaring none fails here rather than falling back to a
default, since an unstated width is the defect itself. PLAYBOOK 3.15 carries
the exemptions and why none of them can be wrapped.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# The one place the width is written down, so an edit to the declaration moves
# the gate with it rather than leaving the two disagreeing.
EDITORCONFIG = REPO / ".editorconfig"

# A section header naming Markdown, alone or in a brace list. Matched against
# the bracketed line, so a section such as [*.cmd] cannot answer to it.
MARKDOWN_SECTION = re.compile(r"[.{,]md[},\]]")

WIDTH_KEY = "max_line_length"

# Imported with the v0.1.0 tree at its own width. The exclusion is the rule's
# scope; a document this project authored has no such escape.
IMPORTED = {"docs/specs/Open_Modbus_Tutorial.md"}

# A URL survives no line break, so a line carrying one is measured by nothing
# the author can act on. A relative link is short and is not exempt.
URL = re.compile(r"https?://")

REMEDY = (
    "Wrap the line at or before the declared column. A heading that will not "
    "fit wants a shorter title rather than a longer line, and a table or a "
    "fenced block does not need wrapping because neither is measured here."
)

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

# What the tree held when this floor was set: 33 documents inside the rule.
# Markdown churns, so the floor takes a margin below the measured count.
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
        # whatever precedes the first '=' on its own line.
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
    # the operating system directly rather than through a shell.
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
        # Absent a checkout there is no tracked-file list, and a directory walk
        # would pick up scratch files CI never sees.
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
