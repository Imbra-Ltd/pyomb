"""A numbered heading follows the one above it, without repeating or skipping.

PLAYBOOK reached `main` carrying two sections numbered 3.21 and two numbered
3.22. Both duplicates merged green, in separate pull requests, because each
change appended a section and picked the next number after the last one it had
seen. The defect lives in the document as a whole, where no diff shows it.

A duplicate is worse than a dangling number. A cross-reference to 3.22 pointed
past the end of the document before the collision, which a reader notices at
once, and afterwards resolved to a real section about something else.
PLAYBOOK 3.28 carries what this deliberately reads past.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Published specifications copied in whole. Their numbering belongs to whoever
# wrote them, and the tutorial among them carries a duplicate nobody here owns.
EXCLUDED = ("docs/specs/",)

# A numbered heading, optionally spanning a range: `### 1 to 3. Title` covers
# one through three, so the heading after it opens at four rather than two.
HEADING = re.compile(r"^(#{1,6}) +([0-9]+(?:\.[0-9]+)*)(?: +to +([0-9]+))?\.? ")

FENCE = "```"

# What the tree held when these floors were set: 10 documents carrying 126
# numbered headings. Documents churn, so both take a margin below the measure.
DOCUMENTS_AT_LEAST = 8

ORDINALS_AT_LEAST = 100

# The three the rule is written for. A document may stop carrying numbered
# headings, but not one of these, whose sections are cross-referenced by number.
REQUIRED = ("CLAUDE.md", "docs/ONBOARDING.md", "docs/PLAYBOOK.md")

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

REMEDY = (
    "Read the tail of the section before appending to it: a number picked "
    "after the last heading in the diff collides with the last heading in the "
    "document. Renumber the later section rather than the earlier one, and "
    "check what cites it -- a reference to a duplicated number resolves to a "
    "real section about something else, which reads as correct."
)


def tracked_documents():
    """Every Markdown document git tracks, minus the vendored specifications.

    Returns:
        list[str] : The tracked document paths, in git's own order
    """

    # The argument vector is a list carrying no caller input, so it reaches the
    # operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", "*.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    names = [name for name in listing.split("\0") if name]

    return [name for name in names if not name.startswith(EXCLUDED)]


def headings(text):
    """Yield the numbered headings of one document, fenced blocks skipped.

    Args:
        text (str) : The document's full Markdown source

    Yields:
        tuple[int, str, str, int, int] : Line number, the ordinal as written,
            the parent it groups under, and the first and last values it covers
    """

    fenced = False

    for number, line in enumerate(text.split("\n"), start=1):
        if line.lstrip().startswith(FENCE):
            fenced = not fenced
            continue

        if fenced:
            continue

        found = HEADING.match(line)

        if not found:
            continue

        parts = found.group(2).split(".")

        # Group under the parent and the heading level together, so 3.x and
        # 4.x are separate runs and each may restart at one.
        parent = f"{found.group(1)} {'.'.join(parts[:-1]) or '(root)'}"
        low = int(parts[-1])
        high = int(found.group(3)) if found.group(3) else low

        yield number, found.group(2), parent, low, high


class NumberedHeadingsDoNotCollide(unittest.TestCase):
    """Pins every numbered section to the one above it."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list to read, and a
        # directory walk would pick up scratch files CI never sees.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.documents = tracked_documents()
        cls.inspected = {}

        for name in cls.documents:
            found = list(headings((REPO / name).read_text(encoding="utf-8")))

            if found:
                cls.inspected[name] = found

    def test_the_enumeration_reached_the_documents_it_covers(self):
        """A pass below means the rule was applied, not that nothing was read."""

        total = sum(len(found) for found in self.inspected.values())

        self.assertGreaterEqual(
            len(self.inspected),
            DOCUMENTS_AT_LEAST,
            f"{len(self.inspected)} document(s) carry a numbered heading where "
            f"at least {DOCUMENTS_AT_LEAST} do, so the assertion below would "
            "pass having read almost nothing. A document written but not "
            "staged is invisible here, because the listing reads git's index "
            "rather than the working tree.",
        )

        self.assertGreaterEqual(
            total,
            ORDINALS_AT_LEAST,
            f"the enumeration returned {total} numbered heading(s) where the "
            f"corpus holds at least {ORDINALS_AT_LEAST}. Either the heading "
            "pattern drifted from the convention the documents use, or enough "
            "sections were retired to eat the margin, in which case "
            "re-measure and lower the floor rather than treating this as a "
            "defect.",
        )

        missing = sorted(name for name in REQUIRED if name not in self.inspected)

        self.assertEqual(
            missing,
            [],
            "these documents carry cross-referenced section numbers and "
            "reached this check carrying none, so nothing reads their "
            "numbering:\n  " + "\n  ".join(missing),
        )

    def test_no_numbered_heading_repeats_or_skips_its_neighbour(self):
        """A section number opens where the one above it left off."""

        offenders = []

        for name, found in sorted(self.inspected.items()):
            runs = {}

            for number, written, parent, low, high in found:
                run = runs.setdefault(parent, [])

                # A run is compared against its own last value only, so a
                # document whose first section is not 1 is left alone.
                if run and low <= run[-1][0]:
                    offenders.append(f"{name}:{number} {written} repeats {run[-1][1]} at line {run[-1][2]}")

                elif run and low != run[-1][0] + 1:
                    offenders.append(f"{name}:{number} {written} follows {run[-1][1]} at line {run[-1][2]}")

                run.append((high, written, number))

        self.assertEqual(
            offenders,
            [],
            "numbered headings that repeat or skip the one above them, where a "
            "cross-reference resolves to the wrong section:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
