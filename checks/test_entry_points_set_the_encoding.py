"""An entry point states its output encoding; a library module never does.

A program that writes text and says nothing about its encoding takes whatever
the console hands it. That is what turns a correct string into mojibake on
someone else's machine, and the boundary is the thing to fix rather than every
string that crosses it.

Nothing in this tree could produce mojibake today, because the character-set
rule holds every non-Markdown file to ASCII, so every literal these programs
print already sits in the intersection of every encoding a console is likely to
use. That is a property of the strings, not of the boundary: an exception
message carrying bytes off the wire is formatted at runtime and no source rule
reaches it. Fixing the boundary is what makes the guarantee hold regardless.

The half of this that is a real defect rather than a tidy-up is where the call
goes. `sys.stdout` belongs to the process, not to the module that imports last.
A library module that reconfigures it at import reaches into an application
that only wanted to send a Modbus frame, and changes how every other writer in
that process behaves. So the rule has two directions, and this module asserts
both: an entry point sets the encoding inside its `__main__` guard, and nothing
under `src/` sets it anywhere else. The second assertion is the one worth
having, since the first only omits a line while the second corrupts a stream.

`src/pyomb/logger.py` is the case that looks like an exception and is not. It
builds a handler on `sys.stdout` and deliberately sets no encoding on it, for
the same reason its docstring already gives for not touching the root logger: a
library takes the stream it is handed.

Three roots are read: the package, the operational scripts, and the examples.
The last was added after the argument above was turned on it. Every example
prints values formatted at run time -- a packet's repr, an exception the
library raised -- so the character-set rule reaches them no further than it
reaches the wire bytes in that exception message, while the console they land
on is the least predictable of the three, being a stranger's rather than a
maintainer's.
"""

import ast
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

PACKAGE = REPO / "src" / "pyomb"

SCRIPTS = REPO / "scripts"

# The third root, and the one with the weakest console guarantee: a maintainer
# runs the other two, a stranger runs these. It was outside the rule until the
# character-set argument above was read against it -- every example prints
# values formatted at run time, so the source rule reaches them no further
# than it reaches an exception message in the package.
EXAMPLES = REPO / "examples"

# The standard streams a program may reconfigure. stderr is included so the
# import-scope rule cannot be satisfied by moving the call one stream over.
STREAMS = ("stdout", "stderr")

# What makes a module an entry point that writes text, rather than one that
# merely runs. A module with a guard that prints nothing is not required to
# state an encoding it never uses.
WRITERS = ("print", "Logger")

GUARD_REMEDY = "Add sys.stdout.reconfigure(encoding='utf-8') inside the __main__ guard, above the call the guard makes."

IMPORT_REMEDY = (
    "Move the call inside a __main__ guard. At import scope it mutates a "
    "stream the importing application owns, which reaches every other writer "
    "in that process."
)


def parsed(path):
    """Parse one source file.

    Args:
        path (pathlib.Path) : The file to read

    Returns:
        ast.Module : The parsed syntax tree
    """

    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def is_main_guard(node):
    """Report whether a node is an `if __name__ == "__main__":` block.

    Args:
        node (ast.AST) : Any syntax-tree node

    Returns:
        bool : True when the node guards a module's script path
    """

    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False

    left = node.test.left

    return isinstance(left, ast.Name) and left.id == "__name__"


def reconfigures_a_stream(node):
    """Report whether a node is a reconfigure call on a standard stream.

    Args:
        node (ast.AST) : Any syntax-tree node

    Returns:
        bool : True for sys.stdout.reconfigure(...) and its stderr twin
    """

    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False

    if node.func.attr != "reconfigure":
        return False

    stream = node.func.value

    return isinstance(stream, ast.Attribute) and stream.attr in STREAMS


def writes_text(tree):
    """Report whether a module ever writes to the console.

    Args:
        tree (ast.Module) : The module's syntax tree

    Returns:
        bool : True when the module calls print or builds a Logger
    """

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in WRITERS:
            return True

    return False


def guards(tree):
    """Collect a module's top-level `__main__` guards.

    Args:
        tree (ast.Module) : The module's syntax tree

    Returns:
        list[ast.If] : The guard nodes, in source order
    """

    return [node for node in tree.body if is_main_guard(node)]


class EntryPointsSetTheEncoding(unittest.TestCase):
    """Pins where the encoding call may appear, and where it may not."""

    @classmethod
    def setUpClass(cls):
        cls.sources = sorted(PACKAGE.glob("*.py")) + sorted(SCRIPTS.glob("*.py")) + sorted(EXAMPLES.glob("*.py"))
        cls.trees = {path: parsed(path) for path in cls.sources}

    def test_there_are_entry_points_to_check(self):
        """A pass means the rule was applied, not that nothing was found."""

        found = [path.name for path, tree in self.trees.items() if guards(tree) and writes_text(tree)]

        self.assertNotEqual(
            found,
            [],
            "no module with a __main__ guard writes text, so the assertion "
            "below would pass without reading anything. Either the guards "
            "moved or the writer signals need widening.",
        )

    def test_every_writing_entry_point_states_its_encoding(self):
        """A program that prints says how, rather than asking the console."""

        offenders = []

        for path, tree in self.trees.items():
            if not writes_text(tree):
                continue

            for guard in guards(tree):
                if not any(reconfigures_a_stream(node) for node in ast.walk(guard)):
                    offenders.append(f"{path.relative_to(REPO).as_posix()}:{guard.lineno}")

        self.assertEqual(
            offenders,
            [],
            "entry points that write text without stating an encoding, so the "
            "console decides it:\n  " + "\n  ".join(offenders) + "\n" + GUARD_REMEDY,
        )

    def test_no_library_module_reconfigures_a_stream_at_import(self):
        """The package takes the stream it is handed, whoever imports it."""

        offenders = []

        for path in sorted(PACKAGE.glob("*.py")):
            tree = self.trees[path]
            guarded = {id(node) for guard in guards(tree) for node in ast.walk(guard)}

            for node in ast.walk(tree):
                if reconfigures_a_stream(node) and id(node) not in guarded:
                    offenders.append(f"{path.relative_to(REPO).as_posix()}:{node.lineno}")

        self.assertEqual(
            offenders,
            [],
            "the package reconfigures a standard stream outside a __main__ "
            "guard, which mutates a stream the importing application "
            "owns:\n  " + "\n  ".join(offenders) + "\n" + IMPORT_REMEDY,
        )


if __name__ == "__main__":
    unittest.main()
