---
id: "035"
status: Accepted
date: 2026-09-01
category: protocol
supersedes: []
superseded_by: []
---

# ADR-035: The direction note contributes a vocabulary, not a structure

**Upstream:** filed as `none`. With the domain skin off: a proposal document
reviewed against a tree that has moved past it is adopted rule by rule, and
what it contributes is usually names for things that already exist rather
than a structure to build. One project reaching that once is not evidence it
generalizes; revisit if a second does.

## Context

`docs/design/design_notes.md` runs 873 lines and proposes four operating
modes, six architectural layers, twelve capabilities and a roadmap to 1.0.
It binds nothing. Issue #224 reviewed it and raised seven findings. The
first is already answered by the record that made packet constraints
queryable, which rejected the note's three validation modes. Six remain.

### What the tree holds, measured today

| Claim | Command | Result |
| --- | --- | --- |
| No serial anywhere | `grep -rn "import serial" src/pyomb/` | prints nothing |
| Transport seams exist | `grep -n "^class " src/pyomb/stream.py` | four abstract bases naming no transport |
| Function codes | `grep -rn "PDU_ID" src/pyomb/packets.py` | thirteen request codes |

The thirteen are 1, 2, 3, 4, 5, 6, 7, 8, 15, 16, 22, 23 and 43.

### Two corrections to the review that produced these findings

Finding 3 reports "twelve of thirteen exist". Both figures are wrong. The
note lists twelve target codes and eleven of them exist, FC24 being the
only absent one. FC7 and FC8 are implemented and the note lists neither, so
across the fourteen codes the two lists name between them, thirteen exist.

Finding 6 lists capabilities that trace to no requirement. Two of its
neighbours in the note do trace to one, because they are already built:
fragmentation and per-fragment delay live in `stream.py`, and the server
carries a delay, a failure switch and a connection limit. The note names
these a Channel layer; the tree has the behaviour without the name.

### What forces the decision now

Four open issues wait on this review. Three of them — #173, #192 and #194 —
touch simulator surfaces the note restructures, and finding 4 says to
sequence the document first or pay twice. They cannot start until the
restructure is either adopted or refused.

## Decision

| # | Rule |
| --- | --- |
| 1 | The three-package import rule binds; the six layers are vocabulary |
| 2 | A capability tracing to no requirement is neither adopted nor tracked |
| 3 | Serial transport is in scope, tracked by #231, and unscheduled |
| 4 | The note's roadmap is not a plan |
| 5 | A round-trip property never stands alone |
| 6 | #173, #192 and #194 are unblocked by this record |

### 1. The layers describe responsibilities the packages already carry

`CLAUDE.md` 1.2 binds three packages and the direction imports may travel
between them. The note's six layers are not a competing structure. They are
a finer reading of the same pipeline, and each maps onto exactly one
package:

```text
  the note's six layers            the three packages that bind
  ---------------------            ----------------------------
  Testing / Scenarios    --+
  Client / Server        --+-----> simulators
  PDU                    --+
  Framing                --+-----> codec
  Channel / Wire         --+
  Transport              --+-----> transport
```

The six names MAY be used in prose and in docstrings, where they are more
precise than the package name. They MUST NOT be read as a mandate to split
`packets.py` into a PDU module and a framing module, or `stream.py` into a
channel module and a transport module. No requirement asks for either
split, and the import rule that binds is already enforced.

Revisit trigger: a second transport landing under #231. Framing and
transport genuinely separate at that point, because an RTU framer splits on
silence and a TCP framer splits on a declared length. Re-read this rule
then rather than on a schedule; nothing else watches it.

### 2. An unrequired capability is refused, not filed

Proxy mode, PCAP export, capture and replay, deterministic fuzzing, an
async API and the conformance framework trace to no requirement this
project has stated. None is adopted. None gets a tracking issue either,
because an issue for unrequired work is a backlog entry that every future
grooming pass re-reads and re-defers.

Adopting any one of them takes its own record, written when a requirement
appears. This is the scope guard applied to a document rather than to a
session: a planned item traceable to no requirement is scope creep whatever
document proposes it.

Fault injection and wire control are outside this rule. They are the
project's stated purpose and they already ship.

### 3. Serial transport is in scope and unscheduled

