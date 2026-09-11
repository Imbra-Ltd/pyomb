"""The Dependabot ecosystem enrolled for the lock is one that reads the lock.

`uv.lock` is what CI installs from, and Dependabot is enrolled to refresh it.
An ecosystem that never opens the file satisfies that enrolment by appearance:
the job runs on schedule, the configuration reads as intended, and the lock
ages with no signal. The pip updater names `Pipfile.lock`, `poetry.lock` and
`pdm.lock` and nothing else, so three weekly runs refreshed nothing before the
absence of a lock-touching pull request was counted. PLAYBOOK 4.6 carries the
arrangement this pins.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Read as text rather than parsed, matching the grouping gate beside it: no
# manifest here declares a YAML parser.
CONFIG = REPO / ".github" / "dependabot.yml"

# The entry that opens one ecosystem's update block.
PACKAGE_ECOSYSTEM = re.compile(r"^\s*-\s*package-ecosystem:\s*[\"']?([A-Za-z-]+)")

# Which ecosystem reads which Python lock file. The pip updater's file fetcher
# names the last three; uv.lock belongs to the uv ecosystem alone.
LOCK_READERS = {
    "uv.lock": "uv",
    "Pipfile.lock": "pip",
    "poetry.lock": "pip",
    "pdm.lock": "pip",
}

# What the configuration held when this floor was set: 2 enrolled ecosystems.
# Entries churn, so the floor takes a margin below that.
ECOSYSTEMS_AT_LEAST = 1

NOT_A_CHECKOUT = "not a git checkout, so there is no tracked-file list to read"

NO_CONFIG = "no dependabot configuration, so nothing enrols an ecosystem"

REMEDY = (
    "Enrol the ecosystem that reads the committed lock in "
    ".github/dependabot.yml, and retire one that reads no lock this tree "
    "carries. An enrolment that never opens the file is a refresh that never "
    "runs, and nothing reports it: the job is green on schedule."
)


def committed_locks():
    """The lock files git tracks at the repository root, by name.

    Returns:
        list[str] : The tracked names among those this rule knows
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", "-z", *LOCK_READERS],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    return [name for name in listing.split("\0") if name]


def enrolled_ecosystems(text):
    """The package-ecosystem values the configuration enrols, in file order.

    Args:
        text (str) : The configuration's full source

    Returns:
        list[str] : One entry per update block
    """

    found = []

    for line in text.split("\n"):
        opened = PACKAGE_ECOSYSTEM.match(line)

        if opened:
            found.append(opened.group(1))

    return found


class DependabotReadsTheCommittedLock(unittest.TestCase):
    """Pins the lock's enrolment to an ecosystem that opens the lock."""

    @classmethod
    def setUpClass(cls):
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        if not CONFIG.is_file():
            raise unittest.SkipTest(NO_CONFIG)

        cls.locks = committed_locks()
        cls.ecosystems = enrolled_ecosystems(CONFIG.read_text(encoding="utf-8"))

    def test_the_tree_commits_a_lock_this_rule_reads(self):
        """A pass below means the pairing was checked, not that no lock exists."""

        self.assertNotEqual(
            self.locks,
            [],
            "the listing found none of " + ", ".join(LOCK_READERS) + " tracked, "
            "so the rule below would pass having paired nothing. Either the "
            "lock was renamed or moved and the table no longer names it, or "
            "the toolchain is no longer locked, which is a decision this "
            "module cannot make for the project -- re-point the table rather "
            "than reading this as a clean tree.",
        )

    def test_the_configuration_enrols_the_ecosystems_it_is_known_to(self):
        """A pass below means the entries were read, not that none were found."""

        self.assertGreaterEqual(
            len(self.ecosystems),
            ECOSYSTEMS_AT_LEAST,
            f"the configuration yielded {len(self.ecosystems)} enrolled "
            f"ecosystem(s) where the floor is {ECOSYSTEMS_AT_LEAST}, so the "
            "rule below would pass having read almost nothing. Either the way "
            "an entry is written has changed and the pattern no longer finds "
            "it, or the enrolments were retired, in which case re-measure and "
            "lower the floor rather than treating this as a defect.",
        )

    def test_every_committed_lock_is_read_by_an_enrolled_ecosystem(self):
        """The lock the project commits is one Dependabot opens."""

        offenders = []

        for lock in self.locks:
            reader = LOCK_READERS[lock]

            if reader not in self.ecosystems:
                offenders.append(f"{lock}: read by {reader}, which is not enrolled")

        self.assertEqual(
            offenders,
            [],
            "these committed locks are read by no enrolled ecosystem, so "
            "nothing Dependabot runs ever refreshes them:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )

    def test_every_enrolled_lock_ecosystem_reads_a_committed_lock(self):
        """No Python enrolment stands in for a refresh it cannot perform."""

        read = {LOCK_READERS[lock] for lock in self.locks}
        offenders = []

        for ecosystem in self.ecosystems:
            if ecosystem in LOCK_READERS.values() and ecosystem not in read:
                offenders.append(f"{ecosystem}: reads none of the committed locks")

        self.assertEqual(
            offenders,
            [],
            "these enrolled ecosystems open no lock this tree commits, so the "
            "enrolment reads as a refresh while refreshing nothing:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
