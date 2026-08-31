---
id: "031"
status: Accepted
date: 2026-08-30
category: protocol
supersedes: []
superseded_by: []
---

# ADR-031: Packet constraints are declared per class and queried, not a mode

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

### A constraint is not always a bound, and not always on a PDU

| Constraint | Shape | Carried by | Checked |
| --- | --- | --- | --- |
| FC3 quantity is 1 to 125 | a bound on one field | a PDU class | no |
| FC15 byte count is the quantity rounded up to whole bytes | a rule across fields | a PDU class | no |
| The protocol identifier is zero | a fixed value | `ModbusHeader` | no |
| The slave address is 1 to 247; 0 broadcasts, 248 to 255 are reserved | a bound on one field | the RTU ADU classes | no |
| The MBAP length matches the ADU received | a rule across parts | the TCP ADU classes | yes |

Four of the five are unchecked, and only two are bounds on a PDU field. So
scoping this to PDU field limits would leave the header and the slave address
out, and both carry constraints the specification states plainly.

`ModbusHeader`'s own docstring example passes `prot_id=2`, which no Modbus
frame may carry. Nothing rejects it.

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
| 1 | Every packet component declares its own constraints |
| 2 | Two methods: `violations()` returns findings, `validate()` raises |
| 3 | A component's findings include those of the parts it holds |
| 4 | `serialize()` never validates and gains no parameter |
| 5 | Enforcement is a caller's line at the transport boundary |
| 6 | There is no validation mode |

### 1. Constraints live on the class that carries the field

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

This is every packet component, not only the PDU classes. `ModbusHeader`
carries the protocol identifier, and the RTU ADU classes carry the slave
address. All of them descend from `ModbusPacketAbc`, so the methods below are
declared there and the header and ADUs are covered by construction:

```text
  ModbusPacketAbc            declares violations() and validate()
      +-- ModbusHeader       protocol identifier is zero
      +-- ModbusPdu          per-function-code bounds
      +-- the five ADUs      slave address, and the parts they hold
```

### 2. Two methods, and the name carries the contract

| Method | Returns | Caller |
| --- | --- | --- |
| `violations()` | findings; an empty tuple when clean | a test asserting which rule broke |
| `validate()` | nothing; raises `ModbusPacketError` when not clean | a client refusing to send |

`validate()` is one line over `violations()`. Both are needed because an
exception carries a message rather than data, and a raise stops at the first
problem. A test grading a peer needs the rule's identity, and a packet
breaking two rules should report two.

The naming follows the module's existing guards. `validate_crc` and
`validate_mbap_length` both raise, and all five of their call sites sit
inside `deserialize()`. A `validate` that returned a list instead would put
two opposite contracts under one verb.

### Why a method rather than a lookup

FC15 carries three fields the specification ties together:

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
        +--> pdu.validate()   raises when that tuple is not empty
        |
        +--> test:            assert the finding, send anyway, grade the peer
        +--> client:          call validate() before sending
        +--> serialize():     calls neither
```

### 3. A component reports for the parts it holds

An ADU holds a header and a PDU, and each of the three carries constraints of
its own. Asking the ADU returns all of them, so a caller has one question to
ask rather than three:

```text
  ModbusTcpRequest.violations()
        |
        +-- its own          the parts agree with each other
        +-- header's         the protocol identifier is zero
        +-- pdu's            the function code's own bounds
```

Without this a caller has to know the shape of what it holds, which is the
knowledge the classes exist to carry.

### 4 to 6. What stays out

Rule 4 makes the design note's rule 5 hold by construction, because no
parameter exists to pass wrongly. Rule 5 keeps validation out of the codec,
per CLAUDE.md 1.2. Rule 6 means a caller ignoring a finding filters the
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
  function code the library models, plus the header and the slave address, is
  the work; the check consumes it.
- Two constraints outside the PDU are named here and unchecked today: the
  protocol identifier must be zero, and the slave address runs 1 to 247 with
  0 broadcasting. Both are in scope for the work rather than a later ticket.
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
- `validate()` is the only path that raises, so the `ModbusError` subclass is
  constructed in one place rather than at each boundary that enforces.
- Two `validate` spellings now coexist: the module-level guards that
  `deserialize()` calls, and the method a caller calls. They agree on
  raising, which is what keeps the shared verb honest.
- Filtering a finding is a caller's decision with no record. A named
  relaxation would be a later decision, and takes its own record.

## Related

- #196 -- the field-range work this settles the mechanism for
- #224 -- the design note review, whose first finding this answers
- #229 -- whether the packing helper stays public, which the Context cites
- #232 -- the header docstring example this record's Context notes in passing
- ADR-009 -- the record that gave caller-supplied packing its own name
- `docs/design/design_notes.md` -- sections 10 and 25