The project describes itself as a library for Modbus TCP and RTU. RTU
reaches the codec and stops: the two RTU packet classes decode bytes a
caller already holds, and nothing can obtain those bytes. That gap is
between what the project claims and what it does, which is a requirement
rather than a speculative feature.

So serial is in scope, and rule 2 does not reach it. It stays unscheduled
and unmilestoned, tracked by #231, which already carries the three layers
the work needs. When it is picked up, `pyserial` sits behind an extra named
for the capability rather than the library, and the codec keeps importing
no socket and no serial port.

### 4. Version numbers come from the milestone

The note's roadmap assigns transport and framer work to 0.4. That release
shipped without it, so every later row names a version the project will not
match. The roadmap is not adopted, and no attempt is made to repair it.

Scope for a release is decided by the milestone, which is a live record.
The roadmap stays in the note as what was proposed on the day.

### 5. A round-trip property never stands alone

The note's section 23 proposes `deserialize(serialize(packet)) == packet`
as the property to test extensively. `CLAUDE.md` 3 already refuses that as
a standalone: a round trip proves the encoder and the decoder agree, not
that either is right. Three shipped defects had exactly that shape.

The note's section is therefore rejected rather than adopted, and no new
rule is written, because the rule already has one home. A property-based
test MAY round-trip, and MUST anchor at least one case to a published
vector under `docs/specs/`.

Hypothesis is not adopted. Every property this codec has needed so far is
expressible as a parameterized case over specification vectors. Revisit
trigger: a property that cannot be written that way.

### 6. The three simulator issues are unblocked

Rule 1 refuses the restructure, so there is no pending document change for
#173, #192 and #194 to be sequenced behind. Finding 4's "pay twice" cost
does not arise. The three proceed on their own merits, and #192 still wants
the same release as #173 because both break the same public API.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Adopt the six-layer model and rewrite `CLAUDE.md` 1.2 in the same change | The closest to a full answer. It buys a name for two seams that already have one, at the price of splitting two modules no requirement asks to split, and it blocks three open issues while the split lands. |
| Reject the six layers outright, names included | Simpler to state and it throws away the part that works. Channel and Framing name real behaviour the tree has and the package names do not distinguish, which is exactly what a vocabulary is for. |
| File a tracking issue per unrequired capability | Makes the backlog honest about what was considered. It also creates six tickets nobody will close, each re-read at every grooming pass, and an unmilestoned issue is meant to be deferred work rather than refused work. |
| Rule serial out of scope with the other capabilities | Consistent, and it contradicts the project's own one-line description. RTU is half-delivered rather than unrequested, so refusing it would leave the claim standing with nothing behind it. |
| Correct the note's roadmap and function-code list in place | Puts the correction where the reader finds the error. The record governing design notes forbids it: a note is not edited to record what was decided about it, or it becomes a second place to look for a rule. |
| Split this record into one per finding | Each finding then carries its own context and its own reversal cost. They share one question — what this document contributes — and answering it six times would repeat the same context six times. |

## Consequences

- Three issues are unblocked and none of them changed. #173, #192 and #194
  can be scheduled on their own merits, which is what finding 4 asked for.
- Six capabilities are refused with no tracking issue. Nothing will surface
  them again, which is the intent and also the cost: a requirement arriving
  later has to find this record rather than a ticket.
- The note keeps two known errors in its body, its roadmap and its testing
  section. A reader who opens it without this record reads both as current.
  Rule 3 of the record governing design notes accepts that cost already.
- Serial stays unmilestoned, so nothing schedules it. The revisit trigger
  on rule 1 fires when it lands, and a person reading this record is what
  detects that; no gate does.
- `CLAUDE.md` 1.2 is unchanged. That is the point of rule 1, and it means
  the six-layer vocabulary lives only here.
- The Channel and Framing names are now usable in docstrings without
  implying a module. A future reader may still take a docstring naming a
  layer as a promise that the layer is a package.
- Nothing about the wire changes, no signature moves, and no test is
  touched. This record is a decision about direction only.

## Related

- Issue #224 — the review this record answers, and its seven findings
- Issue #231 — the serial transport work rule 3 puts in scope
- Issues #173, #192, #194 — the simulator surfaces rule 6 unblocks
- ADR-030 — the record that governs how a design note is treated
- ADR-031 — the record that answered finding 1 by rejecting validation modes
- `docs/design/design_notes.md` — sections 3, 4, 6 to 9, 23 and 24
