"""An action split across sub-actions is bumped by one pull request.

Some actions ship as several sub-actions under one repository -- the CodeQL
action is init and analyze here -- and the halves refuse to run against each
other's version. Dependabot names each half as its own dependency, so an
ungrouped configuration raises one pull request per half. Each moves half the
pair and fails the very analysis it is updating.

That is a deadlock rather than a slow merge. Whichever pull request goes first
is red on its own, a required check cannot be satisfied by a branch that has
not merged, and no ordering exists that fixes it. Two such pull requests sat
open for a day with every other check green before this was written.

The cost is not the two stale pins. Pinning an action to a commit rather than a
tag is a supply-chain control that assumes something keeps the pin current, and
the mechanism meant to keep it current is exactly what cannot complete. So the
pins stop moving silently, and nothing else reports that they have.

The rule is therefore about the configuration and not about one version: where
the workflows reference two or more halves of one action, a single Dependabot
group has to cover all of them, so the halves move together.

Two reading choices. The workflows and the configuration are read as text
rather than parsed, because no manifest here declares a YAML parser -- the only
one in the test extra's closure is a transitive dependency of bandit, and this
module is not worth staking on that. And the corpus is the filesystem rather
than git's index, matching the workflow gate beside it: a workflow directory is
not somewhere scratch files accumulate, so the two enumerations agree.
"""

import pathlib
import re
import unittest
from fnmatch import fnmatchcase

REPO = pathlib.Path(__file__).resolve().parents[1]

WORKFLOWS = REPO / ".github" / "workflows"

CONFIG = REPO / ".github" / "dependabot.yml"

ECOSYSTEM = "github-actions"

# `uses: owner/repo/sub@sha`, capturing everything before the pin. That string
# is what Dependabot names the dependency -- the sub-path included, which is
# why the halves arrive as separate pull requests in the first place. A local
# action reference carries no pin and does not match, which is correct: nothing
# bumps it.
USES = re.compile(r"^\s*-?\s*uses:\s*([^@\s]+)@")

# The entry that opens one ecosystem's update block.
PACKAGE_ECOSYSTEM = re.compile(r"^\s*-\s*package-ecosystem:\s*[\"']?([A-Za-z-]+)")

# A list item, quoted or bare, with any trailing comment dropped.
ITEM = re.compile(r"^-\s*[\"']?([^\"'#\s]+)")

GROUPS_KEY = "groups:"

PATTERNS_KEY = "patterns:"

# One nesting level, which .editorconfig fixes at two spaces for YAML. It is
# what separates a group's name from the fields inside it, so `exclude-patterns`
# is not read as a group that happens to have no includes.
NESTING = 2

# What the workflows held when this floor was set: 18 pinned references across
# the three of them, naming 5 distinct actions. The floor counts references
# rather than actions and sits at a third of them, because steps churn --
# dropping a setup action removes several references and is an ordinary edit,
# which must not fail a control that reports a broken enumeration. Every way
# this enumeration breaks returns nothing at all, so the margin costs no
# detection.
ACTION_REFERENCES_AT_LEAST = 6

NO_WORKFLOWS = "no workflow directory, so there are no action references to read"

NO_CONFIG = "no dependabot configuration, so nothing declares an update group"

REMEDY = (
    "Add a group to the github-actions ecosystem in .github/dependabot.yml "
    "whose patterns cover every half of the action, so one pull request moves "
    "them together:\n"
    "    groups:\n"
    "      <name>:\n"
    "        patterns:\n"
    '          - "owner/action*"\n'
    "One group has to match all the halves. Splitting them across two groups "
    "reproduces the deadlock with the pull requests renamed."
)


def action_references():
    """Collect every pinned action reference the workflows use.

    Each occurrence is kept rather than deduplicated. The rule below reads
    the distinct names, but the floor reads this list: an occurrence count
    falls off sharply when the pattern drifts, where a set of five distinct
    names can lose two and still clear any margin worth stating.

    Returns:
        list[str] : One dependency name per pinned reference, in file order
    """

    found = []

    for path in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
        for line in path.read_text(encoding="utf-8").split("\n"):
            if line.strip().startswith("#"):
                continue

            reference = USES.match(line)

            if reference:
                found.append(reference.group(1))

    return found


