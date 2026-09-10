"""Readers for the changelog, shared by the gates that parse it.

Two gates read this file for different reasons. One pins the changelog to the
version the package reports, so a release cannot be tagged without its entry.
The other reads the dated entries as the in-tree record of what has shipped,
so a release branch can be told from the tree it sits on.

They parse the same document, so the parsing lives here rather than in either
of them. A second copy of a fence-aware section reader would drift from the
first the moment the changelog grows a fenced block, and only one of the two
gates would notice.
"""

import collections
import re

# The label Keep a Changelog reserves for the block that has not shipped, and
# the one whose link has to move on every release.
UNRELEASED = "Unreleased"

# One version section. The date is optional in the pattern, so a half-cut entry
# parses and is reported rather than reading as an entry that is not there.
Section = collections.namedtuple("Section", "version date")

SECTION = re.compile(r"^## \[(?P<label>[^\]]+)\](?:\s*-\s*(?P<date>\S+))?\s*$")

LINK = re.compile(r"^\[(?P<label>[^\]]+)\]:\s*(?P<target>\S+)\s*$")


def read_sections(text):
    """Read the version sections a changelog carries, in file order.

    Args:
        text (str) : The changelog's full Markdown source

    Returns:
        list[Section] : One entry per version section, `Unreleased` excluded
    """

    sections = []
    fenced = False

    for line in text.split("\n"):
        # A fence toggles rather than nests, so a heading quoted inside a block
        # is read past rather than reported as a section.
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue

        if fenced:
            continue

        found = SECTION.match(line)

        if found and found.group("label") != UNRELEASED:
            sections.append(Section(found.group("label"), found.group("date")))

    return sections


def read_section_body(text, label):
    """Read the bullet entries under one section heading, wrapped lines joined.

    Args:
        text (str)  : The changelog's full Markdown source
        label (str) : The section heading's label, `Unreleased` included

    Returns:
        list[str] : Each top-level bullet's text, in file order
    """

    entries = []
    current = None
    in_section = False
    fenced = False

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue

        if fenced:
            continue

        found = SECTION.match(line)

        if found:
            if current is not None:
                entries.append(" ".join(current))
                current = None

            in_section = found.group("label") == label

            continue

        if not in_section:
            continue

        if line.startswith("- "):
            if current is not None:
                entries.append(" ".join(current))

            current = [line[2:].strip()]
        elif current is not None and line.strip() and not line.startswith("#"):
            current.append(line.strip())
        elif current is not None:
            entries.append(" ".join(current))
            current = None

    if current is not None:
        entries.append(" ".join(current))

    return entries


def read_links(text):
    """Read the link definitions at the foot of a changelog.

    Args:
        text (str) : The changelog's full Markdown source

    Returns:
        dict[str, str] : Each label's target, `Unreleased` included
    """

    links = {}
    fenced = False

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue

        if fenced:
            continue

        found = LINK.match(line)

        if found:
            links[found.group("label")] = found.group("target")

    return links
