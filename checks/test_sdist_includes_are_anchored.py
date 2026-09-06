"""Every sdist include pattern is anchored to the repository root.

A hatchling pattern with no path separator matches at any depth, so `LICENSE`,
`tests` and `README.md` each select the templates submodule's file of that name
as well as this project's. The rule is the leading slash and it holds for every
pattern, including the one already safe: a rule with an exception for the
entries that are safe by accident asks a reader which kind each entry is.

The check reads the patterns rather than building a distribution, and skips on
3.10, which has no TOML parser. PLAYBOOK 3.17 carries the archive check that
catches a pattern anchored and still wrong.
"""

import pathlib
import unittest

try:
    import tomllib
except ImportError:  # pragma: no cover - taken only on Python 3.10
    tomllib = None

REPO = pathlib.Path(__file__).resolve().parents[1]

MANIFEST = REPO / "pyproject.toml"

# What roots a pattern at the top of the tree. Hatchling reads a pattern the
# way git reads a `.gitignore` line, so a leading slash is the whole of it.
ANCHOR = "/"

# The directory holding the repository gates. It is absent from the include
# list rather than excluded, which is what keeps this reading sufficient.
GATES = "checks"

REMEDY = (
    "Give the pattern a leading slash so it selects from the repository root "
    "only. A bare name matches every directory of that name at any depth, "
    "including the ones inside a submodule."
)


def sdist_includes():
    """The include patterns the sdist build target declares.

    Returns:
        list[str] : The patterns in the order the manifest lists them, or an
            empty list where the target declares none
    """

    manifest = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))

    target = manifest["tool"]["hatch"]["build"]["targets"]["sdist"]

    return list(target.get("include", []))


@unittest.skipIf(tomllib is None, "the standard library gained a TOML parser in Python 3.11")
class SdistIncludesAreAnchored(unittest.TestCase):
    """Pins the anchoring that keeps the submodule out of the distribution."""

    def test_the_manifest_declares_the_patterns_this_rule_governs(self):
        """The target still carries an include list to check."""

        self.assertNotEqual(
            sdist_includes(),
            [],
            "the sdist target declares no include list, so either the "
            "distribution now ships whatever the tree holds or the target "
            "moved -- this rule is checking nothing until that is resolved",
        )

    def test_no_include_pattern_matches_below_the_repository_root(self):
        """Each pattern selects from the root rather than at any depth."""

        offenders = [pattern for pattern in sdist_includes() if not pattern.startswith(ANCHOR)]

        self.assertEqual(
            offenders,
            [],
            "sdist include patterns that match at any depth, so each also "
            "selects the same name inside the templates submodule:\n  " + "\n  ".join(offenders) + "\n" + REMEDY,
        )

    def test_the_repository_gates_are_not_named_by_the_include_list(self):
        """The gates stop shipping by living outside every included path."""

        offenders = [pattern for pattern in sdist_includes() if pattern.strip(ANCHOR).split(ANCHOR)[0] == GATES]

        self.assertEqual(
            offenders,
            [],
            f"the include list names {GATES}, so the source archive carries "
            "the repository gates again. A consumer running pytest against "
            "that archive then runs this project's Markdown width rule, its "
            "decision-record schema and its changelog rules over their own "
            f"checkout. The gates stop shipping by sitting outside every "
            f"included path, which is what moving them to {GATES}/ bought -- "
            f"restore that rather than adding an exclude, because this module "
            "reads the include list only and an exclude is covered by nothing:"
            "\n  " + "\n  ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
