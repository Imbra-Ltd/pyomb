"""Source stays printable ASCII; Markdown carries only what a reader can see.

The printable restriction was lifted off Markdown altogether. A document is
written for a reader, so a box-drawing diagram, an arrow or a quotation in
another script is content rather than drift. What survives the lift is the half
a reader cannot see: a control character renders as nothing, and one of them is
load-bearing for a second gate -- a single NUL makes git classify a file as
binary, which stops line-ending normalisation and blinds that rule.

So the two halves are held to two different rules. PLAYBOOK 3.13 carries the
incident behind the second and what substitutes for what.
"""

import pathlib
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Binary by nature, so "characters" does not apply to them. The Modbus
# specifications are the only ones in the tree.
BINARY_SUFFIXES = {".pdf"}

# The two control characters that legitimately appear in text. The reader
# strips carriage returns before either rule below sees them.
LEGAL_CONTROL = "\t\n"

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

# What each half held when these floors were set: 34 Markdown files and 97
# other readable ones. Counted separately, since the rules below read one each.
MARKDOWN_AT_LEAST = 16

OTHER_AT_LEAST = 48

SOURCE_SUBSTITUTES = (
    "Use '--' for an em dash, '-' for a hyphen, and a straight quote for a "
    "quotation. A character that renders like a Latin letter but is not one "
    "is a homoglyph; replace it with the Latin letter. A control character "
    "below U+0020 renders as nothing and is almost always a byte written "
    "where the text of its escape was meant."
)

MARKDOWN_SUBSTITUTES = (
    "A control character renders as nothing, so the line does not hold what "
    "it appears to -- the character is almost always a byte written where the "
    "text of its escape was meant, and deleting it is the fix. A NUL is the "
    "one that reaches past its own line: it makes git classify the file as "
    "binary, which stops line-ending normalisation and leaves "
    "checks/test_line_endings.py reading a clean tree over a file full of CRLF."
)


def legal_in_source(character):
    """Whether a character may appear outside Markdown.

    Args:
        character (str) : One character read from a tracked file

    Returns:
        bool : True where the character is printable ASCII, tab or newline
    """

    return character in LEGAL_CONTROL or 32 <= ord(character) <= 126


def legal_in_markdown(character):
    """Whether a character may appear in Markdown.

    Args:
        character (str) : One character read from a tracked document

    Returns:
        bool : True unless the character is an invisible control character
    """

    code = ord(character)

    # Everything except the two Unicode control blocks, U+0000-U+001F and
    # U+007F-U+009F. The first carries the NUL that blinds the line-ending gate.
    return character in LEGAL_CONTROL or 32 <= code <= 126 or code >= 160


def tracked_files():
    """Every path git tracks, relative to the repository root.

    Returns:
        list[str] : The tracked paths, in git's own order
    """

    # The argument vector is a fixed list and carries no caller input, so it
    # reaches the operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [name for name in listing.split("\0") if name]


def readable_halves(tracked):
    """Split the tracked paths into the two populations the rules read.

    Args:
        tracked (list[str]) : Every tracked path, in git's own order

    Returns:
        tuple[list[str], list[str]] : The Markdown paths and the other
            readable ones, with binaries and the submodule gitlink dropped
    """

    markdown = []
    other = []

    for name in tracked:
        path = REPO / name

        # A submodule is tracked as a gitlink rather than a file, and its
        # contents are the upstream project's business, not this rule's.
        if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
            continue

        (markdown if path.suffix.lower() == ".md" else other).append(name)

    return markdown, other


class SourceIsAscii(unittest.TestCase):
    """Pins each half of the tree to the character set its own rule allows."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list, and a filesystem
        # walk would pick up ignored artifacts CI never sees.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.tracked = tracked_files()
        cls.markdown, cls.other = readable_halves(cls.tracked)

    def scan(self, names, is_legal):
        """Locate the characters one half's rule does not permit.

        Args:
            names (list[str]) : The paths to read, already filtered to one half
            is_legal (object) : The rule that half is held to, taking one
                character and returning whether it may appear

        Returns:
            list[str] : One 'path:line:column U+XXXX' entry per offending character
        """

        found = []

        for name in names:
            path = REPO / name

            text = path.read_text(encoding="utf-8")

            # split() rather than splitlines(), which breaks on the vertical
            # tab and form feed -- consuming the characters this rule looks for.
            for row, line in enumerate(text.split("\n"), start=1):
                for column, character in enumerate(line, start=1):
                    if not is_legal(character):
                        found.append(f"{name}:{row}:{column} U+{ord(character):04X}")

        return found

    def test_the_enumeration_reached_both_halves_of_the_tree(self):
        """A pass below means the characters were read, not that none were."""

        self.assertGreaterEqual(
            len(self.markdown),
            MARKDOWN_AT_LEAST,
            f"the enumeration returned {len(self.markdown)} Markdown file(s) "
            f"where the tree holds at least {MARKDOWN_AT_LEAST}, so the "
            "control-character rule below would pass having read almost "
            "nothing. A document that is written but not staged is invisible "
            "here, because the listing reads git's index rather than the "
            "working tree.",
        )

        self.assertGreaterEqual(
            len(self.other),
            OTHER_AT_LEAST,
            f"the enumeration returned {len(self.other)} readable non-Markdown "
            f"file(s) where the tree holds at least {OTHER_AT_LEAST}, so the "
            "rule below would pass having read almost nothing. Either the "
            "listing is not reaching the repository or the binary filter has "
            "started dropping files it was never meant to.",
        )

    def test_nothing_outside_markdown_leaves_printable_ascii(self):
        """Source, tests, configuration and workflows are ASCII without exception."""

        offenders = self.scan(self.other, legal_in_source)

        self.assertEqual(
            offenders,
            [],
            "characters outside printable ASCII found outside Markdown, where "
            "the rule has no exception:\n  " + "\n  ".join(offenders) + "\n" + SOURCE_SUBSTITUTES,
        )

    def test_markdown_carries_no_control_characters(self):
        """Prose may carry any visible character; one that renders as nothing may not."""

        offenders = self.scan(self.markdown, legal_in_markdown)

        self.assertEqual(
            offenders,
            [],
            "control characters found in Markdown, which may carry any "
            "character a reader can see and none that renders as "
            "nothing:\n  " + "\n  ".join(offenders) + "\n" + MARKDOWN_SUBSTITUTES,
        )


if __name__ == "__main__":
    unittest.main()
