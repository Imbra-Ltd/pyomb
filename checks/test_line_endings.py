"""No tracked file reaches the index carrying a carriage return.

The rule was documented and unenforced. The playbook carried both commands
that verify it and their pass conditions, and nothing ran either one, so the
check fired only when a person opened the section and typed it.

The second rule reaches what a count of carriage returns cannot. A file git
classifies as binary is not normalised, so its carriage returns enter the index
while the count stays at zero -- the violation and the thing that hides it from
the count are the same event. Which files are legitimately binary is read from
git's own attribute column. PLAYBOOK 3.12 carries the incident and the fix.
"""

import collections
import pathlib
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# One index entry, with git's `i/` and `attr/` markers already stripped. The
# attributes are a tuple because a path may carry several.
Entry = collections.namedtuple("Entry", "path index attributes")

# The index values that put a carriage return in a commit. `mixed` is a file
# carrying both endings, which a plain count of `crlf` misses.
CARRIAGE_RETURN = frozenset({"crlf", "mixed"})

# What git reports for a blob it treats as binary, in both columns. Wearing it
# in the index alone is the case that hides a violation.
NOT_TEXT = "-text"

NOT_A_CHECKOUT = "not a git checkout, so there is no index to read line endings from"

# What the index held when this floor was set: 136 paths. The tree churns, so
# the floor takes a margin below it; a broken enumeration returns nothing.
TRACKED_AT_LEAST = 64

RENORMALISE = (
    "A carriage return reached the index before the normalisation covered the "
    "file. `git add --renormalize .` rewrites the index, and the diff it "
    "produces is the fix."
)

DECLARE_OR_CLEAN = (
    "Either the file is genuinely binary, in which case it wants its own entry "
    "in `.gitattributes` beside the specifications, or it is text carrying a "
    "byte that should not be there -- one NUL is enough -- in which case "
    "`checks/test_source_is_ascii.py` names the character and its line. Until "
    "one of the two happens, git stores the file without normalising it and "
    "any carriage return in it is invisible to the rule above."
)


def eol_records():
    """Read git's per-file line-ending report for every tracked path.

    Returns:
        list[str] : One record per index entry, in git's own order
    """

    # The argument vector is a fixed list and carries no caller input, so it
    # reaches the operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "--eol", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [record for record in listing.split("\0") if record]


def tracked_paths():
    """Every path git tracks, read independently of the line-ending report.

    Returns:
        set[str] : The tracked paths
    """

    # Same argument as above: a fixed list, no caller input, no shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return {name for name in listing.split("\0") if name}


def unreadable(records):
    """Locate the records that do not carry the three fields this rule reads.

    Args:
        records (list[str]) : The records git printed

    Returns:
        list[str] : One quoted record per unparseable entry
    """

    found = []

    for record in records:
        info, tab, path = record.partition("\t")

        if not tab or not path or not info.startswith("i/") or "attr/" not in info:
            found.append(repr(record))

    return found


def read(records):
    """Split each line-ending record into path, index value and attributes.

    Args:
        records (list[str]) : The records git printed

    Returns:
        list[Entry] : One entry per record, markers stripped
    """

    entries = []

    for record in records:
        # The path follows the first tab, so the split is on the tab rather
        # than on whitespace: `-z` does not quote a path that holds spaces.
        info, _, path = record.partition("\t")

        fields = info.split()
        index = fields[0].partition("i/")[2] if fields else ""

        # Several attributes may apply to one path, separated by spaces, so the
        # value is everything after the marker rather than the next token.
        attributes = tuple(info.partition("attr/")[2].split())

        entries.append(Entry(path, index, attributes))

    return entries


def committed_with_a_carriage_return(entries):
    """Locate the tracked files the index stores with a carriage return.

    Args:
        entries (list[Entry]) : The parsed index entries

    Returns:
        list[str] : One 'path (value)' entry per offending file
    """

    return [f"{entry.path} ({entry.index})" for entry in entries if entry.index in CARRIAGE_RETURN]


def stored_as_binary_undeclared(entries):
    """Locate the files git treats as binary that nothing declared binary.

    Args:
        entries (list[Entry]) : The parsed index entries

    Returns:
        list[str] : One path per offending file
    """

    return [entry.path for entry in entries if entry.index == NOT_TEXT and NOT_TEXT not in entry.attributes]


