---
id: "036"
status: Accepted
date: 2026-09-01
category: protocol
supersedes: []
superseded_by: []
---

# ADR-036: The payload takes bytes, and the format string is retired

**Upstream:** filed as `none`. With the domain skin off: where a library
offers two ways to express the same thing and documents the narrower one,
the fix is to document the wider one and retire the other, not to explain
the difference. That is one project's experience once; revisit if a second
repository reaches the same shape.

## Context

A caller building a frame this library models no class for had two routes,
and they produced identical bytes:

```text
  documented    ModbusPdu(fc=1, data=(1, 2, 3, 4)).pack(">BHBHB")
  undocumented  ModbusPdu(fc=1, data=struct.pack(">HBHB", 1, 2, 3, 4))
                                                    both -> 01000102000304
```

The documented route is the weaker of the two. A format string describes
only the layouts `struct` knows how to write. Bytes carry any sequence at
all, which is what a library for putting arbitrary frames on the wire is
for.

### What the undocumented route was missing

It worked on the wire and was second class everywhere else. The `data`
argument was documented as a tuple and never mentioned bytes. Reading a
packet back always produced a tuple, so a packet built from bytes did not
equal the packet read from its own output:

```text
  p = ModbusPdu(fc=1, data=b"\x12\x34")
  q = ModbusPdu.deserialize(p.serialize())

  p.serialize() == q.serialize()   True    same frame
  p == q                           False   different types inside
```

### What forces the decision now

Mutation. The change that single-sourced each packet's named fields makes
a value writable, and the direction that follows is a packet edited past
what its class promises -- a truncated field, a duplicated byte, a widened
one. Such a packet cannot stay its class. It becomes a plain container of
bytes, and that container wants bytes rather than a format string.

### What the helpers are actually used for

Measured on the tree this record lands in:

| Call site | Count |
| --- | --- |
| `self._pack(` in `packets.py` | 27 |
| `cls._unpack(` in `packets.py` | 1 |
| Outside `packets.py` in `src/` | 0 |
| In the test suite | 5, across two modules |

So the helper is overwhelmingly internal. It is the shared code every
packet class builds its own bytes with, and only incidentally an escape
hatch a caller reaches for.

## Decision

| # | Rule |
| --- | --- |
| 1 | `data` accepts bytes, documented, and holds them as their byte values |
| 2 | The packing helpers are internal, named `_pack` and `_unpack` |
| 3 | `pack` and `unpack` survive as deprecated wrappers, removed in 0.6.0 |
| 4 | A tuple payload is unchanged |

### 1. Bytes are held as the tuple of their byte values

A payload given as `bytes` or `bytearray` is stored as the tuple of its
byte values, which is the form `deserialize()` already produces. Holding
the two apart is what made a packet unequal to itself across a round trip.

The normalisation is lossless here. The generic PDU's format is one byte
per element, so a tuple of byte values and the bytes themselves describe
the same frame. A class declaring named fields derives its payload and
takes neither.

### 2 and 3. Internal, with the old names kept for one release

```text
  the packet classes  ---->  _pack / _unpack     internal, 28 call sites
                                   ^
  a caller            ---->  pack / unpack       deprecated, warns, 0.6.0
                      ---->  data=b"..."         supported
```

The helpers keep their behaviour and lose their public names. The old
names stay for one release as wrappers that warn and delegate, because
the escape hatch is documented and a consumer using it would otherwise
meet an `AttributeError` far from the cause.

The wrappers warn; the internal calls do not. A packet built through the
ordinary path emits nothing, which is pinned by a test -- a warning naming
a route the caller never took would be worse than no warning at all.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Remove the public names outright | What the issue asked for, and one line smaller. A documented escape hatch removed without warning surfaces as an `AttributeError` in consumer code, and this project ships to consumers it cannot enumerate. One release of warning costs a wrapper. |
| Keep them public and document bytes as well | The smallest change, and it leaves two supported routes to one outcome with the weaker one still documented. That is the state this record exists to end. |
| Hold bytes as bytes rather than normalising | Preserves exactly what the caller passed, which is the appealing part. Equality then has to compare frames rather than values, which is a change to every packet class to fix a case only the generic one has. |
| Make the payload bytes-only, converting tuples on the way in | The cleanest model, and it breaks every existing caller and 26 class constructors for no gain the wire can see. |
| Defer until mutation is built | Honest about what forces it, and it leaves the round-trip defect standing meanwhile. The container is needed whether or not mutation lands next. |

## Consequences

- A packet built from bytes now equals the packet read back from its own
  output. That case was broken and is the round trip a caller assumes.
- Two names are deprecated and dated. Nothing enforces the 0.6.0 removal
  except a person reading this record or the warning text.
- The five test call sites move to the supported route. One of them read
  its payload back as four mixed-width fields and now reads six byte
  values, because the widths were never in the bytes -- the assertion
  changed to say so rather than being deleted.
- A caller who passes bytes and reads `data` back gets a tuple. The input
  is wider than the stored form, which is visible and deliberate.
- The claim that the packing helpers are public no longer holds. The
  record that gave them their own name keeps its other two decisions,
  which are the signature contract and the required format argument, so
  it stands rather than being superseded.
- Nothing on the wire changes. The per-function-code suites assert their
  frames against the published vectors and are untouched.

## Related

- Issue #229 -- the two-routes defect this record answers
- Issue #228 -- the single-sourcing change that makes mutation reachable
- ADR-009 -- the record that gave caller-supplied packing its own name
- `docs/design/design_notes.md` -- section 11, on packet mutation
