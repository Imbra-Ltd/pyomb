"""The changelog records the release the package reports, and its links agree.

Cutting a release is a procedure of eight steps, and two adjacent ones write
the version into a document. One points the README quick start at the wheel the
new tag will carry; the other cuts the `Unreleased` block into a dated entry
and adds its compare link. The first has been gated since it was written and
cannot be missed. The second was gated by nothing.

So it was missed. `v0.3.0` was tagged and published with no `[0.3.0]` section
and with `[Unreleased]` still comparing against `v0.2.1`; the entry and the
links were written afterwards, which corrects `main` and cannot correct the
sdist inside the tag. Re-tagging a published release to fix an asset is worse
than the gap, so that archive keeps a changelog that does not mention the
release it is part of. That asymmetry is the whole argument for catching this
before the tag rather than after.

Nothing about the omission was visible at the time. Its neighbour passed, every
documented pre-release check ran and reported clean, and a procedure whose
gated steps pass reads as a procedure that was followed. Enforcement does not
carry across adjacent steps, and the step worth gating first is the one whose
omission cannot be corrected afterwards.

`src/pyomb/__init__.py` is the source of truth for the version, as it is for
the README's wheel URL, and every rule here is one-directional: a failure means
the changelog needs the edit, never that the version does.

The rules run over a parsed changelog rather than over its text, so the same
readers that examine the real file examine a planted one. A check that has
never failed is a check nothing has tested, and the last test here is where
each rule is made to fail on the break it exists to catch.
"""

import collections
import pathlib
import re
import unittest

import pyomb

CHANGELOG = pathlib.Path(__file__).resolve().parents[1] / "CHANGELOG.md"

# The label Keep a Changelog reserves for the block that has not shipped. It is
# a section and a link like any version, and it is the one whose link has to
# move on every release.
UNRELEASED = "Unreleased"

# One version section: the version it records and the date beside it. The date
# is optional in the pattern so a half-cut entry parses and is reported, rather
# than failing to match and reading as an entry that is not there at all.
Section = collections.namedtuple("Section", "version date")

# What every rule found, so one code path serves the real changelog and the
# planted ones the negative control feeds it.
Findings = collections.namedtuple(
    "Findings",
    "release_entry unreleased_link unlinked_sections orphan_links mismatched_links",
)

SECTION = re.compile(r"^## \[(?P<label>[^\]]+)\](?:\s*-\s*(?P<date>\S+))?\s*$")

LINK = re.compile(r"^\[(?P<label>[^\]]+)\]:\s*(?P<target>\S+)\s*$")

# The `Unreleased` link compares the tip against the last release, so the tag
# it names is the version the package reports.
COMPARE_HEAD = re.compile(r"/compare/v(?P<base>.+?)\.\.\.HEAD$")

# A version link is a comparison against its predecessor, except the first
# release, which has nothing to compare against and points at its own tag.
# Either way the version it names is its right-hand side.
VERSION_TARGET = re.compile(r"/(?:compare/v.+?\.\.\.v|releases/tag/v)(?P<version>.+)$")

CUT_THE_BLOCK = (
    "Cut the `Unreleased` block into a dated `[X.Y.Z]` entry, the way the "
    "release procedure's step 4 says. Doing it on the release branch is what "
    "puts the entry inside the tagged sdist; doing it afterwards corrects the "
    "branch and leaves the published archive describing the release before "
    "this one."
)

MOVE_THE_LINK = (
    "The compare links live at the foot of the file. `Unreleased` compares the "
    "tip against the newest release, so cutting an entry moves it to the "
    "version just cut."
)


def read_sections(text):
    """Read the version sections a changelog carries, in file order.

    Args:
        text (str) : The changelog's full Markdown source

    Returns:
        list[Section] : One entry per version section, `Unreleased` excluded
    """

    sections = []
    fenced = False

    for line in text.split("\n"):
        # A fence toggles rather than nests, so a heading quoted inside a block
        # is read past. Nothing here fences today; a changelog that starts
        # showing a command should not start reporting the headings in it.
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue

        if fenced:
            continue

        found = SECTION.match(line)

        if found and found.group("label") != UNRELEASED:
            sections.append(Section(found.group("label"), found.group("date")))

    return sections


def read_links(text):
    """Read the link definitions at the foot of a changelog.

    Args:
        text (str) : The changelog's full Markdown source

    Returns:
        dict[str, str] : Each label's target, `Unreleased` included
    """

    links = {}
    fenced = False

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue

        if fenced:
            continue

        found = LINK.match(line)

        if found:
            links[found.group("label")] = found.group("target")

    return links