# A record of each kind this module exists to catch, in git's own output shape:
# what a count of `crlf` reports, what it misses, and the reclassification.
PLANTED = (
    "i/crlf  w/crlf  attr/text=auto        \tdocs/planted-crlf.md",
    "i/mixed w/crlf  attr/text=auto        \tdocs/planted-mixed.md",
    "i/-text w/-text attr/text=auto        \tdocs/planted-detected-binary.md",
)

# The three shapes a clean tree carries. A control that only plants violations
# tests half the rule -- a check flagging everything flags each plant too.
CLEAN = (
    "i/lf    w/crlf  attr/text=auto        \tREADME.md",
    "i/-text w/-text attr/-text            \tdocs/specs/PI_MBUS_300.pdf",
    "i/      w/      attr/text=auto        \tdocs/solid-ai-templates",
)


class LineEndings(unittest.TestCase):
    """Pins the index to LF, including the files git stops normalising."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no index to read. The skip is for that
        # case only; a checkout whose git call fails is a failure.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.records = eol_records()
        cls.entries = read(cls.records)
        cls.tracked = tracked_paths()

    def test_the_reader_split_every_record_git_printed(self):
        """A record this module cannot parse reads as a file with no findings."""

        broken = unreadable(self.records)

        self.assertEqual(
            broken,
            [],
            "records were returned that do not carry the three fields this "
            "module reads:\n  " + "\n  ".join(broken) + "\nThe output shape of "
            "`git ls-files --eol -z` has moved. Fix the reader -- a record it "
            "drops is a file neither rule below ever examines.",
        )

    def test_the_index_listing_reached_the_tracked_files(self):
        """A short listing satisfies both rules below without reading much."""

        self.assertGreaterEqual(
            len(self.tracked),
            TRACKED_AT_LEAST,
            f"git reported {len(self.tracked)} tracked path(s) where the index "
            f"holds at least {TRACKED_AT_LEAST}, so both rules below would "
            "pass having examined almost nothing. A file that is written but "
            "not staged is invisible here, because the listing reads git's "
            "index rather than the working tree; anything else means the "
            "working directory is not the repository.",
        )

    def test_a_record_was_read_for_every_tracked_path(self):
        """The rules are only as strong as the set of files they reached."""

        parsed = {entry.path for entry in self.entries}

        missing = sorted(self.tracked - parsed)
        extra = sorted(parsed - self.tracked)

        self.assertEqual(
            (missing, extra),
            ([], []),
            "the line-ending report and the tracked-file list disagree, so the "
            "rules below examined a different set of files than the index "
            "holds.\n  tracked but unexamined: "
            + ", ".join(missing)
            + "\n  examined but untracked: "
            + ", ".join(extra),
        )

    def test_no_tracked_file_carries_a_carriage_return_in_the_index(self):
        """Whatever a working tree does, a commit stores LF."""

        offenders = committed_with_a_carriage_return(self.entries)

        self.assertEqual(
            offenders,
            [],
            "tracked files are stored in the index with a carriage return:\n  "
            + "\n  ".join(offenders)
            + "\n"
            + RENORMALISE,
        )

    def test_no_file_the_project_declares_text_is_stored_as_binary(self):
        """The classification that skips normalising is also what hides it."""

        offenders = stored_as_binary_undeclared(self.entries)

        self.assertEqual(
            offenders,
            [],
            "git stores these as binary while `.gitattributes` declares them "
            "text, so normalisation skips them and the rule above cannot see "
            "them:\n  " + "\n  ".join(offenders) + "\n" + DECLARE_OR_CLEAN,
        )

    def test_both_rules_flag_a_planted_violation_and_clear_a_clean_one(self):
        """A rule that has never failed is a rule nothing has tested."""

        planted = read(PLANTED)
        clean = read(CLEAN)

        self.assertEqual(
            committed_with_a_carriage_return(planted),
            ["docs/planted-crlf.md (crlf)", "docs/planted-mixed.md (mixed)"],
            "the carriage-return rule no longer flags the two index values "
            "that carry one, so it would pass a tree that commits them.",
        )

        self.assertEqual(
            stored_as_binary_undeclared(planted),
            ["docs/planted-detected-binary.md"],
            "the detected-binary rule no longer flags a file git treats as "
            "binary while the project declares it text, which is the shape "
            "that hides a carriage return from the rule above.",
        )

        self.assertEqual(
            (committed_with_a_carriage_return(clean), stored_as_binary_undeclared(clean)),
            ([], []),
            "a rule flagged a record from a clean tree, so the findings it "
            "reports elsewhere say nothing about the tree it read.",
        )


if __name__ == "__main__":
    unittest.main()
