"""The message and its envelope never import a socket.

ADR-054 narrowed the codec rule from one package to two: pdu carries the
message, adu carries the envelope a transport puts around it, and neither
may import a socket, TLS, or anything from the transport package that
wraps them. The rule is written down in CLAUDE.md 1.2; this is what
enforces it, since a comment nobody checks is a promise nobody keeps.
"""

import ast
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# The two packages the rule binds, read from the source tree rather than
# hardcoded elsewhere, so a third package added later inherits the check
# only once it is added here.
ROOTS = ("pdu", "adu")

# A dotted module name is forbidden if it equals one of these, or if it
# starts with one of these followed by a dot -- socket.socket as much as
# socket, pyomb.transport.tls as much as pyomb.transport.
FORBIDDEN = ("socket", "ssl", "pyomb.transport")

# What the tree held when this floor was set: five files across the two
# packages (pdu's four group modules plus common.py, and adu's two).
FILES_AT_LEAST = 6


def forbidden_import(name):
    """Whether a dotted module name reaches the network boundary.

    Args:
        name (str) : A dotted module name from an import statement

    Returns:
        str : The forbidden name it matches, or "" if none do
    """

    for banned in FORBIDDEN:
        if name == banned or name.startswith(banned + "."):
            return banned

    return ""


def network_imports(path):
    """The forbidden imports one file's own statements name.

    Args:
        path (pathlib.Path) : The source file to read

    Returns:
        list[str] : One "line: name (matches banned)" entry per import
            that reaches the network boundary
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    found = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                banned = forbidden_import(alias.name)
                if banned:
                    found.append(f"{node.lineno}: import {alias.name} (matches {banned})")

        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            banned = forbidden_import(node.module)
            if banned:
                found.append(f"{node.lineno}: from {node.module} import ... (matches {banned})")

    return found


class PduAndAduDoNotTouchTheNetwork(unittest.TestCase):
    """Pins the codec's network-free half of the split ADR-054 made."""

    @classmethod
    def setUpClass(cls):
        cls.files = sorted(path for root in ROOTS for path in (REPO / "src" / "pyomb" / root).glob("*.py"))

    def test_the_enumeration_reached_both_packages(self):
        """A pass below means the files were read, not that none were."""

        self.assertGreaterEqual(
            len(self.files),
            FILES_AT_LEAST,
            f"found {len(self.files)} file(s) under {ROOTS} where the tree "
            f"holds at least {FILES_AT_LEAST}; the rule below would pass "
            "having read almost nothing rather than the packages being clean.",
        )

    def test_neither_package_imports_the_network(self):
        """pdu carries the message, adu carries its envelope; neither opens a socket."""

        offenders = []

        for path in self.files:
            for entry in network_imports(path):
                offenders.append(f"{path.relative_to(REPO)}:{entry}")

        self.assertEqual(
            offenders,
            [],
            f"{len(offenders)} import(s) reach the network boundary from "
            "pdu or adu, which CLAUDE.md 1.2 states neither may cross:\n  " + "\n  ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
