---
id: "031"
status: Accepted
date: 2026-08-30
category: protocol
supersedes: []
superseded_by: []
---

# ADR-031: Field limits are queryable data, not a validation mode

**Upstream:** filed as braboj/solid-ai-templates#1293 against
`templates/base/core/quality.md`. With the domain skin off: the rule against
boolean flag parameters prescribes an enum, and an enum is the wrong shape
when the caller needs to know which named constraint fired rather than how
strict to be. A mode collapses a set of named limits into one ordinal and
discards the names.

## Context

The codec validates two things, both structural. `validate_crc` checks the
RTU checksum and `validate_mbap_length` checks the TCP header's declared
length. `grep -rn "def validate" src/pyomb/` returns those two and nothing
else, across 26 concrete request and response classes.

No function-code field limit is written down anywhere in the tree. The
Modbus Application Protocol specification caps a Read Holding Registers
quantity at `0x07D0`; one past it serializes without complaint:

```text
ModbusRequestFC3(start_addr=0, quantity=0x07D1).serialize()
  -> 03000007d1
```

A real device answers that request with exception code 03. The frame is
well-formed, its CRC is correct, and nothing in the library knows it is
wrong.

One case behaves differently, and #196 lists it as unvalidated when it is
not. A starting address above `0xFFFF` does not serialize -- `struct.pack`
refuses the `>H` field and the error surfaces as a `ModbusPacketError`
naming struct.

So the tree already refuses some out-of-range values, for the wrong reason
and with a message that names the packer rather than the constraint.

A concrete class cannot build that field at all, and the reason is
arithmetic rather than a missing feature: `0x1FFFF` does not fit the sixteen
bits the specification gives the field. Widening it produces a different
frame, and the generic PDU already builds one -- `pack(">BIH")` emits
`030001ffff0001`, as does handing the same bytes to `ModbusPdu` as data.
Neither route needs anything this record adds.

What forces the decision now is that two open proposals answer this
differently. #196 asks for a check the caller can request per call. The
design note under `docs/design/` proposes three validation modes -- STRICT,
PERMISSIVE and RAW -- and its rule 5 says serialization must not imply
validation. #224 holds both open pending a ruling.

The library's niche decides it. Faster Modbus implementations exist in
compiled languages, and this one earns its place by exercising them. The
primary user story is therefore not "refuse to send this" but "send this and
assert the device answers exception 03". For that a test needs the limit as
data, so it knows which verdict to demand.

## Decision

Five parts, one concern: how the specification's field limits enter the
library.

1. **The limits are a table.** Each entry names a function code, a field, its
   bound and the clause of the Modbus Application Protocol specification that
   sets it. The table is recorded once, not per class, and a class carrying no
   bounded field has an empty entry rather than no entry.

2. **Inspection is a pure function returning named findings.** A module-level
   `violations(pdu)` beside the existing validators returns a tuple of
   findings, empty for a conforming PDU. It raises nothing, reads no
   configuration and takes no flag.

3. **Serialization never validates.** `serialize()` gains no parameter. The
   design note's rule 5 then holds by construction, because there is no
   default to argue about and no argument to pass wrongly.

4. **Enforcement is a caller's line at the boundary.** A client or server that
   wants production strictness raises a specific `ModbusError` subclass on a
   non-empty result before sending. That code lives in the transport and
   simulator layers, never in the codec, per CLAUDE.md 1.2.

5. **There is no validation mode.** No STRICT, PERMISSIVE or RAW setting, and
   no object to hang one on. A caller wanting to ignore a class of finding
   filters the returned tuple.

```text
  docs/specs/          the published bound
        |
        v
  LIMITS table         one entry per bounded field, with its source
        |
        v
  violations(pdu)  ->  ()                  conforming
                   ->  (Violation(...),)   names the field and the bound
        |
        +--> test:    assert the finding, send anyway, grade the peer
        +--> client:  raise before sending
        +--> serialize(): does not call it
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Three validation modes, as the design note proposes | The closest to a full answer, and it fails on PERMISSIVE. That mode is defined as allowing values "useful for interoperability testing", which names no set a conformance suite can be written against. It also collapses a table of named limits into three ordinals, discarding the one thing a peer-grading test asserts on -- which rule broke. |
| `serialize(check=True)`, as #196 implies | A boolean flag parameter, which CLAUDE.md 2.2 bans for the usual reason. It also answers the wrong question: whether to raise, rather than what is wrong with the frame. |
| Validate in the constructor | Catches the defect earliest and forfeits the product. A malformed packet must be a first-class object, and a constructor that refuses one makes the library unable to build the frames it exists to send. |
| An enum of modes, per the upstream rule against boolean flags | The upstream rule is right about behaviour switches and wrong here. An enum answers "how strict", and the caller's question is "which bound did this cross". This is the divergence the Upstream line records. |
| Close #196 as wontdo and keep only CRC and length checks | Honest about the current state, and it leaves the specification's limits written down nowhere. A conformance test would then hardcode `0x07D0` at each call site, which is the third copy this project's own rules call a bug. |

## Consequences

- The deliverable is the table, not the check. Sizing the work means reading
  the specification for every function code the library models, and the check
  is a thin consumer of what that reading produces.
- #196 becomes implementable without the rest of #224. Its acceptance criteria
  survive almost verbatim; only the mechanism named in its third criterion
  changes, from a check the caller requests to a function the caller calls.
- #196's premise is corrected in one place. An over-wide starting address is
  already refused, so the work covers the fields that fit their struct format
  and cross a specification bound.
- Nothing about the wire output changes, and no existing signature moves. The
  suite's fixed vectors are untouched.
- A caller who never calls `violations` gets today's behaviour exactly. That
  is deliberate, and it means the check earns nothing until a client or a test
  consumes it.
- The finding type is a new public surface, so it needs a docstring stating
  its contract and an entry in `__all__` like any other export.
- Filtering a finding is a caller's decision with no record. Where a project
  wants a named relaxation, that is a later decision and takes its own record.

## Related

- #196 -- the field-range work this settles the mechanism for
- #224 -- the design note review, whose first finding this answers
- #229 -- whether the packing helper stays public, which the Context cites
- ADR-009 -- the record that gave caller-supplied packing its own name. The
  capability predates it; what it changed is which name carries it
- `docs/design/design_notes.md` -- sections 10 and 25, the modes proposal and
  the rule this keeps
