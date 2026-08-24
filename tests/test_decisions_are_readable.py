"""Decision records stay readable: bounded sentences, bounded paragraphs.

A decision record is read once, months later, by someone deciding whether the
decision still holds. The prose that costs them is not long prose -- it is a
single sentence carrying an enumeration, where three reasons are chained on
semicolons and the reader has to hold all of the first one while parsing the
third. The records here reached a seventy-three-word sentence of exactly that
shape before anything measured them.

The two limits below are one rule: a sentence is the unit a reader holds at
once, and a paragraph may hold two of them. Both are calibrated rather than
chosen -- see the constants for the distribution each came from and the
command that re-measures it.

What the check deliberately does not read:

Fenced blocks carry the ASCII diagrams the decision format asks for, and a
diagram has no sentences. Tables are the format the decision template asks for
under Alternatives considered and Consequences, and a cell is already a short
unit. Headings are titles. Block quotes are verbatim quotations of the pinned
templates: they are the rule a record is measured against, they are not this
project's prose, and rewriting one to fit a limit would falsify the quotation.

The limits apply to list items too, because a sentence is a sentence wherever
it sits. Without that the rule would be trivially satisfied by moving a
sixty-word sentence under a bullet, which moves the reader's problem rather
than fixing it. Only the paragraph limit is scoped to paragraphs: a list item
is already a structural break, so bounding its sentences is enough.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# The records this rule governs. Prose elsewhere in the tree is not held to it:
# the journal is a session log written at speed, and the README and the agent
# context file already measure well inside these limits without a gate.
DECISIONS = "docs/decisions/"

# Calibrated against the prose the project is measured by rather than picked as
# a round number. Across the seventy-one pinned template files the 99th
# percentile sentence is 42 words, and the two documents this project keeps
# tightest -- the README and the agent context file -- top out at 41. Forty is
# where that prose already sits, so the gate refuses what those authors would
# not have written. It is not a style preference: below about 35 the limit
# falls under the templates' own 99th percentile and the gate would be stricter
# than the prose it inherits, which is a gate the project would fight.
MAX_SENTENCE_WORDS = 40

# Two maximum-length sentences. The relation is the point -- a paragraph that
# runs past two full sentences is where a reader loses the thread, and deriving
# the bound from the sentence limit keeps the two from drifting apart when one
# is re-measured.
MAX_PARAGRAPH_WORDS = 2 * MAX_SENTENCE_WORDS

# The gate itself is `pytest tests/test_decisions_are_readable.py`, and it
# passes when both lists below come back empty. Re-calibrating is the separate
# job: it needs the word-length distribution of the current corpus against the
# pinned templates, and the run that set these two numbers is recorded in the
# decision record that introduced this module, under its measurement heading.

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

REMEDY = (
    "A sentence over the limit almost always carries a list. Render it as a "
    "list: the words survive, the reader stops having to hold three clauses "
    "at once, and the count falls out. A paragraph over the limit usually "
    "holds two subjects; give the second its own paragraph. Neither fix "
    "changes what a record claims, and a fix that does is a new decision "
    "rather than an edit."
)

# A period ends a sentence only where what follows starts a new one. Requiring
# an opening character keeps a version number, an ellipsis and an abbreviation
# from splitting one sentence into two. The backtick is in the set because a
# record routinely opens a sentence with an identifier, and missing that
# boundary would join two sentences and report a length neither has.
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[\"'`])")

# A code span is one unit to a reader regardless of what it holds, and a period
# inside one is never a sentence boundary. Collapsing each to a single token
# before splitting removes both problems at once.
CODE_SPAN = re.compile(r"`[^`]*`")

BULLET = re.compile(r"^([-*]|\d+\.)\s+")


def tracked_decisions():
    """Every decision record git tracks, relative to the repository root.

    Returns:
        list[str] : The tracked decision-record paths, in git's own order
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell and cannot
    # become a second command. The checks match on call shape and cannot see
    # that. Resolving git's absolute path first would trade a suppression for a
    # lookup that fails on a machine where the check is meaningless anyway.
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

    # The record's YAML front matter is metadata rather than prose: it holds
    # fields, not sentences, so measuring it as a paragraph asks a question it
    # has no answer to. Its width is still the width gate's business.
    front_matter = False

    def flush():
        nonlocal buffered
        if buffered:
            found.append(("paragraph", opened, " ".join(buffered)))
        buffered = []

    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.strip()

        # Only a delimiter on the very first line opens front matter, so a
        # thematic break further down the document is not mistaken for one.
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

        # Each of these ends whatever paragraph was accumulating: a blank line
        # and a heading by definition, a table row and a block quote because
        # the unit that follows is not the one that preceded it.
        if not line or line.startswith(("#", "|", ">")):
            flush()
            continue

        # The metadata the decision format puts above the first heading. These
        # are fields rather than prose, and the value of one is a date or a
        # status word.
        if line.startswith(("**Status:**", "**Date:**")):
            flush()
            continue

        if BULLET.match(line):
            flush()
            found.append(("list item", number, BULLET.sub("", line)))
            continue

        # An indented continuation belongs to the list item above it, not to a
        # new paragraph. Without this a wrapped bullet would be measured twice:
        # once short as the item, once short as a paragraph.
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
        # Absent a checkout there is no tracked-file list to read, and a
        # directory walk would pick up scratch files CI never sees. The skip is
        # for that case only; a checkout whose git call fails is a failure.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.records = tracked_decisions()

    def test_a_decision_record_carries_no_sentence_past_the_limit(self):
        """No sentence in a decision record exceeds the calibrated word limit."""

        offenders = []

        for name in self.records:
            for _, number, prose in units((REPO / name).read_text(encoding="utf-8")):
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

        for name in self.records:
            for kind, number, prose in units((REPO / name).read_text(encoding="utf-8")):
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