def incomplete_release_entry(sections, version):
    """Report what a section for the reported version is missing.

    Args:
        sections (list[Section]) : The version sections the changelog carries
        version (str)            : The version the package reports

    Returns:
        list[str] : Empty when a dated section records the version
    """

    found = [section for section in sections if section.version == version]

    if not found:
        recorded = ", ".join(section.version for section in sections)

        return [f"no section records {version}; the file records {recorded or 'nothing'}"]

    return [f"the {version} section carries no date" for section in found if not section.date]


def unreleased_compares_from_elsewhere(links, version):
    """Report an Unreleased link that does not compare from the reported version.

    Args:
        links (dict[str, str]) : The link definitions the changelog carries
        version (str)          : The version the package reports

    Returns:
        list[str] : Empty when the link compares the tip against that version
    """

    target = links.get(UNRELEASED)

    if target is None:
        return [f"{UNRELEASED} carries no link definition"]

    found = COMPARE_HEAD.search(target)

    if found is None:
        return [f"{UNRELEASED} -> {target}, which is not a comparison against the tip"]

    if found.group("base") == version:
        return []

    return [f"{UNRELEASED} compares from v{found.group('base')}, not v{version}"]


def sections_without_a_link(sections, links):
    """Report the version sections nothing at the foot of the file defines.

    Args:
        sections (list[Section]) : The version sections the changelog carries
        links (dict[str, str])   : The link definitions the changelog carries

    Returns:
        list[str] : One version per section whose heading renders unlinked
    """

    return sorted({section.version for section in sections} - set(links))


def links_without_a_section(sections, links):
    """Report the version links that define a label no section uses.

    Args:
        sections (list[Section]) : The version sections the changelog carries
        links (dict[str, str])   : The link definitions the changelog carries

    Returns:
        list[str] : One label per definition left behind
    """

    return sorted(set(links) - {UNRELEASED} - {section.version for section in sections})


def links_naming_another_version(links):
    """Report the version links whose target names a version other than theirs.

    Args:
        links (dict[str, str]) : The link definitions the changelog carries

    Returns:
        list[str] : One 'label -> what it names' entry per mismatch
    """

    found = []

    for label, target in sorted(links.items()):
        if label == UNRELEASED:
            continue

        named = VERSION_TARGET.search(target)

        if named is None:
            found.append(f"{label} -> {target}, which names no version")
        elif named.group("version") != label:
            found.append(f"{label} -> names v{named.group('version')}")

    return found


def findings(text, version):
    """Run every rule over one changelog.

    Args:
        text (str)    : The changelog's full Markdown source
        version (str) : The version the package reports

    Returns:
        Findings : Each rule's findings, in the order the rules are declared
    """

    sections = read_sections(text)
    links = read_links(text)

    return Findings(
        incomplete_release_entry(sections, version),
        unreleased_compares_from_elsewhere(links, version),
        sections_without_a_link(sections, links),
        links_without_a_section(sections, links),
        links_naming_another_version(links),
    )


# A changelog satisfying every rule, in the shape this project's own file uses:
# an unreleased block, two dated entries, and a link apiece -- the older one
# pointing at its own tag, having nothing to compare against.
CLEAN_VERSION = "9.9.9"

CLEAN = """# Changelog

## [Unreleased]

## [9.9.9] - 2026-01-02

### Added

- Something the release carries.

## [9.9.8] - 2026-01-01

### Added

- Something the release before it carried.

[Unreleased]: https://example.invalid/compare/v9.9.9...HEAD
[9.9.9]: https://example.invalid/compare/v9.9.8...v9.9.9
[9.9.8]: https://example.invalid/releases/tag/v9.9.8
"""

# One break per rule, each an edit to the clean file above. The first is the
# release this gate was written for: the version bumped, the block was never
# cut, and every other check passed.
BREAKS = (
    (
        "release_entry",
        "the version bumped and the Unreleased block was never cut",
        CLEAN.replace("## [9.9.9] - 2026-01-02", "## [9.9.7] - 2026-01-02"),
    ),
    (
        "release_entry",
        "the block was cut but the entry carries no date",
        CLEAN.replace("## [9.9.9] - 2026-01-02", "## [9.9.9]"),
    ),
    (
        "unreleased_link",
        "the entry was cut and the Unreleased link left behind",
        CLEAN.replace("compare/v9.9.9...HEAD", "compare/v9.9.8...HEAD"),
    ),
    (
        "unlinked_sections",
        "the entry was cut and no compare link added for it",
        CLEAN.replace("[9.9.9]: https://example.invalid/compare/v9.9.8...v9.9.9\n", ""),
    ),
    (
        "orphan_links",
        "a link survives the section it belonged to",
        CLEAN.replace("## [9.9.8] - 2026-01-01", "## [9.9.6] - 2026-01-01"),
    ),
    (
        "mismatched_links",
        "the new link was copied from its neighbour and not retargeted",
        CLEAN.replace("compare/v9.9.8...v9.9.9", "compare/v9.9.7...v9.9.8"),
    ),
)


