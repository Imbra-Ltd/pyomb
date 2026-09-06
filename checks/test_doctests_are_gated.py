"""The package's docstring examples are executed, and the exempt ones are named.

Nothing executed any of them until the configuration this module guards was
added, and what that hid was an example asserting a property its class does not
provide -- green on main, for as long as anyone had been reading it.

Three ways the gate goes quietly blind, and one test each: the configuration
stops reaching the package, an exempt name drifts so its deselect freezes
nothing, or the two lists disagree. PLAYBOOK 3.24 carries the exemption rule
and what was removed rather than exempted.
"""

import doctest
import importlib
import pathlib
import pkgutil
import re
import unittest

import pyomb

REPO = pathlib.Path(__file__).resolve().parents[1]

MANIFEST = REPO / "pyproject.toml"

# One deselect entry, capturing the qualified name after the file path. The
# classes are spelled out: a shorthand escape can be lost into a file.
DESELECT = re.compile(r'"--deselect=[^"]*::([A-Za-z0-9_.]+)"')

# The flag that collects the examples, and the path that puts the package in
# front of it. Both matched as text, for the reason deselected_names gives.
COLLECTS_EXAMPLES = "--doctest-modules"

PACKAGE_PATH = re.compile(r"^testpaths *= *\[[^\]]*\"src\"", re.M)

# The examples that cannot run, each named as the deselect names it. The only
# admissible reason is a peer the project cannot start.
DEFERRED = ()

# Re-measured on 2026-09-01: 37 gated, 36 in the packet classes and one in the
# fragmenter. An example can be removed, so the floor takes a margin below it.
GATED_AT_LEAST = 30


def examples_by_name():
    """Every docstring in the package that carries examples.

    Returns:
        dict[str, int] : Qualified name to the number of example lines
    """

    found = {}

    for info in pkgutil.iter_modules(pyomb.__path__, pyomb.__name__ + "."):
        module = importlib.import_module(info.name)

        for test in doctest.DocTestFinder().find(module):
            if test.examples:
                found[test.name] = len(test.examples)

    return found


def deselected_names():
    """The examples the manifest exempts from the gate.

    The manifest is read as text rather than parsed. A TOML reader entered the
    standard library in 3.11 and this project supports 3.10, so parsing would
    cost a dependency to read three lines.

    Returns:
        list[str] : One qualified name per deselect, in manifest order
    """

    return DESELECT.findall(MANIFEST.read_text(encoding="utf-8"))


class DoctestsAreGated(unittest.TestCase):
    """Pins the example gate to a corpus it actually reaches."""

    @classmethod
    def setUpClass(cls):
        cls.found = examples_by_name()
        cls.deselected = deselected_names()

    def test_the_gate_is_switched_on_in_the_manifest(self):
        """Without the flag every example passes by never being collected."""

        manifest = MANIFEST.read_text(encoding="utf-8")

        self.assertIn(
            COLLECTS_EXAMPLES,
            manifest,
            "the examples are not collected, so nothing below measures them. "
            "A suite that never runs an example reports the same green as one "
            "where every example holds.",
        )
        self.assertIsNotNone(
            PACKAGE_PATH.search(manifest),
            "the package is outside the collected paths, so the collect flag "
            "reaches only the test modules and no example in src/ runs.",
        )

    def test_the_gate_reaches_the_examples_in_the_package(self):
        """A pass below means the examples were read, not that none were found."""

        gated = {name: n for name, n in self.found.items() if name not in DEFERRED}

        self.assertGreaterEqual(
            len(gated),
            GATED_AT_LEAST,
            f"the finder reached {len(gated)} gated example(s) where the floor "
            f"is {GATED_AT_LEAST}. Either the package stopped carrying them, "
            "or the traversal no longer reaches its modules -- and a traversal "
            "that reaches nothing reports every example as holding.",
        )

    def test_every_exempt_example_still_exists(self):
        """A deselect that matches nothing has stopped freezing anything."""

        missing = [name for name in DEFERRED if name not in self.found]

        self.assertEqual(
            missing,
            [],
            f"{missing} are exempt from the gate and carry no examples any "
            "more. A deselect naming an example that has been renamed or "
            "removed silently matches nothing, which looks identical to a "
            "freeze that is still holding. Drop the entry, or correct it.",
        )

    def test_the_manifest_exempts_exactly_what_this_module_records(self):
        """Two copies of one list, so the drift has somewhere to be caught."""

        self.assertEqual(
            sorted(self.deselected),
            sorted(DEFERRED),
            "the manifest's deselect list and the list recorded here disagree. "
            "The manifest is what pytest obeys and this module is what states "
            "why, so a name in one and not the other is either an unexplained "
            "exemption or a reason for an exemption that is not in force.",
        )


if __name__ == "__main__":
    unittest.main()
