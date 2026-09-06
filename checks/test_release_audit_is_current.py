"""A minor or major release carries an audit run since the release before it.

Four releases were cut without one, and only the fourth skip was written down
anywhere. Nothing about the omission was visible while it happened: the steps
either side of it are gated and pass, so an operator running the sequence top
to bottom feels the procedure checking work it never checked. Enforcement does
not carry across adjacent steps, however the sequence reads.

Two sources are read and neither is git -- the reports from git's index, the
releases from the changelog's dated entries. PLAYBOOK 3.23 carries the
narrowings, what each gives up, and the two ways to clear the gate.
"""

import datetime
import pathlib
import re
import subprocess  # nosec B404
import unittest

from changelog import read_sections

import pyomb

REPO = pathlib.Path(__file__).resolve().parents[1]

CHANGELOG = REPO / "CHANGELOG.md"

AUDITS = "docs/audits/"

# A dated 360 report, or a dated record that the step was declined. The
# character classes are spelled out: a shorthand escape can be lost into a file.
REPORT = re.compile(r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})-360(-skipped)?[.]md$")

# The version the package reports, read as far as the patch component. What
# follows is a pre-release suffix, which says when a release ships not what.
VERSION = re.compile(r"^(?P<major>[0-9]+)[.](?P<minor>[0-9]+)[.](?P<patch>[0-9]+)")

# What the tree held on 2026-09-01. A dated report is immutable once merged, so
# the floor takes the measured count rather than a margin below it.
REPORTS_AT_LEAST = 3

# The releases the changelog recorded on 2026-09-01, and append-only for the
# same reason. Nine and not ten -- the reader drops the `Unreleased` section.
RELEASES_AT_LEAST = 9

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

REMEDY = (
    "Run a 360-degree audit per PLAYBOOK 4.4 and write it to "
    "docs/audits/YYYY-MM-DD-360.md before cutting this release. Skipping it is "
    "a decision an operator is allowed to make, and the way to make it is "
    "docs/audits/YYYY-MM-DD-360-skipped.md naming the release and the reason. "
    "Either one clears this gate. What it refuses is the third option, which "
    "is the one four releases took: passing over the step in silence."
)


