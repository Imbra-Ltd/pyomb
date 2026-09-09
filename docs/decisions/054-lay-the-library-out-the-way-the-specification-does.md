---
id: "054"
status: Accepted
date: 2026-09-09
category: repository
supersedes: []
superseded_by: []
---

# ADR-054: Lay the library out the way the specification does

**Upstream:** filed as `none`. With the domain skin off: a package split
that was previously justified by size alone is revisited once real
independence between its parts is measured, rather than waiting for
another size threshold.

## Context

Two files carry most of the codec: `packets/pdu.py` at 3270 lines and
`packets/framing.py` at 1001 lines. Both grew inside the split a prior
record ratified on size and import direction, and neither has been
touched since for cohesion.

### What the tree holds, measured today

| Claim | Command | Result |
| --- | --- | --- |
| Function-code pairs never reference each other | `grep -n "ModbusRequestFC\d+(\|ModbusResponseFC\d+("` over `pdu.py`, read by hand | Every hit is a class's own definition or its own docstring example |
| TCP and RTU classes never reference each other | `grep -n "ModbusRtuPacket\|ModbusTcpPacket\|..."` over `framing.py`, read by hand | Same result: each side names only itself |
| Both sides share one dependency | `grep -n "^from pyomb" framing.py` | `pdu` and `base`, nothing from the other transport |
| The specification's own function-code groups | Modbus Application Protocol v1.1b3 | Bit access, register access, diagnostics, encapsulated interface |

Thirteen function codes exist: 1, 2, 3, 4, 5, 6, 7, 8, 15, 16, 22, 23, 43.
Grouped by what each one addresses: 1, 2, 5, 15 read or write a single bit;
3, 4, 6, 16, 22, 23 read or write a register; 7, 8 are diagnostics; 43 is
the encapsulated interface transport (device identification). No pair
crosses that grouping to reach another pair's fields or classes.

### The rule this measurement answers

A corrected record refuses a specification's own vocabulary as sufficient
grounds for a split -- a name is not a seam. It also states what a seam
is: a module's size, the direction of its imports, or a cohesion boundary
a reader can point at. The independence measured above is that third
kind, found independently of what the specification calls the groups it
falls into. The vocabulary and the seam agree here; only the seam is
what authorizes the split.

### What forces the decision now

Two features wait on this layout: a data store a server-side scripted
handler can read and write, and file-record function codes. Both add
classes to whichever file already holds their group, and adding them to
a 3270-line file makes the next reader's job strictly harder each time.
Issue #413 is the epic collecting the split; issues #405 to #412 are its
tasks.

## Decision

```text
  before                              after

  packets/                            pdu/
    base.py     (violations,            common.py    (violations,
                  abstract bases,                       abstract bases,
                  shared PDU/parser)                     shared PDU/parser)
    pdu.py       (13 FC pairs)          bits.py        (FC1 FC2 FC5 FC15)
    framing.py   (header, CRC,          registers.py   (FC3 FC4 FC6 FC16
                  TCP+RTU ADUs)                          FC22 FC23)
                                        diagnostics.py (FC7 FC8)
  stream.py                            encapsulated.py(FC43)
  tls.py
                                       adu/
  client_simulator.py                   tcp.py  (header, MBAP length,
  server_simulator.py                            TCP request/response)
                                         rtu.py  (CRC, RTU request/
                                                   response/packet)

                                       transport/
                                         stream.py  (moved, unsplit)
                                         tls.py     (moved, unsplit)

                                       simulators/
                                         client_simulator.py (moved)
                                         server_simulator.py (moved)
```

1. **Four packages, one per specification concept.** `pdu` holds the
   protocol data unit -- the message itself, independent of how it
   reaches the wire. `adu` holds the application data unit -- the
   envelope a transport puts around a PDU, one file per envelope kind.
   `transport` holds every module that opens a socket or builds a TLS
   context. `simulators` holds the client and server built on the other
   three. Nothing depends on `simulators`; `transport` and `adu` both
   depend on `pdu`; `pdu` depends on neither.
2. **The shared codec base moves with the PDU it exists for.**
   `ModbusViolation`, `ModbusPacketAbc` and `ModbusPduParserAbc` --
   today's `packets/base.py` -- move into `pdu/common.py` alongside
   `ModbusPdu`, `ModbusPduParser` and `ModbusError`. The ADU classes
   already depend on the PDU classes to hold one, so importing the
   shared base from the same package adds no new edge to the graph.
3. **Neither `pdu` nor `adu` imports a socket, a TLS context, or
   anything from `transport` or `simulators`.** This narrows the
   existing codec rule from one package to two, and is the rule
   task #410 gives an automated check.
