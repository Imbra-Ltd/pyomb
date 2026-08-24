"""Every sdist include pattern is anchored to the repository root.

A hatchling include pattern with no path separator matches at any depth, not
just at the top of the tree. `LICENSE` selects this project's licence and the
templates submodule's licence alike; `tests` selects both this project's suite
and the submodule's own; `README.md` selects both readmes. `src/pyomb` was the
one entry that never leaked, because a pattern carrying a separator is already
read from the root.

The rule this module pins is the leading slash, and it holds for every pattern
including that one. A rule with an exception for the entries that happen to be
safe by accident asks a reader to work out which kind each entry is; a rule
that reads the same for all four does not.

The result reached PyPI. The source distribution built from the v0.2.0 tag
carries 57 files from `docs/solid-ai-templates`, out of 125 in the archive --
a vendored copy of another project's test suite, republished under this
project's name. Anchoring the four patterns drops the archive to 68 files and
removes the submodule entirely, changing nothing else.

The check reads the patterns rather than building a distribution. A build takes
tens of seconds and needs an isolated environment; the defect is visible in the
configuration, where an unanchored pattern is the whole of it. What the test
cannot see is a pattern that is anchored and still wrong, which is a different
mistake and one a reader of the diff can catch.

`python-lib.md` names this class of defect for the exclude patterns in tool
configuration -- audit them when the tree grows a directory, and anchor them.
Includes were left to the same reasoning and nothing checked them.

Reading the manifest needs a TOML parser, and the standard library grew one in
3.11. This project supports 3.10, where the module skips rather than pull a
backport in for one meta-test. The rule it pins is a property of a file, not of
an interpreter, so the 3.13 leg of the matrix checks it for every leg.
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


if __name__ == "__main__":
    unittest.main()
