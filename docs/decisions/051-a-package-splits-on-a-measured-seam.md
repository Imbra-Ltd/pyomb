---
id: "051"
status: Accepted
date: 2026-09-07
category: repository
supersedes: []
superseded_by: []
---

# ADR-051: A package splits on a measured seam, not on a vocabulary

**Upstream:** filed as `none` for now, because the rule set this would
target is being reworked to require fewer records. With the domain skin
off: a rule refusing a document's authority to mandate a structure binds
the justification and not the shape. A change made on independent grounds
does not break it, and reads as though it does.

## Context

`src/pyomb/packets.py` reached 4135 lines. Pull request 362 made it a
package, sliced on that size and on an import graph that stays acyclic.
Every definition was carried verbatim, and a syntax-tree comparison
against the base found all 43 top-level definitions byte-identical.

### What the tree holds, measured today

| Claim | Command | Result |
| --- | --- | --- |
| The module that was split | `git show c8ace1b^:src/pyomb/packets.py \| wc -l` | 4135 lines |
| What replaced it | `wc -l src/pyomb/packets/*.py` | 107, 224, 856, 3089 |
| Imports run one way | `grep -n "^from pyomb.packets" src/pyomb/packets/*.py` | `base <- pdu <- framing` |
| The transport module is untouched | `wc -l src/pyomb/stream.py` | 646 lines, one file |
| The import path is unchanged | `grep -c "^from pyomb.packets" src/pyomb/packets/__init__.py` | 3 submodules re-exported |

### The rule the split appears to break

A merged record refuses a proposal document's six-layer vocabulary as a
structure and keeps it as names. Its first rule says those names:

> MUST NOT be read as a mandate to split `packets.py` into a PDU module
> and a framing module, or `stream.py` into a channel module and a
> transport module.

That clause binds a reading. The split shipped on file size, so it took
none of that reading, and the rule as written is not what forbids it.

What makes the disagreement real is the names. Two of the three
submodules are `pdu.py` and `framing.py`, which are two of the six layer
words. A reader meeting them cannot recover which reason produced them,
and the nearest rule reads as a prohibition they broke.

The pull request said so and declined to decide it. The tree has carried
the disagreement since, and the development journal has carried it as
pending.

## Decision

| # | Rule |
| --- | --- |
| 1 | A package splits on a measured seam; a vocabulary is never one |
| 2 | A submodule name follows its content and confers no authority |
| 3 | The second-transport trigger keeps only its transport half |

```text
  reason offered               reason taken
  -------------------------    ---------------------------
  the six-layer vocabulary     4135 lines in one module
  refused, and still is        measured, and what split it
                                            |
                                            v
                          packets/  base <- pdu <- framing
                          import path pyomb.packets unchanged
```

### 1. A seam is a property of the tree

A split is decided by something a command reports: the size of a module,
the direction of its imports, or a cohesion boundary a reader can point
at. A document proposing layers supplies none of those.

So the standing prohibition binds the justification and not the shape.
The split that shipped took the vocabulary as no part of its argument,
and it is ratified here rather than excused.

### 2. A name follows content

A submodule MAY carry a layer name where the name describes what the
module holds. `framing.py` holds the header, the checksum helpers and the
two ADU classes, so the name is accurate before it is anything else.

Naming a module for a layer grants that vocabulary nothing. No layer
becomes a package by being named, and the two layers that have no module
of their own are not owed one by this record.

### 3. The trigger keeps its transport half

A second transport landing re-opens whether channel and transport want
separate homes inside `stream.py`, which is still one file of 646 lines.
It asks nothing further about the codec, whose layout is settled here.

The narrowing does not touch the premise that trigger rests on. Issue 358
records a falsified claim inside it and defers the correction to whoever
designs the serial frame splitter, which this record leaves untouched.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Supersede the record carrying the rule | Its other five rules are current, and a record marked superseded to correct one clause makes every later reader meet a dead document. The corpus already carries one instance of that cost. |
| Rename the submodules to reuse none of the vocabulary | Removes the ambiguity at its source, and pays for it with names that describe the content worse. Those modules hold a PDU range and a framing layer; a name chosen to dodge a coincidence is a worse name. |
| Withdraw the prohibition outright | Simpler to state, and it discards the half that works. What was refused is a document's authority to mandate a structure, and nothing about a size-driven split restores that authority. |
| Revert the split and restore one module | Consistent with the rule as a reader meets it, at the price of a 4135-line module and the five gates the split repaired. The rule was never about file size. |
| Leave the disagreement until the transport trigger fires | Cheapest today. It leaves a live MUST NOT contradicting the tree for however long that takes, and the next reader cannot tell a deliberate exception from an oversight. |

## Consequences

- Nothing in the tree changes. No file moves, no signature moves, no test
  is touched, and `from pyomb.packets import X` resolves as it did.
- The prohibition binds narrower than a reader would take it from the
  text alone. It refuses a reason, and this record is where that reading
  is written down.
- A future split needs a measurement in its pull request body. A seam
  argued from the layer names alone is refused by rule 1, which is the
  cost rule 1 deliberately imposes.
- A reader meeting `framing.py` still learns nothing about whether a
  Framing layer exists. Rule 2 says the name settles nothing, and only a
  reader who finds this record learns that.
- The revisit trigger is smaller and still unwatched. A person reading
  the rule when a second transport lands is the whole detection
  mechanism, as it was before.
- This record is the only thing joining the shipped names to the rule
  they appear to break, and a reader of that rule does not meet it. That
  cost is the erratum problem issue 359 exists to answer.

## Related

- ADR-035 -- the record whose first rule this one narrows
- Pull request #362 -- the split that shipped, and the note that flagged
  the disagreement rather than deciding it
- Issue #358 -- the falsified premise inside that rule's revisit trigger
- Issue #359 -- the erratum question the last consequence is an instance
  of
