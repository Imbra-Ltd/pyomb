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
strict to be.

## Context

The codec checks two things today, both structural:

| Check | Covers |
| --- | --- |
| `validate_crc` | the RTU checksum |
| `validate_mbap_length` | the TCP header's declared length |

`grep -rn "def validate" src/pyomb/` returns those two and nothing else,
across 26 concrete classes. No function-code field limit is written down
anywhere in the tree.

The specification caps a Read Holding Registers quantity at 125. One past it
serializes without complaint:

```text
ModbusRequestFC3(start_addr=0, quantity=126).serialize()
  ->  030000007e
```

A real device answers that with exception code 03. The frame is well-formed,
its checksum is correct, and nothing in the library knows it is wrong.

### Two constraints, one of them already enforced

| Source | Constrains | Example | Enforced today |
| --- | --- | --- | --- |
| `PDU_FORMAT` | how wide the field is | `H` admits 0 to 65535 | yes, by `struct` |
| the specification | what value is allowed | FC3 quantity 1 to 125 | no |

The format cannot supply the second. Six request classes declare `">BHH"` --
FC1, FC2, FC3, FC4, FC5 and FC6 -- and the specification bounds them
differently:

```text
FC1 coils      quantity=2000  ->  01000007d0   legal
FC3 registers  quantity=2000  ->  03000007d0   sixteen times the cap
```

One format string, two bounds.

### What forces the decision now

| Proposal | Asks for |
| --- | --- |
| #196 | a check the caller requests per call |
| the design note, section 10 | three modes: STRICT, PERMISSIVE, RAW |

Both are held open by #224, pending a ruling.

The niche settles it. Faster Modbus implementations exist in compiled
languages, and this one earns its place by exercising them. The user story is
not "refuse to send this". It is "send this, and assert the device answers
exception 03", which needs the bound as data.

## Decision

| # | Rule |
| --- | --- |
| 1 | Each class declares its own bounds, beside `PDU_FORMAT` and `PDU_ID` |
| 2 | `violations()` is a method, so a class can override it |
| 3 | `serialize()` never validates and gains no parameter |
| 4 | Enforcement is a caller's line at the transport boundary |
| 5 | There is no validation mode |

### 1. Bounds live on the class

The declared bound is the only place the number appears. The docstring names
the constraint and points at it, rather than repeating the value:

```python
class ModbusRequestFC3(ModbusPdu):
    """Request FC3 PDU (Read Analog Outputs).

    Args:
        start_addr (int) : The starting address
        quantity (int)   : The registers to read; bounded, see LIMITS
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x0003
    LIMITS = {"quantity": (1, 125)}
```

A class the specification bounds in no way declares that explicitly, so a
reader can tell an unbounded field from an unwritten one.

### 2. Checking is a method

FC15 is the reason. It carries three fields the specification ties together:

| Field | Rule |
| --- | --- |
| `quantity` | 1 to 1968 |
| `byte_count` | the quantity, rounded up to whole bytes |
| `values` | exactly `byte_count` long |

A per-field lookup cannot express the second and third rows. FC16 and FC23
each carry their own version, so the base class covers the common shape and
an irregular class overrides it.

```text
  docs/specs/            the published bound
        |
        v
  ModbusRequestFC3       LIMITS on the class
  ModbusRequestFC15      overrides violations() for its cross-field rule
        |
        v
  pdu.violations()  ->  ()                 conforming
                    ->  (Violation(...),)  names the field and the bound
        |
        +--> test:         assert the finding, send anyway, grade the peer
        +--> client:       raise before sending
        +--> serialize():  does not call it
```

### 3 to 5. What stays out

Rule 3 makes the design note's rule 5 hold by construction, because no
parameter exists to pass wrongly. Rule 4 keeps validation out of the codec,
per CLAUDE.md 1.2. Rule 5 means a caller ignoring a finding filters the
returned tuple.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Three validation modes, as the design note proposes | The closest to a full answer, and it fails on PERMISSIVE. That mode allows values "useful for interoperability testing", which names no set a conformance suite can be written against. It also collapses a set of named limits into three ordinals, discarding what a peer-grading test asserts on: which rule broke. |
| `serialize(check=True)`, as #196 implies | A boolean flag parameter, which CLAUDE.md 2.2 bans. It answers whether to raise, when the caller's question is what is wrong with the frame. |
| Validate in the constructor | Catches the defect earliest and forfeits the product. A malformed packet must be a first-class object, and a constructor that refuses one makes the library unable to build the frames it exists to send. |
| An enum of modes, per the upstream rule against boolean flags | The upstream rule is right about behaviour switches and wrong here. An enum answers "how strict"; the caller asks "which bound did this cross". This is the divergence the Upstream line records. |
| One central table of bounds, recorded once rather than per class | What #196's first acceptance criterion asks for, and what earlier revisions of this record decided. It de-duplicates nothing real: FC3 and FC4 both cap at 125, which is two statements in the specification that agree rather than one fact written twice. It also cannot hold a rule spanning fields, so FC15, FC16 and FC23 would each need a second mechanism beside it. |
| Read the limits off `PDU_FORMAT` | The most appealing option, since the format is already the class's statement about its own layout and needs no new data. It gives field width and stops there, and the Context table above shows why that is not the same constraint. |
| Repeat the bound in the docstring and add a drift guard | Puts the number where the reader already is, at the price of writing it twice and a test to keep the copies honest. Rejected in favour of one source: the guard is cheap, and a fact stored once cannot drift at all. |
| Close #196 as wontdo, keeping only the checksum and length checks | Honest about the current state, and it leaves the specification's limits written down nowhere. A conformance test would then hardcode 125 at each call site, which is the third copy this project's own rules call a bug. |

## Consequences

- The deliverable is the reading. Going through the specification for every
  function code the library models is the work; the check consumes it.
- Two of #196's acceptance criteria move: its first, which asks that the
  limits be recorded once rather than per class, and its third, which asks
  that a caller be able to request the check.
- A reader learns the number from `LIMITS` rather than from the docstring.
  That is the price of one source, taken deliberately.
- Nothing about the wire output changes and no existing signature moves. The
  suite's fixed vectors are untouched.
- A caller who never calls `violations()` gets today's behaviour exactly, so
  the check earns nothing until a client or a test consumes it.
- The finding type is a new public surface. It needs a docstring stating its
  contract and an entry in `__all__`, like any other export.
- Filtering a finding is a caller's decision with no record. A named
  relaxation would be a later decision, and takes its own record.

## Related

- #196 -- the field-range work this settles the mechanism for
- #224 -- the design note review, whose first finding this answers
- #229 -- whether the packing helper stays public, which the Context cites
- ADR-009 -- the record that gave caller-supplied packing its own name
- `docs/design/design_notes.md` -- sections 10 and 25
