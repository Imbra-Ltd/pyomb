"""A release carries an audit run since the release before it.

The release procedure's step 2 says to run a 360-degree audit and not to ship
with critical findings open. Four releases were cut without one -- v0.2.0,
v0.2.1, v0.3.0 and v0.3.1 -- and only the fourth skip was written down
anywhere. The first three left no trace at all, which is what makes this worth
a gate rather than a reminder.

Nothing about the omission was visible while it happened. The steps either side
of step 2 are gated and pass: one fails until the changelog entry is cut, the
next until the README names the new wheel. An operator running the sequence top
to bottom feels the procedure checking the work, and the ungated step in the
middle is simply not done. Enforcement does not carry across adjacent steps,
however the sequence reads.

The rule is that the newest audit is not older than the release before the one
being cut. An audit run before that release shipped says nothing about the
changes since, so it fails; an audit dated the same day passes.

Same-day was refused until 2026-08-31 and is now accepted, which is a decision
about cost rather than a sharpening of the rule. Dates carry no time, so an
audit written the morning before a release and one written the evening after it
are the same string, and refusing both was the safe reading. What that reading
also did was make two releases on one calendar day impossible: the second is
compared against the first, no record can be dated later than today, and the
release is blocked with no honest way to clear it. The audit step is declinable
by design, so a rule that cannot be satisfied at all is a worse failure than a
same-day audit that covers less than it appears to.

What the rule still catches is unchanged and is what it was written for: an
audit predating the previous release, and no audit at all. Four releases were
cut with neither, and none of them would pass this gate in either form.

Skipping the audit stays available, because it is a judgement call and
sometimes the right one. What is no longer available is skipping it in silence:
a dated `-skipped` record naming the release and the reason clears this gate,
and it lands in the release pull request where a reviewer reads it. The four
releases that skipped the step wrote nothing, and three of them left no trace
anywhere.

Two things are read rather than one, and neither is git. The reports are
enumerated from git's index like every other document gate here, and the
releases are read from the changelog's dated entries. Tags would be the obvious
source and are not available: CI checks out shallow and fetches none, so a
tag-based rule would find nothing and report a clean tree from it.

The gate is unconditional. It does not detect a release branch and does not
need to -- its comparison only tightens when a new dated entry appears, which
is step 4 of the same procedure, so it is silent between releases and fails on
the branch that is cutting one.
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

# A dated 360 report, or a dated record that the step was deliberately skipped.
# Both satisfy the rule, because what it exists to catch is a step passed over
# in silence rather than a step declined. A skip record is one paragraph naming
# the release and the reason, and it arrives in the release pull request where
# a reviewer reads it; omitting the step arrived as nothing at all.
#
# The character classes are spelled out rather than written as a shorthand
# escape, which can be lost on the way into a file while still compiling.
REPORT = re.compile(r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})-360(-skipped)?[.]md$")

# What the tree held when this floor was set: the 2026-08-18 report and the
# 2026-08-29 one added beside this gate. A dated report is immutable once
# merged, so this corpus only ever grows and the floor takes the measured count
# rather than a margin below it. A listing that comes back short means the
# enumeration broke, not that a report was retired.
REPORTS_AT_LEAST = 2

# The six releases the changelog recorded when this floor was set, 0.1.0 through
# 0.4.0. Append-only for the same reason, and sized the same way.
RELEASES_AT_LEAST = 6

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
    # the operating system directly rather than through a shell and cannot
    # become a second command. The checks match on call shape and cannot see
    # that.
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


def stale_audit(dates, sections, version):
    """Report an audit that does not cover the release under consideration.

    Args:
        dates (list[str])  : The dated reports, oldest first
        sections (list)    : The changelog's version sections, in file order
        version (str)      : The version the package reports

    Returns:
        list[str] : Empty when the newest report is not older than the previous
            release
    """

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

    # Not older, rather than strictly newer. A same-day audit passes; see the
    # module docstring for what that trade buys and what it gives up.
    if datetime.date.fromisoformat(newest) >= shipped:
        return []

    return [f"the newest audit is dated {newest}, before {previous.version} shipped on {previous.date}"]


# A tree satisfying the rule: two releases, and a report dated after the older
# of them. The version under consideration is the newer entry, so the report has
# to postdate the older one.
CLEAN_VERSION = "9.9.9"

CLEAN_SECTIONS = read_sections("## [Unreleased]\n\n## [9.9.9] - 2026-01-10\n\n## [9.9.8] - 2026-01-01\n")

CLEAN_DATES = ["2026-01-05"]

# One break per way the rule is reached. The first is the release this gate was
# written for: an audit exists, it predates the last four releases, and every
# other documented check passed.
BREAKS = (
    (
        "the audit predates the release before this one",
        ["2025-12-20"],
        CLEAN_SECTIONS,
    ),
    (
        "no audit has ever been written",
        [],
        CLEAN_SECTIONS,
    ),
    (
        "the previous entry was cut without a date",
        CLEAN_DATES,
        read_sections("## [9.9.9] - 2026-01-10\n\n## [9.9.8]\n"),
    ),
)

# The case the comparison was loosened to admit, asserted rather than left to
# follow from the absence of a break above. A loosening that nothing pins reads
# as an oversight to the next person tightening the rule back up.
SAME_DAY_DATES = ["2026-01-01"]


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

    def test_the_rule_flags_the_break_it_exists_to_catch(self):
        """A rule that has never failed is a rule nothing has tested."""

        for description, dates, sections in BREAKS:
            with self.subTest(planted=description):
                self.assertNotEqual(
                    stale_audit(dates, sections, CLEAN_VERSION),
                    [],
                    f"the rule reported nothing against a tree where {description}, so it would pass that release.",
                )


if __name__ == "__main__":
    unittest.main()