def tracked_reports():
    """Every dated 360 report git tracks, as ISO date strings.

    Returns:
        list[str] : The report dates, oldest first
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", AUDITS + "*.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    found = []

    for name in listing.split("\0"):
        if not name:
            continue

        matched = REPORT.match(pathlib.Path(name).name)

        if matched:
            found.append(matched.group("date"))

    return sorted(found)


def previous_release(sections, version):
    """The release entry the one under consideration follows.

    The version the package reports names the release being cut, or the one
    just shipped -- the two are the same entry, and which of them it is does not
    change what precedes it. Between the version bump and the changelog cut no
    entry names it yet, and the newest entry is then the previous release.

    Args:
        sections (list) : The changelog's version sections, in file order
        version (str)   : The version the package reports

    Returns:
        Section | None : The preceding entry, or None when there is none
    """

    for index, section in enumerate(sections):
        if section.version == version:
            following = sections[index + 1 :]

            return following[0] if following else None

    return sections[0] if sections else None


def owes_an_audit(version):
    """Whether a release of this version owes a 360-degree audit.

    Args:
        version (str) : The version the package reports

    Returns:
        bool | None : True for a minor or major release, False for a patch,
            None when the version cannot be read
    """

    matched = VERSION.match(version)

    if matched is None:
        return None

    # A patch release fixes a defect and changes no interface. A minor or major
    # release is where new surface arrives, which is what the audit reviews.
    return matched.group("patch") == "0"


def stale_audit(dates, sections, version):
    """Report an audit that does not cover the release under consideration.

    Args:
        dates (list[str])  : The dated reports, oldest first
        sections (list)    : The changelog's version sections, in file order
        version (str)      : The version the package reports

    Returns:
        list[str] : Empty when no audit is owed, or when the newest report is
            not older than the previous release
    """

    owed = owes_an_audit(version)

    # Not knowing whether an audit is owed is not the same as none being owed,
    # so an unreadable version is a finding rather than a quiet pass.
    if owed is None:
        return [f"{version} is not a version this gate can read, so whether it owes an audit is unknown"]

    if not owed:
        return []

    previous = previous_release(sections, version)

    if previous is None:
        return ["the changelog records no release before " + version]

    if previous.date is None:
        return [f"the {previous.version} entry carries no date to compare against"]

    try:
        shipped = datetime.date.fromisoformat(previous.date)
    except ValueError:
        return [f"the {previous.version} entry is dated {previous.date}, which is not a date"]

    if not dates:
        return [f"no audit is recorded, and {previous.version} shipped on {previous.date}"]

    newest = dates[-1]

    # Not older, rather than strictly newer, so a same-day audit passes.
    # PLAYBOOK 3.23 carries what that trade buys and what it gives up.
    if datetime.date.fromisoformat(newest) >= shipped:
        return []

    return [f"the newest audit is dated {newest}, before {previous.version} shipped on {previous.date}"]


# A tree satisfying the rule: two releases, and a report dated after the older.
# It names a minor -- fixtures naming a patch would retire every break below.
CLEAN_VERSION = "9.10.0"

CLEAN_SECTIONS = read_sections("## [Unreleased]\n\n## [9.10.0] - 2026-01-10\n\n## [9.9.8] - 2026-01-01\n")

CLEAN_DATES = ["2026-01-05"]

# One break per way the rule is reached. The first is the release this gate was
# written for: an audit exists, and it predates the last four releases.
BREAKS = (
    (
        "the audit predates the release before this one",
        ["2025-12-20"],
        CLEAN_SECTIONS,
        CLEAN_VERSION,
    ),
    (
        "no audit has ever been written",
        [],
        CLEAN_SECTIONS,
        CLEAN_VERSION,
    ),
    (
        "the previous entry was cut without a date",
        CLEAN_DATES,
        read_sections("## [9.10.0] - 2026-01-10\n\n## [9.9.8]\n"),
        CLEAN_VERSION,
    ),
    (
        "a major release carries an audit older than the release before it",
        ["2026-01-05"],
        read_sections("## [10.0.0] - 2026-03-01\n\n## [9.10.1] - 2026-02-01\n"),
        "10.0.0",
    ),
)

# An unreadable version on a tree that is otherwise spotless, so the only
# finding available is the version itself and nothing else could raise one.
UNREADABLE_VERSION = "not-a-version"

FRESH_DATES = ["2026-12-31"]

# The case the comparison was loosened to admit. A loosening that nothing pins
# reads as an oversight to the next person tightening the rule back up.
SAME_DAY_DATES = ["2026-01-01"]

# The case the rule was narrowed to admit, pinned for the same reason. This
# tree is stale by the old standard and passes only because a patch owes none.
PATCH_VERSION = "9.10.1"

PATCH_SECTIONS = read_sections("## [Unreleased]\n\n## [9.10.1] - 2026-02-01\n\n## [9.10.0] - 2026-01-10\n")

# A release candidate for a minor owes the audit its final release owes, so the
# parse reads the patch component and ignores what follows it.
PRERELEASE_VERSION = "9.11.0-rc.1"


class ReleaseAuditIsCurrent(unittest.TestCase):
    """Pins a release to an audit run since the release before it."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list to read, and a
        # directory walk would pick up scratch reports CI never sees.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.dates = tracked_reports()
        cls.sections = read_sections(CHANGELOG.read_text(encoding="utf-8"))
        cls.found = stale_audit(cls.dates, cls.sections, pyomb.__version__)

    def test_the_report_listing_reached_the_audits_in_the_tree(self):
        """A pass below means the reports were read, not that none were found."""

        self.assertGreaterEqual(
            len(self.dates),
            REPORTS_AT_LEAST,
            f"the listing found {len(self.dates)} dated report(s) where the "
            f"floor is {REPORTS_AT_LEAST}, so the rule below would report a "
            "current audit having read nothing. A report that is written but "
            "not staged is invisible here, because the listing reads git's "
            "index rather than the working tree. Otherwise the naming "
            "convention moved and the pattern no longer matches it.",
        )

    def test_the_changelog_reached_the_release_entries(self):
        """The rule compares against an entry, so an empty parse says nothing."""

        self.assertGreaterEqual(
            len(self.sections),
            RELEASES_AT_LEAST,
            f"the changelog parse found {len(self.sections)} release entr(ies) "
            f"where the floor is {RELEASES_AT_LEAST}. Either the headings no "
            "longer read `## [X.Y.Z] - DATE`, or entries were removed from a "
            "file nothing removes entries from.",
        )

    def test_the_newest_audit_is_not_older_than_the_release_before_this_one(self):
        """The step four releases skipped, with nothing recording the skip."""

        self.assertEqual(
            self.found,
            [],
            "the audit on record does not cover the changes this release "
            "carries:\n  " + "\n  ".join(self.found) + "\n" + REMEDY,
        )

    def test_the_rule_clears_a_tree_that_satisfies_it(self):
        """A rule that flags a clean tree says nothing about a real one."""

        self.assertEqual(
            stale_audit(CLEAN_DATES, CLEAN_SECTIONS, CLEAN_VERSION),
            [],
            "the rule reported a finding against a tree written to satisfy it, "
            "so what it reports against the real one says nothing about that "
            "tree.",
        )

    def test_a_skip_record_reads_as_the_step_being_addressed(self):
        """An escape nothing exercises is an escape that does not work."""

        for name in ("2026-08-29-360.md", "2026-08-29-360-skipped.md"):
            with self.subTest(name=name):
                matched = REPORT.match(name)

                self.assertIsNotNone(matched, f"{name} reads as no report at all")
                self.assertEqual(matched.group("date"), "2026-08-29")

        for name in ("README.md", "2026-08-29-360-draft.md", "360.md"):
            with self.subTest(name=name):
                self.assertIsNone(REPORT.match(name), f"{name} reads as a report")

    def test_an_audit_dated_the_day_the_previous_release_shipped_clears(self):
        """Two releases on one calendar day were otherwise unreachable."""

        self.assertEqual(
            stale_audit(SAME_DAY_DATES, CLEAN_SECTIONS, CLEAN_VERSION),
            [],
            "an audit dated the day the previous release shipped was refused. "
            "That is the state this comparison was loosened out of: no record "
            "can be dated later than today, so a second release on one day had "
            "no way to clear the gate at all.",
        )

    def test_a_patch_release_owes_no_audit(self):
        """The case the rule was narrowed to admit, on a deliberately stale tree."""

        self.assertEqual(
            stale_audit(CLEAN_DATES, PATCH_SECTIONS, PATCH_VERSION),
            [],
            "a patch release was refused over a stale audit. A patch fixes a "
            "defect and changes no interface, so it owes no audit at all -- "
            "which is the whole of what this narrowing changed. This tree is "
            "stale by the old standard, and that is what makes it the pin.",
        )

    def test_a_release_candidate_owes_what_its_final_release_owes(self):
        """The patch component decides, and a suffix after it does not."""

        self.assertNotEqual(
            stale_audit(["2025-12-20"], CLEAN_SECTIONS, PRERELEASE_VERSION),
            [],
            "a release candidate for a minor was let through with an audit "
            "predating the release before it. The parse reads the patch "
            "component; a pre-release suffix does not make the version "
            "unreadable and does not excuse the audit.",
        )

    def test_an_unreadable_version_fails_rather_than_passing_quietly(self):
        """Not knowing whether an audit is owed is not the same as none being owed."""

        found = stale_audit(FRESH_DATES, CLEAN_SECTIONS, UNREADABLE_VERSION)

        self.assertNotEqual(
            found,
            [],
            "a version the gate cannot read was treated as owing no audit. "
            "Everything else about this tree is clean, so nothing else could "
            "have raised a finding -- which is what makes the silence the "
            "version guard's own.",
        )
        self.assertIn(
            UNREADABLE_VERSION,
            " ".join(found),
            f"the finding does not name {UNREADABLE_VERSION}, so an operator "
            "reading it cannot tell which version could not be read.",
        )

    def test_the_rule_flags_the_break_it_exists_to_catch(self):
        """A rule that has never failed is a rule nothing has tested."""

        for description, dates, sections, version in BREAKS:
            with self.subTest(planted=description):
                self.assertNotEqual(
                    stale_audit(dates, sections, version),
                    [],
                    f"the rule reported nothing against a tree where {description}, so it would pass that release.",
                )


if __name__ == "__main__":
    unittest.main()
