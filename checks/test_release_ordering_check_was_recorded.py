"""A release's tag carries proof the ordering check ran before it was pushed.

PLAYBOOK 5 step 7 asks an operator to run the release-ordering check -- which
pull requests are ready to land in the gap between tags -- before pushing the
new tag. Nothing recorded whether that happened; a release proceeding without
it looked identical to one that ran it and found nothing to do. The tag's own
annotation is the record: step 8 folds the check's output into `git tag -a`'s
message, so it ships with every archive the tag produces and needs no new
commit on `main`, which `git.md` would refuse.

This gate has nothing to check between releases -- the tag for the version
`pyomb` currently reports does not exist until an operator cuts it -- so it is
silent until then, the same as PLAYBOOK 3.23's audit gate.
"""

import pathlib
import subprocess  # nosec B404
import unittest

import pyomb

REPO = pathlib.Path(__file__).resolve().parents[1]

TAG = f"v{pyomb.__version__}"

# v0.7.0 was tagged before this gate existed, so its tag carries no record.
# Retagging it to add one is refused by git.md and by PLAYBOOK 5's own
# argument against repairing a published tag; grandfathered instead.
GRANDFATHERED = frozenset({"0.7.0"})

# Printed by the ordering check (PLAYBOOK 5, step 7) whenever it applies --
# not when it reports "does not apply" for a tag already at HEAD.
MARKERS = ("preceding tag:", "commits carried:")

NOT_A_CHECKOUT = "not a git checkout, so there is no tag to read"

REMEDY = (
    "Fold the release-ordering check's output into the tag's annotation: "
    'PLAYBOOK 5 step 8 reads `git tag -a vX.Y.Z -m "$output"` where $output '
    "is what step 7 printed. A lightweight tag carries no message either, "
    "which git.md already refuses for a different reason."
)


def missing_markers(annotation):
    """Report which markers the ordering check's output did not leave behind.

    Args:
        annotation (str) : A tag's annotation body, empty for a lightweight
            tag or one that carries none

    Returns:
        list[str] : Empty when every marker is present
    """

    return [marker for marker in MARKERS if marker not in annotation]


def tag_annotation(repo, tag):
    """Read one tag's annotation body, or None where the tag does not exist.

    Args:
        repo (Path) : The repository to read the tag from
        tag (str)   : The tag name, including its leading `v`

    Returns:
        str | None : The annotation body -- empty for a lightweight tag -- or
            None where no tag by that name exists at all
    """

    # The argument vector is a list built from a version this process already
    # imported, so nothing here reaches a shell.
    exists = subprocess.run(  # nosec B603 B607
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    if exists.returncode != 0:
        return None

    # %(contents) reads empty for a lightweight tag and the message body for
    # an annotated one; the ref check above already proved the tag exists.
    read = subprocess.run(  # nosec B603 B607
        ["git", "for-each-ref", "--format=%(contents)", f"refs/tags/{tag}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )

    return read.stdout


# A tag body satisfying the rule, in the shape the ordering check prints.
CLEAN_ANNOTATION = "preceding tag: v1.2.2\n  carries: fix: something\ncommits carried: 1\n"

# One break per way the record can be missing.
BREAKS = (
    ("a lightweight tag, which carries no message at all", ""),
    ("an annotated tag whose message is unrelated", "Release v1.2.3\n"),
    ("the check's own output truncated before the commit count", "preceding tag: v1.2.2\n"),
)


class TheTagRecordsThatTheOrderingCheckRan(unittest.TestCase):
    """Pins the tag for the version `pyomb` currently reports."""

    @classmethod
    def setUpClass(cls):
        # Absent a checkout there is no tag ref to read.
        if not (REPO / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        cls.annotation = tag_annotation(REPO, TAG)

    def test_the_rule_clears_a_tag_that_satisfies_it(self):
        """A rule that flags a clean tag says nothing about a real one."""

        self.assertEqual(
            missing_markers(CLEAN_ANNOTATION),
            [],
            "the rule reported a finding against a tag body written to "
            "satisfy it, so what it reports against a real tag says nothing "
            "about that tag.",
        )

    def test_the_rule_flags_the_break_it_exists_to_catch(self):
        """A rule that has never failed is a rule nothing has tested."""

        for description, annotation in BREAKS:
            with self.subTest(planted=description):
                self.assertNotEqual(
                    missing_markers(annotation),
                    [],
                    f"the rule reported nothing against a tag where {description}, so it would pass that release.",
                )

    def test_the_current_release_tag_carries_the_record(self):
        """The gate PLAYBOOK 5 step 7 was missing: nothing proved it ran."""

        if pyomb.__version__ in GRANDFATHERED:
            self.skipTest(f"{TAG} predates this gate and is grandfathered")

        if self.annotation is None:
            self.skipTest(f"{TAG} does not exist yet; this applies once a release is tagged")

        found = missing_markers(self.annotation)

        self.assertEqual(
            found,
            [],
            f"{TAG}'s annotation does not carry the ordering check's output "
            "(missing: " + ", ".join(found) + "):\n" + REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
