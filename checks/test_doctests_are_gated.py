"""The package's docstring examples are executed, and the exempt ones are named.

An example is the part of the documentation a reader is most likely to copy,
and the part most able to be checked mechanically. Nothing executed any of
them until the configuration this module guards was added, and what that hid
was an example asserting a property its class does not provide -- green on
main, for as long as anyone had been reading it.

Nothing is exempt. Three transport examples were, because each opened a socket
to a server nothing starts; they raised a connection error wherever they ran,
including in the hands of the reader they were written for. They are gone
rather than exempt, and the runnable demonstrations they were reaching for
live in `examples/`, where a peer can be started and CI executes the result.

The exemption machinery stays because the next unrunnable example is a
question of when. An exemption freezes one docstring at a time rather than
excluding a module, so a sibling example that needs no peer keeps its gate --
the difference between freezing the failing instances and narrowing the check.

Three ways this gate goes quietly blind, and one test each. The configuration
can stop reaching the package, in which case every example passes by not being
collected. An exempt name can drift -- an example renamed or removed leaves a
deselect matching nothing, which stops freezing anything and reads exactly like
a freeze that is still working. Or the two lists can disagree, leaving either
an exemption nobody wrote a reason for or a reason for one not in force.
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

# One deselect entry, capturing the qualified example name after the file path.
# The character classes are spelled out rather than written as a shorthand
# escape, which can be lost on the way into a file while still compiling.
DESELECT = re.compile(r'"--deselect=[^"]*::([A-Za-z0-9_.]+)"')

# The flag that collects the examples, and the path that puts the package in
# front of it. Both are matched against the manifest's text for the reason
# deselected_names gives.
COLLECTS_EXAMPLES = "--doctest-modules"

PACKAGE_PATH = re.compile(r"^testpaths *= *\[[^\]]*\"src\"", re.M)

# The examples that cannot run, each named as the deselect names it. Empty:
# the three transport docstrings that were here no longer carry examples at
# all, so there is nothing left to exempt. The only reason that belongs here
# is an example needing a peer the project cannot start; one failing for any
# other reason is a defect in the example.
DEFERRED = ()

# Re-measured on 2026-09-01 after the transport docstrings stopped carrying
# examples: 37 gated, 36 in the packet classes and one in the fragmenter. The
# gated count is unchanged by that work, because the three it removed were
# exempt and so were never counted here -- they were removed rather than
# replaced, which is the outcome the previous note left open. Unlike the
# append-only corpora the release-audit gate reads, an example can
# legitimately be removed, so this takes a stated margin below the measured
# count rather than the count itself.
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
