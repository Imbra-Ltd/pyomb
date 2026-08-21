"""Every tracked file is ASCII, except the em dash the prose deliberately uses.

`templates/base/core/quality.md` requires file content to be restricted to
ASCII. The documents did not follow it and the divergence was never recorded,
so the rule sat unenforced while the em dash spread through the journal, the
decision records, PLAYBOOK, CLAUDE.md and the README. That left the two rules
in direct conflict, because `ai-workflow-match-convention` makes a document's
prior entries the template for its format: writing a new journal entry in ASCII
broke one rule and writing it with an em dash broke the other.

ADR-014 settles it. Markdown prose may use the em dash, and nothing anywhere
may use anything else outside ASCII. This module is the check that rule was
missing, and the reason it is worth having is what the first measurement found:
among several hundred deliberate em dashes sat four genuine defects, invisible
because nothing was counting. A Cyrillic capital Te opened a sentence where a
Latin T belongs and renders identically, so no reader would ever have seen it;
a quoted exception name carried curly quotes; and an en dash stood in for a
hyphen. The em dash allowance is deliberately the narrowest one that lets the
documents stay as they are, so that class of defect still fails here.

ASCII is a range rather than a ceiling, so the check bounds it at both ends.
The low end is the half nobody looks for: a control character renders as
nothing, which hides it better than any homoglyph. The journal carried a NUL
and a DEL inside a code span for a day, in a sentence describing the very grep
that mishandles that range, and the only outward sign was git and grep quietly
reclassifying the file as binary.

The guard is one-directional and needs no fixture: it reads the tree as git
tracks it, so a local scratch file cannot fail a run that CI would pass.
"""

import pathlib
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# The one character prose may carry beyond ASCII. The en dash and the curly
# quotes it gets confused with are not included, and are defects wherever they
# appear -- including in Markdown. Written as an escape so this module, which
# its own first test reads, stays ASCII.
EM_DASH = "\u2014"

# Binary by nature, so "characters" does not apply to them. The Modbus
# specifications are the only ones in the tree.
BINARY_SUFFIXES = {".pdf"}

# ASCII is a range, not a ceiling, and the low end of it is the half nobody
# looks for. A control character reads as nothing at all, so it hides better
# than any homoglyph: the journal carried a NUL and a DEL inside a code span
# for a day, in a sentence about the very grep that mishandles them, and the
# only outward sign was git and grep quietly reclassifying the file as binary.
# Tab and newline are the two that legitimately appear in text; the reader
# strips carriage returns before this sees them.
LEGAL_CONTROL = "\t\n"

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

SUBSTITUTES = (
    "Use '--' for an em dash outside Markdown, '-' for a hyphen, and a "
    "straight quote for a quotation. A character that renders like a Latin "
    "letter but is not one is a homoglyph; replace it with the Latin letter. "
    "A control character below U+0020 renders as nothing and is almost always "
    "a byte written where the text of its escape was meant."
)


def tracked_files():
    """Every path git tracks, relative to the repository root.

    Returns:
        list[str] : The tracked paths, in git's own order
    """

    # The two suppressed checks rest on the same property as the one place the
    # certificate script reaches openssl: the command is a list, which hands the
    # argument vector to the operating system directly rather than to a shell,
    # so nothing here can break out and become a second command. It is also a
    # fixed vector with no caller input in it. The checks match on call shape
    # and cannot see either. Resolving git's absolute path first would trade a
    # suppression for a lookup that can fail on a machine where the check is
    # meaningless anyway.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [name for name in listing.split("\0") if name]


class SourceIsAscii(unittest.TestCase):
    """Pins the ASCII rule to the single exception ADR-014 records."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list to read, and a
        # filesystem walk would pick up ignored artifacts CI never sees. The
        # skip is for that case only; a checkout whose git call fails is a
        # failure, not a skip.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.tracked = tracked_files()

    def offenders(self, markdown, allowed):
        """Locate characters outside printable ASCII in one half of the tree.

        Args:
            markdown (bool) : Select Markdown files when True, the rest when False
            allowed (str)   : Characters beyond printable ASCII that are permitted

        Returns:
            list[str] : One 'path:line:column U+XXXX' entry per offending character
        """

        found = []

        for name in self.tracked:
            path = REPO / name

            # A submodule is tracked as a gitlink rather than a file, and its
            # contents are the upstream project's business, not this rule's.
            if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
                continue

            if (path.suffix.lower() == ".md") != markdown:
                continue

            text = path.read_text(encoding="utf-8")

            # split() rather than splitlines(), which also breaks on the
            # vertical tab, the form feed and the Unicode line separators --
            # so every one of those would be consumed as a line boundary and
            # never appear within a line for this loop to see.
            for row, line in enumerate(text.split("\n"), start=1):
                for column, character in enumerate(line, start=1):
                    if character in allowed or character in LEGAL_CONTROL:
                        continue

                    if not 32 <= ord(character) < 127:
                        found.append(f"{name}:{row}:{column} U+{ord(character):04X}")

        return found

    def test_nothing_outside_markdown_leaves_printable_ascii(self):
        """Source, tests, configuration and workflows are ASCII without exception."""

        offenders = self.offenders(markdown=False, allowed="")

        self.assertEqual(
            offenders,
            [],
            "characters outside printable ASCII found outside Markdown, where "
            "the rule has no exception:\n  " + "\n  ".join(offenders) + "\n" + SUBSTITUTES,
        )

    def test_markdown_carries_nothing_beyond_the_em_dash(self):
        """Prose may use the em dash; a homoglyph or a curly quote is still a defect."""

        offenders = self.offenders(markdown=True, allowed=EM_DASH)

        self.assertEqual(
            offenders,
            [],
            "characters outside printable ASCII found in Markdown, other than "
            "the em dash, which is the only one ADR-014 permits:\n  " + "\n  ".join(offenders) + "\n" + SUBSTITUTES,
        )


if __name__ == "__main__":
    unittest.main()
