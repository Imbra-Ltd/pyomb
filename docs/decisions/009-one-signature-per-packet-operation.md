---
id: "009"
status: Accepted
date: 2026-08-19
category: protocol
supersedes: []
superseded_by: []
---

# ADR-009: One signature per packet operation

**Upstream:** filed as braboj/solid-ai-templates#1033 against
`templates/base/core/quality.md`. With the domain skin off, the convention is
that a variadic parameter on an abstract operation is not a contract but a
licence. It type-checks against every subclass and constrains none, so the
divergence it permits is only ever found by a checker looking somewhere else.

## Context

#6 records 123 `[override]` findings from the mypy gate, frozen under ADR-005
rather than fixed. 122 of them are in `packets.py`, and they are not missing
annotations — they are Liskov violations that surface once the checker looks
inside unannotated functions.

The hierarchy declares two operations three times, and no two declarations
agree:

```text
  ModbusPacketAbc     serialize(self, **kwargs)
                      deserialize(self, stream, **kwargs)      <- instance method
          |
  ModbusPdu           serialize(self, fmt=None)
                      deserialize(cls, stream, fmt=None)       <- classmethod
          |
  ModbusRequestFC1    serialize(self)
  (and 25 siblings)   deserialize(cls, stream)                 <- classmethod
```

Each step narrows what the one above promised. A caller holding a
`ModbusPacketAbc` cannot call either operation without knowing the concrete
class it really has, which is the abstraction inverted: the base exists so the
caller does not have to know.

Two separate defects produce the 122:

1. `**kwargs` on the base. It absorbs any argument, so every subclass that
   accepts fewer is a narrowing. A variadic in a base class states no contract
   a subclass can honour or break — it only guarantees the call compiles.
2. `fmt` on `ModbusPdu`. The generic PDU is fc-plus-data with no fixed layout,
   so a caller-supplied format is genuinely part of what it offers. A concrete
   PDU's layout is fixed by the Modbus specification, and honouring a
   caller-supplied format there would emit a frame a real device rejects. The
   26 concrete classes drop the parameter, which is the correct behaviour
   expressed as a broken promise.

The second defect is the interesting one. The subtyping is not wrong and the
concrete classes are not wrong; the promise is. `ModbusPdu` offers a capability
its own subtypes must not offer, and it offers it through the same name the
abstraction uses.

The third declaration of `deserialize` is a plain error: the base declares an
instance method, and every one of the 34 implementations is a classmethod.
Deserializing constructs an instance, so it cannot require one first. Nothing
ever called it as declared.

## Decision

Three decisions, one concern: what signature a packet operation is called
through.

1. **The contract is `serialize(self)` and `deserialize(cls, stream)`.** The
   base declares both without a variadic, and `deserialize` as an abstract
   classmethod, which is what all 34 implementations already were.

2. **The format escape hatch gets its own name.** `ModbusPdu` keeps
   caller-supplied packing as `pack(self, fmt)` and `unpack(cls, stream, fmt)`.
   These are public — a PDU shape the library does not model is a real need,
   and the tests exercise it — but they are no longer overrides of anything,
   so a subclass declining to offer them breaks nothing.

3. **`fmt` is required where it appears.** `pack` and `unpack` take the format
   positionally with no default, rather than falling back to the class default
   on a falsy value as `serialize(fmt=None)` did. A caller reaching past the
   class default and passing an empty format now gets an error naming what
   struct rejected, not a silent frame built from the default they were
   reaching past.

```text
  ModbusPacketAbc     serialize(self)              -- one contract,
                      deserialize(cls, stream)        declared once

  ModbusPdu           serialize(self)  ------------> pack(self, fmt)
                      deserialize(cls, stream) ----> unpack(cls, stream, fmt)
                                                     the escape hatch, under
                                                     its own name

  ModbusRequestFC1    serialize(self)   ----+
  (and 25 siblings)   deserialize(cls, stream)  calls pack() with the format
                                                the specification fixes
```

The uniformity is pinned by `tests/test_packet_signature_contract.py`, which
enumerates every packet class and asserts the shape of both operations, rather
than by the mypy freeze. The freeze records what a checker found on one day;
the test states what the hierarchy is for.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Push `fmt=None` down to all 34 implementations | Removes the divergence without an API break, and hands every concrete PDU a format override. A caller could then ask `ModbusRequestFC1` for a frame FC1 does not have, which is the class of defect the protocol rules in `CLAUDE.md` exist to prevent. A wider contract is not the same as a correct one. |
| Widen the base to `**kwargs` everywhere | Makes the checker quiet by making the contract vacuous. Every subclass would accept arguments it silently ignores, which is worse than the divergence: a caller's typo becomes a no-op instead of a `TypeError`. |
| Leave it frozen and close #6 as wontdo | The freeze is honest about what it holds, but it holds a defect the abstraction exists to prevent. ADR-005 calls shrinking the freeze the migration; this is that, for the one code where the findings were not missing annotations. |
| Delete the 26 concrete `serialize` overrides and drive everything from `PDU_FORMAT` | The cleanest hierarchy of the options, and out of scope. Each override wraps its errors with a message naming its function code, so deleting them changes what every serialization failure reports. That is a diagnostics decision, not a signature one. |
| Keep `fmt` with its falsy-value fallback | `templates/base/core/config.md` rules against exactly this: a source present but empty must be an error naming the accepted input, never a fallback to the default the caller was reaching past. The old behaviour treated `""` as "not specified". |

## Consequences

- `ModbusPdu.serialize(fmt=...)` and `ModbusPdu.deserialize(stream, fmt=...)`
  no longer accept a format. This is a breaking change to a public signature,
  taken at `v0.1.0` where SemVer permits it in a minor bump. Five call sites in
  the test suite moved to `pack` and `unpack`; no other module in the tree
  passed a format.
- The mypy freeze loses `override` for `pyomb.packets`. `pyomb.stream` keeps
  it for one unrelated finding, so the two modules no longer share an entry.
  Total findings behind the freeze fall from 711 to 593.
- The wire output is unchanged. `serialize()` resolves the same format string
  it always did and hands it to the same `struct.pack` call; the fixed-vector
  tests for every function code pass untouched.
- A future packet class is held to the contract by a test rather than by
  review. The test fails on a re-introduced variadic, on a `deserialize`
  declared as an instance method, and on any parameter added to `serialize`.
- `run_once` in `stream.py` narrows away from `ModbusSenderAbc` in the same
  shape, and is not covered here. It is a different abstraction in a different
  module, and #45 tracks it.
- The socket assignment finding that #6 also recorded is not covered here
  either. Annotating the attribute as optional turns 14 attribute accesses into
  new findings under a code the freeze does not carry, so it is its own scope;
  #46 tracks it.

## Related

- ADR-005 — the mypy freeze this shrinks, and the rule that shrinking it is the
  migration
- #6 — the `[override]` cluster, which this closes
- #45 — the same narrowing in the sender hierarchy
- #46 — the client's optional socket attribute
