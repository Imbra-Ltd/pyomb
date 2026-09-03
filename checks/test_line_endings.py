"""No tracked file reaches the index carrying a carriage return.

`.gitattributes` normalises every text file to LF in the index, so whatever
`core.autocrlf` does in a working tree never reaches a commit, and
`.editorconfig` is the editor-side half for editors that read it. Development
here is Windows and CI is Linux, which is the split the pair exists for.

The rule was documented and unenforced. The playbook carried both commands
that verify it and their pass conditions, and nothing ran either one, so the
check fired only when a person opened the section and typed it. Its sibling
governs which characters may appear in a line and has run as
`checks/test_source_is_ascii.py` on every pull request since it was written. The
two rules are the same shape, and a violating tree looks identical to a clean
one until someone looks.

The second rule here is the one the documented count cannot express. A file
git classifies as binary reports `-text` rather than a line-ending value, and
`text=auto` skips normalising it, so its carriage returns go into the index
unconverted while the count stays at zero. One NUL byte anywhere in a file is
enough to trigger that classification, which is how this project's journal came
to be stored with 1127 CRLF endings while the check reported clean. The
violation and the thing that hides it from the count are the same event.

Which files are legitimately binary is read from git's own attribute column
rather than named here. The specifications are declared binary in
`.gitattributes` and report `-text` in both columns; a file that reports it in
the index alone was detected as binary while the project declared it text,
which is exactly the incident shape. Reading the declaration means adding a
binary file is one line in `.gitattributes` rather than an edit to this module,
and means a file that acquires a stray byte cannot excuse itself by its name.

The guard reads the tree as git tracks it, so a local scratch file cannot fail
a run that CI would pass, and it checks that it read something before it
reports that it found nothing: a listing this module could not parse would
report a clean tree in exactly the same words as a clean tree.
"""

import collections
import pathlib
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# One index entry, with git's `i/` and `attr/` markers already stripped. The
# attributes are a tuple because a path may carry several.
Entry = collections.namedtuple("Entry", "path index attributes")

# The index line-ending values that put a carriage return in a commit. `crlf`
# is a file stored with CRLF throughout, which a plain count of that value
# reports; `mixed` is one carrying both endings, which the same count misses
# while it commits the same bytes. The remaining values -- `lf`, `none`, and
# the empty one a submodule gitlink reports -- carry no carriage return.
CARRIAGE_RETURN = frozenset({"crlf", "mixed"})

# What git reports for a blob it treats as binary, in the index column and the
# attribute column alike. A path wearing it in both was declared binary; one
# wearing it in the index alone was detected as binary while the project
# declared it text, and that is the case that hides a violation.
NOT_TEXT = "-text"

NOT_A_CHECKOUT = "not a git checkout, so there is no index to read line endings from"

# What the index held when this floor was set: 136 paths. The floor sits at
# roughly half, because the tree churns -- a retired module or workflow is an
# ordinary deletion and must not fail a line-ending rule. Every way this
# enumeration breaks returns nothing at all, so the margin costs no detection.
# It is a floor rather than the non-empty check it replaces because a listing
# that comes back holding one path satisfies non-emptiness while measuring
# almost nothing.
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

    # The two suppressed checks rest on the argument vector being a list, which
    # hands the arguments to the operating system directly rather than to a
    # shell, so nothing here can break out and become a second command. It is
    # also fixed, with no caller input in it. The checks match on call shape
    # and cannot see either.
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
        # The three fields are padded to fixed columns and the path follows the
        # first tab, so the split is on the tab rather than on whitespace. `-z`
        # does not quote a path, and a path may contain spaces.
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


# A record of each kind this module exists to catch, in git's own output shape.
# The first is what a plain count of `crlf` reports, the second is what such a
# count misses, and the third is the reclassification that hid 1127 carriage
# returns from it.
PLANTED = (
    "i/crlf  w/crlf  attr/text=auto        \tdocs/planted-crlf.md",
    "i/mixed w/crlf  attr/text=auto        \tdocs/planted-mixed.md",
    "i/-text w/-text attr/text=auto        \tdocs/planted-detected-binary.md",
)

# The three shapes a clean tree carries: a normalised text file, a file
# declared binary in `.gitattributes`, and a submodule gitlink, which reports
# no line endings at all. A control that only plants violations tests half the
# rule -- a check that flags everything flags each planted record too.
CLEAN = (
    "i/lf    w/crlf  attr/text=auto        \tREADME.md",
    "i/-text w/-text attr/-text            \tdocs/specs/PI_MBUS_300.pdf",
    "i/      w/      attr/text=auto        \tdocs/solid-ai-templates",
)


class LineEndings(unittest.TestCase):
    """Pins the index to LF, including the files git stops normalising."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no index to read, and no other source
        # answers the same question. The skip is for that case only; a checkout
        # whose git call fails is a failure, not a skip.
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
