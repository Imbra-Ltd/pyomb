"""The startup block is the chain the pin resolves, not a list kept by hand.

CLAUDE.md opens with a block naming every template that must be read before the
first response, and that list cannot live anywhere else -- the file carrying it
is the only one loaded before an agent does anything. Both ways it goes wrong
are silent and neither shows in a diff, so the guard names which side each
difference sits on rather than reporting that the sets differ.

The resolution is the manifest's. Only the two axis selections and the three
templates no stack declares are written here; the rest is derived, so an
upstream file joining the chain changes the expected set without an edit.
PLAYBOOK 4.1 carries the reconciliation a bump owes.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

SUBMODULE = REPO / "docs" / "solid-ai-templates"

MANIFEST = "templates/manifest.yaml"

# What this repository is, on the two axes the manifest selects layers along.
# Neither is derivable, and the pair is the whole hand-written input here.
AXES = ("stack-python-lib", "platform-github")

# No stack declares these, so the chain never reaches them. The session
# protocol needs the first two; communication states how the agent answers.
UNDECLARED = frozenset(
    {
        "templates/base/workflow/scope.md",
        "templates/base/workflow/ai-workflow.md",
        "templates/base/workflow/communication.md",
    }
)

# The shapes the manifest uses for the fields this resolution reads. An entry
# opens at two spaces, its fields sit at four, and a block list at six.
ENTRY_ID = re.compile(r"^ {2}- id: (\S+)\s*$")
ENTRY_FILE = re.compile(r"^ {4}file: (\S+)\s*$")
INLINE_DEPENDS = re.compile(r"^ {4}depends_on: \[(.*)\]\s*$")
BLOCK_DEPENDS = re.compile(r"^ {4}depends_on:\s*$")
BLOCK_ITEM = re.compile(r"^ {6}- (\S+)\s*$")

# The ids every project resolves whatever its stack and platform, written as a
# single inline list at the top of the manifest.
CORE = re.compile(r"^core: \[(.*)\]\s*$", re.M)

# The block's entries, each a list item naming one template path in a code
# span. Scoped to the block, so a path in prose elsewhere cannot join the set.
BLOCK_ENTRY = re.compile(r"^- `(templates/[^`]+)`", re.M)

STARTUP_HEADING = "## Mandatory startup"

NOT_A_CHECKOUT = "the templates submodule is not checked out, so there is no pinned manifest to resolve"

DIRECTION = (
    "The block is a copy of what the manifest resolves, so it is the side to "
    "correct unless the axes above are wrong. Reconcile it in the same change "
    "as the bump that moved the chain."
)


def manifest_at_pin():
    """Read the templates manifest as the pinned revision carries it.

    Returns:
        str : The manifest's full text
    """

    # The argument vector is a fixed list and carries no caller input, so it
    # reaches the operating system directly rather than through a shell.
    return subprocess.run(  # nosec B603 B607
        ["git", "-C", str(SUBMODULE), "show", f"HEAD:{MANIFEST}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def read_entries(manifest):
    """Map each manifest id to the file it names and the ids it depends on.

    Args:
        manifest (str) : The manifest's full text

    Returns:
        dict[str, tuple[str | None, tuple[str, ...]]] : Each id's file and edges
    """

    entries = {}
    current = None
    in_block = False

    for line in manifest.split("\n"):
        opened = ENTRY_ID.match(line)

        if opened:
            current = [None, []]
            entries[opened.group(1)] = current
            in_block = False
            continue

        if current is None:
            continue

        named = ENTRY_FILE.match(line)

        if named:
            current[0] = named.group(1)
            in_block = False
            continue

        inline = INLINE_DEPENDS.match(line)

        if inline:
            current[1] = split_ids(inline.group(1))
            in_block = False
            continue

        if BLOCK_DEPENDS.match(line):
            in_block = True
            continue

        if in_block:
            item = BLOCK_ITEM.match(line)

            if item:
                current[1].append(item.group(1))
            else:
                in_block = False

    # An entry is built as a mutable pair because its two fields arrive on
    # separate lines. Freezing on the way out keeps a caller from editing it.
    return {name: (file, tuple(edges)) for name, (file, edges) in entries.items()}


def split_ids(inline):
    """Split one inline list's body into ids.

    Args:
        inline (str) : The text between the brackets

    Returns:
        list[str] : The ids, in the order written
    """

    return [name.strip() for name in inline.split(",") if name.strip()]


def read_core(manifest):
    """Read the ids every project resolves regardless of stack or platform.

    Args:
        manifest (str) : The manifest's full text

    Returns:
        list[str] : The core ids, in the order written
    """

    found = CORE.search(manifest)

    return split_ids(found.group(1)) if found else []


def resolve(manifest):
    """Close the manifest's dependency edges over this repository's roots.

    Args:
        manifest (str) : The manifest's full text

    Returns:
        tuple[set[str], list[str]] : The template paths, and any id that could
            not be resolved to one
    """

    entries = read_entries(manifest)

    files = set()
    unresolved = []
    seen = set()
    pending = read_core(manifest) + list(AXES)

    while pending:
        name = pending.pop()

        if name in seen:
            continue

        seen.add(name)

        if name not in entries:
            unresolved.append(f"{name} (no manifest entry)")
            continue

        file, edges = entries[name]

        if file is None:
            unresolved.append(f"{name} (entry names no file)")
            continue

        files.add(file)
        pending.extend(edges)

    return files | UNDECLARED, unresolved


def startup_block():
    """Read the template paths the CLAUDE.md startup block instructs reading.

    Returns:
        set[str] : The paths the block names
    """

    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")

    opened = text.find(STARTUP_HEADING)

    if opened < 0:
        return set()

    # The block runs to the next heading of the same level, so a template path
    # written in prose further down does not count as an instruction.
    closed = text.find("\n## ", opened + len(STARTUP_HEADING))

    return set(BLOCK_ENTRY.findall(text[opened : closed if closed > 0 else len(text)]))


class StartupBlockResolvesTheChain(unittest.TestCase):
    """Pins the startup block to the chain the pinned manifest resolves."""

    @classmethod
    def setUpClass(cls):
        # Without a checkout there is no pinned manifest, and resolving
        # anything else answers about a revision this repository does not pin.
        if not (SUBMODULE / ".git").exists():
            raise unittest.SkipTest(NOT_A_CHECKOUT)

        manifest = manifest_at_pin()

        cls.resolved, cls.unresolved = resolve(manifest)
        cls.listed = startup_block()
        cls.core = read_core(manifest)

    def test_the_manifest_reader_resolved_every_id_it_reached(self):
        """A dropped edge would resolve short and blame the block for it."""

        self.assertEqual(
            self.unresolved,
            [],
            "the manifest reader reached ids it could not turn into files:\n  "
            + "\n  ".join(self.unresolved)
            + "\nThe manifest's shape has moved beyond the four this module "
            "reads. Fix the reader, not the startup block -- the differences "
            "the other checks report are this module's own.",
        )

    def test_the_manifest_carries_a_core_set(self):
        """An unreadable core line would drop six files from both sides at once."""

        self.assertNotEqual(
            self.core,
            [],
            "no core list was read from the manifest, so the resolution is "
            "missing every file that enters through it. The core line is a "
            "single inline list at the top of the manifest; if it has moved "
            "to another shape, this module reads it wrongly.",
        )

    def test_the_startup_block_was_found_where_this_expects_it(self):
        """An unfound block is empty, and an empty one would fail the wrong check."""

        self.assertNotEqual(
            self.listed,
            set(),
            f"no template paths were read from the {STARTUP_HEADING!r} section "
            "of CLAUDE.md. Either the heading has been renamed or its entries "
            "no longer name one path per list item in a code span.",
        )

    def test_the_block_omits_nothing_the_chain_resolves(self):
        """Upstream adding a template leaves the block governing less than it should."""

        missing = sorted(self.resolved - self.listed)

        self.assertEqual(
            missing,
            [],
            "the chain resolves template files the startup block does not "
            "name, so they govern this repository and go unread:\n  " + "\n  ".join(missing) + "\n" + DIRECTION,
        )

    def test_the_block_names_nothing_the_chain_does_not_resolve(self):
        """A template left in the block is a rule the project never adopted."""

        extra = sorted(self.listed - self.resolved)

        self.assertEqual(
            extra,
            [],
            "the startup block names template files the chain does not "
            "resolve, so the project reads rules nothing declares:\n  " + "\n  ".join(extra) + "\n" + DIRECTION,
        )


if __name__ == "__main__":
    unittest.main()