class ChangelogReleaseEntry(unittest.TestCase):
    """Pins the changelog to the release the package reports."""

    @classmethod
    def setUpClass(cls):
        cls.text = CHANGELOG.read_text(encoding="utf-8")
        cls.sections = read_sections(cls.text)
        cls.links = read_links(cls.text)
        cls.found = findings(cls.text, pyomb.__version__)

    def test_version_sections_were_read_from_the_file(self):
        """Rules over an empty parse report a clean file in the same words."""

        self.assertNotEqual(
            self.sections,
            [],
            f"no version sections were read from {CHANGELOG.name}. Either the "
            "file carries none, or its headings no longer read `## [X.Y.Z] - "
            "DATE` and every rule below examined nothing.",
        )

    def test_link_definitions_were_read_from_the_file(self):
        """Three of the five rules are silent when no link is found."""

        self.assertNotEqual(
            self.links,
            {},
            f"no link definitions were read from {CHANGELOG.name}. Either the "
            "compare links at the foot of the file are gone, or they no longer "
            "read `[label]: target` and the rules below examined nothing.",
        )

    def test_the_changelog_records_the_version_the_package_reports(self):
        """The gate the release procedure was missing beside its neighbour."""

        self.assertEqual(
            self.found.release_entry,
            [],
            f"the package reports {pyomb.__version__} and the changelog does "
            "not record it:\n  " + "\n  ".join(self.found.release_entry) + "\n" + CUT_THE_BLOCK,
        )

    def test_the_unreleased_link_compares_from_the_reported_version(self):
        """A stale link makes the unreleased range span a shipped release."""

        self.assertEqual(
            self.found.unreleased_link,
            [],
            "the unreleased comparison does not start at the release the "
            "package reports:\n  " + "\n  ".join(self.found.unreleased_link) + "\n" + MOVE_THE_LINK,
        )

    def test_every_version_section_carries_a_link_definition(self):
        """An undefined reference renders as literal brackets, not a link."""

        self.assertEqual(
            self.found.unlinked_sections,
            [],
            "these version sections have no link definition at the foot of the "
            "file, so their headings render as text rather than resolving to a "
            "comparison:\n  " + "\n  ".join(self.found.unlinked_sections) + "\n" + MOVE_THE_LINK,
        )

    def test_no_link_definition_outlives_its_section(self):
        """A definition left behind names a release the file no longer records."""

        self.assertEqual(
            self.found.orphan_links,
            [],
            "these link definitions name a version no section records, so "
            "either a section was renamed or a definition was left "
            "behind:\n  " + "\n  ".join(self.found.orphan_links),
        )

    def test_every_version_link_names_its_own_version(self):
        """A link copied from its neighbour resolves, and to the wrong range."""

        self.assertEqual(
            self.found.mismatched_links,
            [],
            "these link definitions resolve to a version other than the one "
            "they are labelled with, which a reader sees only by following "
            "them:\n  " + "\n  ".join(self.found.mismatched_links),
        )

    def test_every_rule_clears_a_changelog_that_satisfies_it(self):
        """A rule that flags a clean file says nothing about a real one."""

        self.assertEqual(
            findings(CLEAN, CLEAN_VERSION),
            Findings([], [], [], [], []),
            "a rule reported a finding against a changelog written to satisfy "
            "every one of them, so the findings it reports against the real "
            "file say nothing about that file.",
        )

    def test_every_rule_flags_the_break_it_exists_to_catch(self):
        """A rule that has never failed is a rule nothing has tested."""

        for rule, description, planted in BREAKS:
            with self.subTest(rule=rule, planted=description):
                self.assertNotEqual(
                    getattr(findings(planted, CLEAN_VERSION), rule),
                    [],
                    f"the {rule} rule reported nothing against a changelog "
                    f"where {description}, so it would pass that release.",
                )


if __name__ == "__main__":
    unittest.main()