4. **`stream.py` and `tls.py` move into `transport/` without being
   split internally.** The prior record settled that a channel/transport
   split inside `stream.py` waits for a second transport landing under
   #231, which stays out of scope here. Moving the file changes nothing
   about what is inside it.
5. **`client_simulator.py` and `server_simulator.py` move into
   `simulators/` without being renamed.** Both names already describe
   what they hold; only their directory changes.
6. **Every old import path keeps working through 0.8.0.** The eight paths
   are: `pyomb.packets`, `pyomb.packets.base`, `pyomb.packets.pdu`,
   `pyomb.packets.framing`, `pyomb.stream`, `pyomb.tls`,
   `pyomb.client_simulator` and `pyomb.server_simulator`. Each becomes a
   forwarding module: it imports the names it used to define from their
   new home and re-exports them, and it raises `DeprecationWarning` naming
   the new path on import. A consumer's `isinstance` and identity checks
   are unaffected, because the forwarding module binds the same class
   object, not a copy.
7. **The forwarding modules are deleted in 0.9.0.** 0.8.0 is the first
   release to carry the new layout. #412 removes the eight files above and
   their entries in the release that follows it. That task is deliberately
   not part of this epic's definition of done.
8. **The public API surface at `pyomb` itself is unchanged.** Every name
   `pyomb/__init__.py` re-exports today keeps resolving from the same
   `import pyomb; pyomb.Name` and `from pyomb import Name` forms; only
   the module that defines each name moves.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep `pdu` and `adu` nested under a renamed `codec/` package | Closest to today's shape, and it contradicts the epic's own naming: four folders are named, not three, and #410 checks "the pdu or adu folders" by name. A nested pair reads as one package with two files, not two packages. |
| Split by request/response instead of by specification group | Doubles the file count for no cohesion gain -- a request and its response already share nothing that crosses into a different function code -- and loses the property that makes the split readable: a reader who knows the specification's grouping finds a function code by group, not by direction. |
| `sys.modules` aliasing for the old paths, instead of forwarding modules | Works without a physical file, and it is not what a static analysis tool, an IDE's go-to-definition, or a package installer see -- `pyomb.packets.pdu` would exist at runtime and not on disk, which is a stranger failure mode than a shim file for anyone debugging an import. |
| No compatibility period; break the old paths at 0.8.0 | Cheapest to build. The distribution reaches no package index and ships as release artifacts only, so this trades a known consumer inconvenience for a smaller diff, and the project's own established pattern (the simulator rename, the error-suffix rename) is one release of both names. |
| Move `errors.py`, `defines.py` and `logger.py` into `pdu/` too | The epic explicitly rules out renaming `errors.py`, and `defines.py`/`logger.py` are read by every one of the four new packages plus the shims -- moving them under `pdu` would make `adu`, `transport` and `simulators` reach into a sibling package for constants and logging, which is a worse graph than leaving three small flat modules at the root. |

## Consequences

- `CLAUDE.md` 1.2 names `pdu` and `adu` in place of "the codec package",
  since the rule it states -- wire code does not import a socket -- now
  binds two packages rather than one.
- The README "Project structure" section, updated once per task as each
  package lands, ends the epic naming eight new files and four fewer
  flat ones under `packets/`.
- `docs/PLAYBOOK.md` 2.1 ("Add a function code") names the group file a
  new function code's grouping puts it in, rather than one shared
  `pdu.py`.
- Eight forwarding modules exist between 0.8.0 and 0.9.0. Each is a
  standing maintenance cost with a known removal date; #412 already
  tracks it and does not wait on a trigger to be found, only on the
  release after 0.8.0 entering preparation.
- A consumer importing `pyomb.packets.pdu.ModbusRequestFC1` today keeps
  that import working, unmodified, through 0.8.0, and sees one
  `DeprecationWarning` naming `pyomb.pdu.bits` the first time they do.
- The measured independence in Context is what a later split needs to
  repeat, not what this one alone establishes going forward. A ninth
  function code added to `pdu/registers.py` that reaches into
  `pdu/bits.py` would erode the same property this record measured, and
  nothing here checks for that automatically.

## Related

- ADR-035 -- the record whose three-package rule this narrows to four
- ADR-051 -- the record that ratified the split this one measures against
  and requires a measurement of any split that follows it
- ADR-038 -- the simulator rename that established the forwarding-module
  pattern this record reuses for whole modules rather than single names
- ADR-009 -- the fixed `serialize`/`deserialize` signature every moved
  PDU and ADU class keeps
- Issue #413 -- the epic this record opens
- Issues #231, #391 -- the serial-line work this record's scope excludes