def split_actions(references):
    """Group the references by the action publishing them.

    An action referenced under more than one name is split, whether that is
    two sub-actions or a sub-action beside the bare repository. Either way
    Dependabot bumps the names separately.

    Args:
        references (list[str]) : Pinned action references

    Returns:
        dict[str, list[str]] : The names of each split action, by owner/repo
    """

    by_root = {}

    for reference in references:
        parts = reference.split("/")

        if len(parts) < 2:
            continue

        by_root.setdefault("/".join(parts[:2]), set()).add(reference)

    return {root: sorted(names) for root, names in by_root.items() if len(names) > 1}


def ecosystem_block(text, ecosystem):
    """Slice one ecosystem's update entry out of the configuration.

    Args:
        text (str) : The configuration's full source
        ecosystem (str) : The package-ecosystem value to select

    Returns:
        list[str] : The entry's lines, empty when the ecosystem is absent
    """

    block = []
    collecting = False

    for line in text.split("\n"):
        opened = PACKAGE_ECOSYSTEM.match(line)

        if opened:
            collecting = opened.group(1) == ecosystem

        if collecting:
            block.append(line)

    return block


def group_patterns(block):
    """Read the update groups declared inside one ecosystem's entry.

    Args:
        block (list[str]) : The entry's lines

    Returns:
        dict[str, list[str]] : The patterns of each group, by group name
    """

    groups = {}
    group = None
    inside = False
    depth = 0
    listing = False

    for line in block:
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if stripped == GROUPS_KEY:
            inside, depth, group, listing = True, indent, None, False
            continue

        if not inside:
            continue

        # Back out to the entry's own level, so a key following the groups
        # block is not read as another group.
        if indent <= depth:
            inside, group, listing = False, None, False
            continue

        if listing:
            item = ITEM.match(stripped)

            if item:
                groups[group].append(item.group(1))
                continue

            listing = False

        if stripped == PATTERNS_KEY and group is not None:
            listing = True
            continue

        if stripped.endswith(":") and indent == depth + NESTING:
            group = stripped[:-1].strip("\"'")
            groups.setdefault(group, [])

    return groups


def covering_group(groups, names):
    """Name the group whose patterns match every one of the given names.

    Args:
        groups (dict[str, list[str]]) : Patterns by group name
        names (list[str]) : The dependency names that must move together

    Returns:
        str : The covering group's name, or an empty string when none covers
    """

    for group, patterns in groups.items():
        # Dependabot folds case when it matches a pattern; fnmatchcase does
        # not, and fnmatch would fold on Windows only. Lowering both sides
        # keeps this reading the same on either platform.
        if all(any(fnmatchcase(name.lower(), pattern.lower()) for pattern in patterns) for name in names):
            return group

    return ""


class DependabotGroupsSplitActions(unittest.TestCase):
    """Pins every split action to a single Dependabot update group."""

    @classmethod
    def setUpClass(cls):
        if not WORKFLOWS.is_dir():
            raise unittest.SkipTest(NO_WORKFLOWS)

        if not CONFIG.is_file():
            raise unittest.SkipTest(NO_CONFIG)

        cls.references = action_references()
        cls.split = split_actions(cls.references)
        cls.groups = group_patterns(ecosystem_block(CONFIG.read_text(encoding="utf-8"), ECOSYSTEM))

    def test_the_workflows_carry_the_action_references_they_are_known_to(self):
        """A pass below means the rule was applied, not that nothing was read."""

        self.assertGreaterEqual(
            len(self.references),
            ACTION_REFERENCES_AT_LEAST,
            f"the enumeration found {len(self.references)} pinned action "
            f"reference(s) where the floor is {ACTION_REFERENCES_AT_LEAST}, so "
            "the rule below would pass having read almost nothing. Either the "
            "way a workflow pins an action has changed and the pattern no "
            "longer finds it, or enough steps were retired to eat the margin, "
            "in which case re-measure and lower the floor rather than treating "
            "this as a defect.",
        )

    def test_every_split_action_is_covered_by_one_group(self):
        """Halves that must agree on a version move in one pull request."""

        offenders = []

        for root, names in sorted(self.split.items()):
            if not covering_group(self.groups, names):
                offenders.append(f"{root}: {', '.join(names)}")

        self.assertEqual(
            offenders,
            [],
            "these actions are referenced under several names that no single "
            "update group covers, so each half is bumped by its own pull "
            "request and none of them can merge:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
