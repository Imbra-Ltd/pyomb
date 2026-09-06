"""Decision records stay readable: bounded sentences, bounded paragraphs.

A record is read once, months later, by someone deciding whether the decision
still holds. What costs that reader is not long prose but a single sentence
carrying an enumeration -- three reasons chained on semicolons, the first of
which has to be held intact while the third is parsed. The records reached a
seventy-three-word sentence of that shape before anything measured them.

Both limits reach list items as well as paragraphs, or the rule would be
satisfied by putting a bullet in front of a long sentence. PLAYBOOK 3.14
carries what the check reads past and why.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# The records this rule governs. The journal is a session log written at speed,
# and the README and the context file already measure inside these limits.
DECISIONS = "docs/decisions/"

# Calibrated rather than chosen: the pinned templates' 99th-percentile sentence
# is 42 words, and this project's tightest prose tops out at 41.
MAX_SENTENCE_WORDS = 40

# Two maximum-length sentences, derived from the limit above so re-measuring
# one cannot leave the pair drifting apart.
MAX_PARAGRAPH_WORDS = 2 * MAX_SENTENCE_WORDS

# What the directory held when this floor was set, template included. A record
# is append-only, so the measured count is a floor that only ever rises.
RECORDS_AT_LEAST = 23

# The corpus reached 967 sentences across 501 units when this was set. The
# margin is for a parser correction, not for the failure this catches.
SENTENCES_AT_LEAST = 450

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

REMEDY = (
    "A sentence over the limit almost always carries a list. Render it as a "
    "list: the words survive, the reader stops having to hold three clauses "
    "at once, and the count falls out. A paragraph over the limit usually "
    "holds two subjects; give the second its own paragraph. Neither fix "
    "changes what a record claims, and a fix that does is a new decision "
    "rather than an edit."
)

# A period ends a sentence only where what follows opens one, so a version
# number, an ellipsis and an abbreviation do not split one. A backtick opens.
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[\"'`])")

# A code span is one unit to a reader, and a period inside one is never a
# boundary. Collapsing each to a token before splitting removes both problems.
CODE_SPAN = re.compile(r"`[^`]*`")

BULLET = re.compile(r"^([-*]|\d+\.)\s+")


def tracked_decisions():
    """Every decision record git tracks, relative to the repository root.

    Returns:
        list[str] : The tracked decision-record paths, in git's own order
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", DECISIONS],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [name for name in listing.split("\0") if name and name.endswith(".md")]


def units(text):
    """Split one record into the prose units the limits apply to.

    Args:
        text (str) : The record's full Markdown source

    Returns:
        list[tuple[str, int, str]] : One (kind, line, prose) triple per unit,
            where kind is 'paragraph' or 'list item' and line is 1-based
    """

    found = []
    buffered = []
    opened = 0
    fenced = False

    # Front matter holds fields rather than sentences, so measuring it as a
    # paragraph asks a question it has no answer to.
    front_matter = False

    def flush():
        nonlocal buffered
        if buffered:
            found.append(("paragraph", opened, " ".join(buffered)))
        buffered = []

    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.strip()

        # Only a delimiter on the very first line opens front matter, so a
        # thematic break further down is not mistaken for one.
        if line == "---" and (number == 1 or front_matter):
            front_matter = number == 1
            continue

        if front_matter:
            continue

        # A fence toggles rather than nests, so the diagrams between a pair of
        # them are skipped whatever they contain.
        if line.startswith("```"):
            fenced = not fenced
            flush()
            continue

        if fenced:
            continue

        # Each of these ends whatever paragraph was accumulating, because the
        # unit that follows is not the one that preceded it.
        if not line or line.startswith(("#", "|", ">")):
            flush()
            continue

        # The metadata the decision format puts above the first heading. These
        # are fields, and the value of one is a date or a status word.
        if line.startswith(("**Status:**", "**Date:**")):
            flush()
            continue

        if BULLET.match(line):
            flush()
            found.append(("list item", number, BULLET.sub("", line)))
            continue

        # An indented continuation belongs to the item above it. Without this a
        # wrapped bullet would be measured twice, short both times.
        if raw.startswith((" ", "\t")) and found and found[-1][0] == "list item":
            kind, line_number, prose = found[-1]
            found[-1] = (kind, line_number, prose + " " + line)
            continue

        if not buffered:
            opened = number

        buffered.append(line)

    flush()

    return found


def sentences(prose):
    """Split one prose unit into sentences.

    Args:
        prose (str) : The unit's text, already joined onto a single line

    Returns:
        list[str] : The sentences, in order, with code spans collapsed
    """

    collapsed = CODE_SPAN.sub("CODE", prose)

    return [part.strip() for part in SENTENCE_BREAK.split(collapsed) if part.strip()]


class DecisionsAreReadable(unittest.TestCase):
    """Pins the sentence and paragraph limits the decision records are held to."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list, and a directory walk
        # would pick up scratch files CI never sees.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.records = tracked_decisions()

        # Parsed once here rather than in each test below, so the coverage
        # assertion and the two limits all report on the same reading.
        cls.measured = [
            (name, kind, number, prose)
            for name in cls.records
            for kind, number, prose in units((REPO / name).read_text(encoding="utf-8"))
        ]

    def test_the_enumeration_reached_the_records_and_their_prose(self):
        """A pass below means the prose was measured, not that none was found."""

        self.assertGreaterEqual(
            len(self.records),
            RECORDS_AT_LEAST,
            f"the enumeration returned {len(self.records)} record(s) where the "
            f"directory holds at least {RECORDS_AT_LEAST}, so both limits "
            "below would pass having read almost nothing. A new record that is "
            "written but not staged is invisible here, because the listing "
            "reads git's index rather than the working tree; anything else "
            "means the path this module looks under has moved.",
        )

        counted = sum(len(sentences(prose)) for _, _, _, prose in self.measured)

        self.assertGreaterEqual(
            counted,
            SENTENCES_AT_LEAST,
            f"the records parsed to {len(self.measured)} unit(s) carrying "
            f"{counted} sentence(s), where the corpus holds at least "
            f"{SENTENCES_AT_LEAST}. The file list is reached and the prose is "
            "not, so the limits below are measuring an empty set. Either the "
            "unit reader or the sentence split has stopped returning what the "
            "records hold.",
        )

    def test_a_decision_record_carries_no_sentence_past_the_limit(self):
        """No sentence in a decision record exceeds the calibrated word limit."""

        offenders = []

        for name, _, number, prose in self.measured:
            for sentence in sentences(prose):
                length = len(sentence.split())

                if length > MAX_SENTENCE_WORDS:
                    offenders.append(f"{name}:{number} {length} words: {sentence[:60]}...")

        self.assertEqual(
            offenders,
            [],
            f"sentences longer than {MAX_SENTENCE_WORDS} words, the length past "
            "which a reader is holding more clauses than the sentence resolves:"
            "\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )

    def test_a_decision_record_carries_no_paragraph_past_the_limit(self):
        """No prose paragraph in a decision record exceeds two full sentences."""

        offenders = []

        for name, kind, number, prose in self.measured:
            length = len(prose.split())

            if kind == "paragraph" and length > MAX_PARAGRAPH_WORDS:
                offenders.append(f"{name}:{number} {length} words")

        self.assertEqual(
            offenders,
            [],
            f"paragraphs longer than {MAX_PARAGRAPH_WORDS} words, which is two "
            "sentences at the limit above and the point a paragraph stops "
            "holding one subject:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
