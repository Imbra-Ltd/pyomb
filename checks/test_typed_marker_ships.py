"""The package ships the marker that makes its annotations visible.

PEP 561 says an installed package advertises inline annotations with a
`py.typed` file inside the package directory. A checker that does not find one
treats every name imported from the package as `Any`, however thoroughly the
package is annotated.

The failure is silent from both sides: a consumer's strict run goes green over
an unchecked boundary, and mypy here reads `src/` directly, where no marker is
needed. The check reads the tree rather than building a distribution.
"""

import pathlib
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Where the package lives, and the marker PEP 561 asks for inside it.
PACKAGE = REPO / "src" / "pyomb"

MARKER = PACKAGE / "py.typed"

# Hatchling carries every file under a declared package, so the marker needs
# no include of its own -- only this entry still naming its directory.
PACKAGED = "src/pyomb"

REMEDY = (
    "Create an empty src/pyomb/py.typed and commit it. Without it a consumer "
    "type-checking against this package sees Any for every name, and their "
    "own strict run passes while the boundary goes unchecked."
)


def tracked_under(directory):
    """The paths git's index holds under a directory.

    Args:
        directory (pathlib.Path) : The directory to list, inside the repository

    Returns:
        set[str] : Repository-relative POSIX paths, empty where git lists none
    """

    # The argument vector is a list and carries no caller input, so it reaches
    # the operating system directly rather than through a shell.
    listing = subprocess.run(  # nosec B603 B607
        ["git", "ls-files", directory.relative_to(REPO).as_posix()],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO,
        check=False,
    )

    return {line for line in listing.stdout.splitlines() if line}


class TypedMarkerShips(unittest.TestCase):
    """Pins the marker that carries this package's annotations to consumers."""

    def test_the_listing_reaches_the_package(self):
        """The index lists the package, so the assertions below read something."""

        listed = tracked_under(PACKAGE)

        self.assertNotEqual(
            listed,
            set(),
            f"git lists no file under {PACKAGE.relative_to(REPO).as_posix()}, so "
            "the assertion below would pass against an unread tree rather than "
            "against a packaged marker",
        )

    def test_the_marker_exists(self):
        """PEP 561's marker sits inside the package directory."""

        self.assertTrue(MARKER.is_file(), REMEDY)

    def test_the_marker_is_tracked(self):
        """The marker is in the index, since an untracked file reaches no build."""

        listed = tracked_under(PACKAGE)

        self.assertIn(
            MARKER.relative_to(REPO).as_posix(),
            listed,
            "the marker exists on disk and git does not carry it, so it is "
            "absent from every clone and every distribution built from one. "
            "git add it.",
        )

    def test_the_wheel_target_still_packages_the_directory_holding_it(self):
        """The wheel declares the package, which is what carries the marker."""

        manifest = (REPO / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn(
            f'"{PACKAGED}"',
            manifest,
            f"the wheel target no longer names {PACKAGED}, so whatever it "
            "packages now, the marker is not travelling with it by the route "
            "this check assumes",
        )
