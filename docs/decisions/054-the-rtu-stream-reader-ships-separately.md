---
id: "054"
status: Accepted
date: 2026-09-07
category: repository
supersedes: []
superseded_by: []
---

# ADR-054: The RTU stream reader ships from a separate package

**Upstream:** not filed; the issue is owed, and filing on another repository
is the owner's call. With the domain skin off: merging to a public repository
under a permissive licence publishes irrevocably, so a capability the project
means to withhold is withdrawn before the next tag rather than before the next
merge. `templates/base/core/git.md` is the candidate file.

## Context

Modbus RTU puts no length field on the wire. A reader therefore works out
where each frame ends from the content, and this library gained that reader on
2026-09-07. Five names carried it: the direction, a splitter told which
direction it decodes, a sniffer told nothing, the synchronisation state, and
one frame paired with the direction it was read as.

That capability is to be sold. This repository is public and its licence is
MIT, so every release hands what it holds to anyone who installs it, under no
condition and with no way back.

No released artifact carries the five names yet:

``` text
git ls-tree -r --name-only v0.6.0 -- src/pyomb/ | grep -i packet
    src/pyomb/packets.py          <- one module, no stream reader

git log --format='%h %cs' -1 -- src/pyomb/packets/framing.py
    dabd4b8 2026-09-07            <- landed after the tag of 2026-09-03
```

The commits are public and cannot be recalled. What is still open is what the
next release carries, and that window closes the moment it is cut.

## Decision

1. **The stream reader leaves** -- the five public names and the private
   helpers that size a frame from its function code MUST NOT be part of this
   library. They ship from a separate, privately held package.
2. **The seam is the published surface** -- that package MUST reach this one
   only through names this one already exports. Nothing is made public to
   serve it, and no import crosses into a private helper.
3. **The codec keeps what is codec** -- reporting a PDU's size from the bytes
   received so far, reading an RTU frame without being told its direction, and
   the checksum helpers all stay. None of them reads a stream on its own.
4. **A tag bounds a withdrawal, a merge does not** -- a capability meant to be
   withheld MUST be withdrawn before the next release. A withdrawal MUST NOT
   be described as recalling what is already published, because it is not.

``` text
  this library, MIT, public        the separate package, private
  +---------------------------+    +----------------------------+
  | ModbusRtuPacket           |    | RtuSide                    |
  | ModbusPdu.expected_size   |<---| ModbusRtuSplitter          |
  | ModbusPduParser           |    | RtuSyncState               |
  | calc_crc16, validate_crc  |    | RtuSniffedFrame            |
  | ModbusPacketError         |    | ModbusRtuSniffer           |
  +---------------------------+    +----------------------------+
        every arrow lands on a name already in __all__
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep it here and relicense forward | One codebase, but it changes the terms under which every consumer of this library takes every other part of it. The reader is one capability; the licence is the whole surface |
| Keep the splitter free, sell the layer above | The splitter is the capability. What sits above it is a serial byte source, which is ordinary work anyone can write |
| Rewrite history so the commits never happened | Force-pushing is barred here, the repository is public, and a fetched commit is out regardless. It buys nothing and costs the history |
| Withdraw after the next release | The release is what publishes an installable artifact. Waiting turns a cheap removal into a permanent one |

## Consequences

- The five names stop resolving from `pyomb` and from `pyomb.packets`. Anyone
  who took them from `main` between 2026-09-07 and this record keeps them
  under MIT, which is a consequence and not a defect.
- Two decision records and one design-note section describe a component this
  repository no longer holds. They move with it.
- Thirty-three tests leave the suite. Every floor the gates assert survives
  the drop, measured before the cut: the fast tier holds 676 against a floor
  of 400, the gated doctests 40 against 30, and the decision records 53
  against 22.
- The separate package now carries a dependency this one cannot see. A change
  to how a PDU reports its size, or to how an RTU frame deserialises, breaks a
  consumer no gate here runs.
- `docs/design/design_notes.md` ends at section 26. A later section takes the
  next number, so the numbering carries a hole that is deliberate.

## Related

- Issue #383 carries the extraction and its acceptance criteria.
- Issue #231 asks for the serial byte source, which is the layer beneath the
  reader and stays open here.
