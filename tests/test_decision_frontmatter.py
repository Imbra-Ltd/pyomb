"""Every decision record carries well-formed YAML front matter.

The upstream governance record makes front matter the source of truth for a
record's status, its date and its supersession links, and lists the smoke check
that should enforce it: front matter present and well-formed, the id matching
the filename, status and category drawn from closed sets, and the
supersedes / superseded_by pair reciprocally consistent. This module is that
check.

It is worth having for the reason the governance record gives. Before it, a
record's status lived in prose, so a supersession updated one side of a pair
and nothing noticed the other was stale. Two of this project's records
supersede an earlier one, and neither of the earlier ones pointed forward until
the migration wired both directions.

The parser here is deliberate rather than lazy. The schema is six known scalar
and list fields on a fixed set of files, and the project ships no runtime
dependencies at all -- pulling a YAML library into the test extra to read
`status: Accepted` would cost more than it explains. The parser therefore
accepts only what the schema allows and refuses anything else, which is
stricter than a real YAML reader rather than looser.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

DECISIONS = "docs/decisions/"

# The three the governance record fixes. A record is Proposed until it merges,
# Accepted once it does, and Superseded when a later record replaces it.
STATUSES = {"Proposed", "Accepted", "Superseded"}

# This project's closed set, which is not the upstream one. Those categories
# name the template repository's own domains -- manifest shape, layer
# organization, its sync tooling -- and none of them describe a decision about
# a Modbus wire format. Widening this set is a decision that takes its own
# record, which is the discipline the closed set exists to impose.
CATEGORIES = {
    # The wire, the packet API, and the contracts a device sees
    "protocol",
    # Linters, type checkers, security scanners, the dependency lock
    "tooling",
    # Session protocol, documentation conventions, how decisions are recorded
    "process",
    # Versioning, the release record, what ships and how
    "release",
    # Repository identity, naming, history, layout
    "repository",
}

REQUIRED = ("id", "status", "date", "category", "supersedes", "superseded_by")

# What the directory held when this floor was set, less the template this
# module skips, measured with `git ls-files docs/decisions/*.md`. A record is
# append-only -- it merges and is never deleted, since a superseded one stays
# in the tree carrying the link to what replaced it -- so the measured count is
# a floor that only ever rises. It is a floor rather than a non-empty check
# because a listing that comes back holding one record satisfies non-emptiness
# while measuring almost nothing.
RECORDS_AT_LEAST = 22

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SCALAR = re.compile(r'^(\w+):\s*"?([^"]*)"?\s*$')

LIST = re.compile(r"^(\w+):\s*\[(.*)\]\s*$")

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"


def tracked_decisions():
    """Every decision record git tracks, excluding the template.

    Returns:
        list[str] : The tracked record paths, in git's own order
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell and cannot
    # become a second command.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", DECISIONS],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [name for name in listing.split("\0") if name and name.endswith(".md") and not name.endswith("TEMPLATE.md")]


def front_matter(text):
    """Parse the front matter block at the top of one record.

    Args:
        text (str) : The record's full Markdown source

    Returns:
        dict | None : Field name to value, where a list field yields a list of
            strings; None when the document opens with no front matter
    """

    lines = text.split("\n")

    if not lines or lines[0].strip() != "---":
        return None

    fields = {}

    for line in lines[1:]:
        stripped = line.strip()

        if stripped == "---":
            return fields

        listed = LIST.match(stripped)

        if listed:
            body = listed.group(2).strip()
            fields[listed.group(1)] = [item.strip().strip('"') for item in body.split(",")] if body else []
            continue

        scalar = SCALAR.match(stripped)

        if scalar:
            fields[scalar.group(1)] = scalar.group(2).strip()

    # Reaching here means the closing delimiter never arrived, which is a
    # malformed block rather than an absent one. The caller distinguishes the
    # two by the missing fields.
    return fields


