"""The startup block is the chain the pin resolves, not a list kept by hand.

CLAUDE.md opens with a block naming every template file that must be read
before the first response. That list cannot live anywhere else: the rule
requiring it exists because the file carrying it is the only one loaded before
an agent does anything, so every other document is unreachable until something
names it. What the list can be is checked, and until now only half of it was.

The maintenance recipe states both ways the block goes wrong. It ships a
command for one of them -- a block naming a file the pin does not carry, which
is a startup instruction that cannot be followed -- and leaves the other as
prose telling the reader to resolve the chain and compare. That second
direction is the one that has already fired. Upstream moved a template into the
chain, the block stayed short, and nothing reported it; a person noticed, and
the reconciliation became a ticket.

Both directions are silent, and neither shows up in a diff, because the change
that causes them happens in another repository. A short block reads as this
project maintaining a convention upstream already owns. A long one reads as
this project enforcing rules it never adopted. The two failures need opposite
responses and look identical from here, which is why the guard names which side
each difference sits on rather than reporting that the sets differ.

The resolution is the manifest's, not this module's. Two axes select the roots
-- what the project is built with and where it is hosted -- and the manifest's
own core set and dependency edges close over them. Only four facts are written
down here: the two axis selections, which are what this repository is, and the
two session-protocol templates no stack declares, which the decision record on
the startup block explains. Everything else is derived, so an upstream file
that joins or leaves the chain changes the expected set without an edit here.

The manifest is read at the pinned revision rather than from the working tree
or the upstream default branch. Those describe a future state of this
repository, and a rule read from one and quoted as governing does not govern
until the pin moves.

Reading it needs no YAML parser, which would be a dependency this project does
not carry, so a small reader takes the four shapes the manifest actually uses.
It is checked before it is trusted: a reader that silently dropped an edge
would resolve short and blame the block, so the first test fails on an
unresolvable id instead of letting the second report a difference it caused.
"""

import pathlib
import re
import subprocess  # nosec B404
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

SUBMODULE = REPO / "docs" / "solid-ai-templates"

MANIFEST = "templates/manifest.yaml"

# What this repository is, on the two independent axes the manifest selects
# layers along. Neither is derivable: a stack is what the project is built
# with, a platform is where it is hosted, and nothing in the tree states
# either. These two are the whole hand-written input to the resolution.
AXES = ("stack-python-lib", "platform-github")

# No stack declares these, so the chain never reaches them and each is added
# deliberately. The decision record covering the startup block carries why
# they are added rather than resolved. The first two are what the session
# protocol needs; communication states how the agent answers, which binds
# every turn and so is worthless unresolved -- it went unread for the whole
# life of the block because nothing listed it.
UNDECLARED = frozenset(
    {
        "templates/base/workflow/scope.md",
        "templates/base/workflow/ai-workflow.md",
        "templates/base/workflow/communication.md",
    }
)

# The four shapes the manifest uses for the fields this resolution reads. An
# entry opens at two spaces of indent and its fields sit at four; dependencies
# appear either inline in brackets or as a block list at six.
ENTRY_ID = re.compile(r"^ {2}- id: (\S+)\s*$")
ENTRY_FILE = re.compile(r"^ {4}file: (\S+)\s*$")
INLINE_DEPENDS = re.compile(r"^ {4}depends_on: \[(.*)\]\s*$")
BLOCK_DEPENDS = re.compile(r"^ {4}depends_on:\s*$")
BLOCK_ITEM = re.compile(r"^ {6}- (\S+)\s*$")

# The ids every project resolves whatever its stack and platform, written as a
# single inline list at the top of the manifest.
CORE = re.compile(r"^core: \[(.*)\]\s*$", re.M)

# The startup block's entries, each a list item naming one template path in a
# code span. Scoped to the block itself so a path mentioned in prose elsewhere
# in the file cannot join the set being checked.
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

    # The suppressed checks rest on the argument vector being a list, which
    # goes to the operating system directly rather than through a shell, so
    # nothing in it can become a second command. It is fixed, with no caller
    # input anywhere in it. The checks match on call shape and see neither.
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
    # separate lines. Freezing them on the way out keeps a caller from
    # editing the table it was handed.
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

    # The block runs to the next heading of the same level. Bounding it stops
    # a template path written in prose further down the file from counting as
    # an instruction to read that file.
    closed = text.find("\n## ", opened + len(STARTUP_HEADING))

    return set(BLOCK_ENTRY.findall(text[opened : closed if closed > 0 else len(text)]))


class StartupBlockResolvesTheChain(unittest.TestCase):
    """Pins the startup block to the chain the pinned manifest resolves."""

    @classmethod
    def setUpClass(cls):
        # Without a checkout there is no pinned manifest, and resolving
        # anything else would answer about a revision this repository does not
        # pin. The skip is for that case only; a checkout whose git call fails
        # is a failure, not a skip.
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
