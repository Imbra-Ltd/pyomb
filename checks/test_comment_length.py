"""Comments and docstrings stay within the length CLAUDE.md 2.2 sets.

Length here is a proxy for placement. A comment that needs a paragraph is
usually explaining something that belongs in PLAYBOOK or a decision record,
where a reader can find it without opening the source; left in place it grows
by imitation, because the next author copies the neighbours rather than the
rule.

The bound is on prose, not on the contract: a docstring's `Args:`, `Returns:`
and `Raises:` sections are excluded, so annotating a wide signature never
costs anything here. Whether a comment was needed at all is a judgement this
cannot reach, and review keeps it.
"""

import ast
import pathlib
import subprocess  # nosec B404
import tokenize
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# The directories under the bound. Each migration slice adds one as it cleans
# it, so the gate and the tree widen together.
ROOTS = ("scripts", "examples")

COMMENT_LINES = 2

DOCSTRING_PROSE_LINES = 10

# The Google sections that carry the contract or a gated example rather than
# explanation. Everything else in a docstring counts as prose.
CONTRACT = (
    "Args:",
    "Arguments:",
    "Attributes:",
    "Example:",
    "Examples:",
    "Raises:",
    "Returns:",
    "Yields:",
)

OWNS_A_DOCSTRING = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

# A licence header opens the file and is a legal notice rather than an
# explanation, so its length is not this project's to choose.
LICENCE = ("Copyright", "SPDX-License-Identifier")

# What the two roots held when this floor was set: 8 modules on 2026-09-05.
# Files churn, so the floor takes a margin below the measured count.
FILES_AT_LEAST = 5

REMEDY = (
    "Read the block, then delete it if it restates the code, move it to "
    "docs/PLAYBOOK.md if it is operational, or to a decision record if it is "
    "design reasoning that has to stay fixed. Compressing it in place "
    "satisfies the count and fails the reader it was written for."
)


def sources():
    """Every tracked Python module under the roots the bound covers.

    Returns:
        list[str] : Repository-relative paths, in git's own order
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "*.py"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    ).stdout.split()

    return [name for name in listing if name.split("/")[0] in ROOTS]


def comment_blocks(path):
    """Runs of consecutive comment lines in one module.

    Read through `tokenize` rather than line-wise, so a `#` inside a string or
    a docstring is not mistaken for a comment. Two things are deliberately not
    blocks: a licence header, which is a legal notice rather than an
    explanation, and a comment trailing code, which is one label on one line
    however many of them stack up.

    Args:
        path (str) : Repository-relative path to a Python module

    Returns:
        list[tuple[int, int]] : Each run's first line and its length
    """

    source = (REPO / path).read_text(encoding="utf-8").splitlines()

    with open(str(REPO / path), "rb") as handle:
        tokens = list(tokenize.tokenize(handle.readline))

    rows = sorted(
        token.start[0]
        for token in tokens
        if token.type == tokenize.COMMENT and not source[token.start[0] - 1][: token.start[1]].strip()
    )

    runs, run, start, previous = [], 0, None, None

    for row in rows:
        if previous is not None and row == previous + 1:
            run += 1
        else:
            if run:
                runs.append((start, run))
            run, start = 1, row
        previous = row

    if run:
        runs.append((start, run))

    if runs and runs[0][0] == 1 and any(word in source[0] for word in LICENCE):
        runs = runs[1:]

    return runs


def docstring_prose(text):
    """How many lines of explanation a docstring carries.

    Args:
        text (str) : The docstring, uncleaned

    Returns:
        int : Non-blank lines before the first contract section
    """

    lines = text.strip().splitlines()

    for number, line in enumerate(lines):
        if line.strip() in CONTRACT:
            lines = lines[:number]
            break

    return len([line for line in lines if line.strip()])


def docstrings(path):
    """Every docstring in one module, with the prose each carries.

    Args:
        path (str) : Repository-relative path to a Python module

    Returns:
        list[tuple[int, int, str]] : Line, prose length, and the owner's name
    """

    tree = ast.parse((REPO / path).read_text(encoding="utf-8"))
    found = []

    for node in ast.walk(tree):
        if not isinstance(node, OWNS_A_DOCSTRING):
            continue

        text = ast.get_docstring(node, clean=False)

        if text is None:
            continue

        owner = getattr(node, "name", "<module>")
        found.append((getattr(node, "lineno", 1), docstring_prose(text), owner))

    return found


class CommentsAndDocstringsAreBounded(unittest.TestCase):
    """Pins both lengths over the directories the migration has reached."""

    @classmethod
    def setUpClass(cls):
        cls.paths = sources()

    def test_the_listing_reached_the_modules_under_the_bound(self):
        """A pass below means the modules were read, not that none were found."""

        self.assertGreaterEqual(
            len(self.paths),
            FILES_AT_LEAST,
            f"the listing reached {len(self.paths)} module(s) under {ROOTS} "
            f"where the floor is {FILES_AT_LEAST}. Both assertions below are "
            "vacuous over an empty listing, so this is the failure to fix "
            "first -- it reads git's index, so an unstaged file is invisible.",
        )

    def test_no_comment_block_runs_past_the_bound(self):
        """A comment needing a paragraph is usually in the wrong document."""

        over = [
            f"{path}:{line} -- {length} lines"
            for path in self.paths
            for line, length in comment_blocks(path)
            if length > COMMENT_LINES
        ]

        self.assertEqual(
            over,
            [],
            f"{len(over)} comment block(s) run past {COMMENT_LINES} lines:\n  " + "\n  ".join(over) + "\n\n" + REMEDY,
        )

    def test_no_docstring_carries_more_prose_than_the_bound(self):
        """Args, Returns and Raises are the contract and do not count."""

        over = [
            f"{path}:{line} {owner} -- {length} prose lines"
            for path in self.paths
            for line, length, owner in docstrings(path)
            if length > DOCSTRING_PROSE_LINES
        ]

        self.assertEqual(
            over,
            [],
            f"{len(over)} docstring(s) carry more than {DOCSTRING_PROSE_LINES} "
            "lines of prose:\n  " + "\n  ".join(over) + "\n\n" + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
