"""A decision record links to another through its front matter, not its prose.

`templates/base/core/docs.md` requires that the only record-to-record links be
the `supersedes` and `superseded_by` fields, because those are the only ones a
check can validate. A prose reference rots silently: the record it names gets
superseded, or its reasoning is withdrawn, and the sentence pointing at it goes
on reading exactly as it did.

The rule arrived at `v2.46.0`, after nineteen records had already merged, and
the same file declares a merged record immutable. Fourteen of the nineteen cite
another record in a prose body and eight of those do it inside a Decision
section, where the citation is usually the decision rather than a pointer
beside it -- so rewriting them is not the content-preserving format migration
the immutability rule permits. ADR-020 settles it: the prohibition binds
records numbered 020 and above, and the ones below keep their prose as merged.

That makes the boundary the whole content of this module, and the reason it is
a constant with this comment beside it rather than a number inline.

Two things are deliberately not read. A fenced block is skipped, so a record
may quote the rule or the command that measures compliance without failing
itself -- ADR-020 does both. The closing pointers section is skipped, because
the template permits context-only links there; what it may not carry is
decision-bearing text, which no check can judge and review has to.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

DECISIONS = "docs/decisions/"

# The first record the rule covers. Records below it merged before the rule
# existed, and the immutability rule protects their prose from being rewritten
# to satisfy it. Raising this number would exempt a record that was authored
# under the rule, which is the one edit this constant must never take.
FIRST_GATED = 20

# A record's file name opens with its zero-padded number, which is also its
# front-matter id.
NUMBERED = re.compile(r"^(\d{3})-")

# A reference to a record, in the form the documents use.
CITATION = re.compile(r"ADR-(\d{3})")

# Everything from the closing pointers heading onward is outside the rule.
RELATED = re.compile(r"^##\s+Related\b")

FENCE = "```"

REMEDY = (
    "Move the link into the front matter when it is a supersession, or into a "
    "closing Related section when it is context only. A reference that carries "
    "the decision cannot move: state the substance instead, naming what was "
    "decided rather than the record that decided it."
)

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

# What the directory held when these floors were set: twenty-two numbered
# records, of which three sit at or above the boundary. A record is append-only
# -- it merges and is never deleted, since a superseded one stays in the tree
# carrying the link to what replaced it -- so both counts only ever rise. They
# are floors rather than non-empty checks because a listing that comes back
# holding one record satisfies non-emptiness while measuring almost nothing.
RECORDS_AT_LEAST = 22

GATED_AT_LEAST = 3


def tracked_decisions():
    """Every numbered decision record git tracks.

    Returns:
        list[str] : The tracked record paths, in git's own order
    """

    # The argument vector is a list carrying no caller input, so it reaches the
    # operating system directly rather than through a shell. The checks match
    # on call shape and cannot see that.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", DECISIONS],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [name for name in listing.split("\0") if name and NUMBERED.match(pathlib.Path(name).name)]


def number(name):
    """Read a record's number from its file name.

    Args:
        name (str) : The record's repository-relative path

    Returns:
        int : The leading digits of the file name
    """

    return int(NUMBERED.match(pathlib.Path(name).name).group(1))


def prose_lines(text):
    """Yield the lines of a record that the rule actually covers.

    Args:
        text (str) : The record's full Markdown source

    Yields:
        tuple[int, str] : Line number and content, fences and the closing
            pointers section already removed
    """

    fenced = False

    for count, line in enumerate(text.split("\n"), start=1):
        if line.lstrip().startswith(FENCE):
            fenced = not fenced
            continue

        if fenced:
            continue

        # The closing section and everything after it is context only, so the
        # rule stops here rather than at the end of the file.
        if RELATED.match(line):
            return

        yield count, line


class DecisionCitations(unittest.TestCase):
    """Pins the citation rule to the records ADR-020 brings into scope."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list to read, and a
        # directory walk would pick up scratch files CI never sees.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.records = tracked_decisions()
        cls.gated = [name for name in cls.records if number(name) >= FIRST_GATED]

    def test_the_enumeration_reached_the_records_in_scope(self):
        """A pass means the rule was applied, not that nothing was read."""

        self.assertGreaterEqual(
            len(self.records),
            RECORDS_AT_LEAST,
            f"the enumeration returned {len(self.records)} numbered record(s) "
            f"where the directory holds at least {RECORDS_AT_LEAST}. A new "
            "record that is written but not staged is invisible here, because "
            "the listing reads git's index rather than the working tree; "
            "anything else means the path this module looks under has moved.",
        )

        self.assertGreaterEqual(
            len(self.gated),
            GATED_AT_LEAST,
            f"{len(self.gated)} tracked record(s) are numbered "
            f"{FIRST_GATED:03d} or above, where at least {GATED_AT_LEAST} are, "
            "so the assertion below would pass having read almost nothing. "
            "Either the boundary moved or the records did.",
        )

    def test_a_gated_record_cites_no_other_record_in_its_prose(self):
        """From the boundary on, the front matter carries every link."""

        offenders = []

        for name in self.gated:
            own = number(name)
            text = (REPO / name).read_text(encoding="utf-8")

            for count, line in prose_lines(text):
                for found in CITATION.finditer(line):
                    # A record naming itself is its own title, not a citation.
                    if int(found.group(1)) != own:
                        offenders.append(f"{name}:{count} {found.group(0)}")

        self.assertEqual(
            offenders,
            [],
            "decision records citing another record in their prose body, "
            "where a reference rots without anything noticing:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )

    def test_the_boundary_names_a_record_that_exists(self):
        """A boundary pointing past the last record would gate nothing."""

        # The default keeps an empty listing reporting the boundary rather than
        # raising on an empty max(), so the coverage test above is what names
        # a broken enumeration and this one keeps naming a stale boundary.
        highest = max((number(name) for name in self.records), default=0)

        self.assertLessEqual(
            FIRST_GATED,
            highest,
            f"the boundary is {FIRST_GATED:03d} but the highest tracked record "
            f"is {highest:03d}, so nothing is in scope and the rule holds only "
            "by there being no record to break it.",
        )


if __name__ == "__main__":
    unittest.main()
