"""The README's install command names the version the package reports.

The quick start offers a release wheel by URL, so the version is written down
twice: once in `src/pyomb/__init__.py`, which hatchling reads and which every
other consumer of the version derives from, and once in the tag path and the
wheel filename of that URL. A release that bumps one and not the other leaves
the quick start pointing at an earlier release's asset, and nothing else
notices -- to ruff, mypy, bandit and the rest of the suite that URL is prose.

The guard is one-directional. `__init__.py` is the source of truth and the
README carries the derived copy, so a failure here means the README needs
updating, never the other way round.
"""

import pathlib
import re
import unittest

import pyomb

# Both places the version appears inside the install command. Capturing them
# separately means a half-finished edit fails rather than passing on whichever
# occurrence was updated.
WHEEL_URL = re.compile(r"/releases/download/v(?P<tag_path>[^/]+)/pyomb-(?P<filename>[^-]+)-py3-none-any\.whl")

README = pathlib.Path(__file__).resolve().parents[1] / "README.md"


class ReadmeInstallCommand(unittest.TestCase):
    """Pins the README's wheel URL to the version the package reports."""

    def setUp(self):
        self.readme = README.read_text(encoding="utf-8")
        self.matches = list(WHEEL_URL.finditer(self.readme))

    def test_the_quick_start_offers_exactly_one_release_wheel(self):
        """A README carrying no wheel URL would pass the version check below."""

        self.assertEqual(
            len(self.matches),
            1,
            "expected one release wheel URL in README.md, found "
            f"{len(self.matches)}. The quick start offers the wheel from the "
            "latest release; adding a second URL means this guard no longer "
            "pins the one a reader copies.",
        )

    def test_the_wheel_url_names_the_reported_version(self):
        """A bumped version and an unbumped README is a 404 for every reader."""

        for match in self.matches:
            for part, found in match.groupdict().items():
                with self.subTest(part=part):
                    self.assertEqual(
                        found,
                        pyomb.__version__,
                        f"the README wheel URL names {found} in its {part}, "
                        f"but the package reports {pyomb.__version__}. Point "
                        "the quick start install command at the current "
                        "release.",
                    )


if __name__ == "__main__":
    unittest.main()