class DecisionFrontMatter(unittest.TestCase):
    """Pins the front-matter schema every decision record carries."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tracked-file list to read, and a
        # directory walk would pick up scratch files CI never sees.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.records = tracked_decisions()
        cls.parsed = {name: front_matter((REPO / name).read_text(encoding="utf-8")) for name in cls.records}

    def test_the_enumeration_reached_the_record_directory(self):
        """A pass below means the schema was read, not that nothing was."""

        self.assertGreaterEqual(
            len(self.records),
            RECORDS_AT_LEAST,
            f"the enumeration returned {len(self.records)} record(s) where the "
            f"directory holds at least {RECORDS_AT_LEAST}, so every assertion "
            "below would pass having read almost nothing. A new record that is "
            "written but not staged is invisible here, because the listing "
            "reads git's index rather than the working tree; anything else "
            "means the path this module looks under has moved.",
        )

    def test_every_record_opens_with_a_complete_front_matter_block(self):
        """The block is present and carries all six required fields."""

        offenders = []

        for name, fields in self.parsed.items():
            if fields is None:
                offenders.append(f"{name}: no front matter block")
                continue

            missing = [key for key in REQUIRED if key not in fields]

            if missing:
                offenders.append(f"{name}: missing {', '.join(missing)}")

        self.assertEqual(
            offenders,
            [],
            "decision records whose front matter is absent or incomplete. "
            f"Every record opens with a block carrying {', '.join(REQUIRED)}, "
            "and the two list fields are present even when empty:\n  " + "\n  ".join(offenders),
        )

    def test_every_field_holds_a_value_the_schema_allows(self):
        """id matches the filename, and status, date and category are in range."""

        offenders = []

        for name, fields in self.parsed.items():
            if fields is None:
                continue

            number = pathlib.Path(name).name[:3]

            if fields.get("id") != number:
                offenders.append(f"{name}: id {fields.get('id')!r} is not {number!r}")

            if fields.get("status") not in STATUSES:
                offenders.append(f"{name}: status {fields.get('status')!r} is not one of {sorted(STATUSES)}")

            if not DATE.match(str(fields.get("date", ""))):
                offenders.append(f"{name}: date {fields.get('date')!r} is not YYYY-MM-DD")

            if fields.get("category") not in CATEGORIES:
                offenders.append(f"{name}: category {fields.get('category')!r} is not one of {sorted(CATEGORIES)}")

        self.assertEqual(
            offenders,
            [],
            "decision records carrying a field value outside the schema. A new "
            "category is a decision that takes its own record rather than an "
            "edit here:\n  " + "\n  ".join(offenders),
        )

    def test_supersession_links_agree_in_both_directions(self):
        """Each supersedes entry is answered by a superseded_by entry, and status follows."""

        offenders = []

        by_id = {fields["id"]: (name, fields) for name, fields in self.parsed.items() if fields and "id" in fields}

        for name, fields in self.parsed.items():
            if fields is None:
                continue

            for other in fields.get("supersedes", []):
                if other not in by_id:
                    offenders.append(f"{name}: supersedes {other!r}, which is not a record")
                    continue

                if fields["id"] not in by_id[other][1].get("superseded_by", []):
                    offenders.append(
                        f"{name}: supersedes {other!r}, but {by_id[other][0]} does not "
                        f"list {fields['id']!r} in superseded_by"
                    )

            # The status and the link are two statements of one fact, so a
            # record that says it was replaced must name what replaced it.
            replaced = bool(fields.get("superseded_by"))

            if replaced and fields.get("status") != "Superseded":
                offenders.append(f"{name}: superseded_by is set, so status must be Superseded")

            if fields.get("status") == "Superseded" and not replaced:
                offenders.append(f"{name}: status is Superseded, so superseded_by must name a record")

        self.assertEqual(
            offenders,
            [],
            "supersession links that disagree. A record that replaces another "
            "updates both sides in the same change:\n  " + "\n  ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
