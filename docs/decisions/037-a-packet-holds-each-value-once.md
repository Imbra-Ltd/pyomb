---
id: "037"
status: Accepted
date: 2026-09-01
category: protocol
supersedes: []
superseded_by: []
---

# ADR-037: A packet holds each value once, and the payload is a view

**Upstream:** filed as `none`. With the domain skin off: where an object
stores the same information twice and serializes only one copy, the fix is to
delete the copy rather than keep the two in step. Synchronising is the
tempting answer and it leaves both copies, so the next writer to miss one
reopens the defect. One project reaching that once is not evidence it
generalizes; revisit if a second does.

## Context

Every concrete packet class stored each value twice: as the named attribute a
caller reads and writes, and as a combined payload built once in the
constructor. Only the payload was serialized.

```text
  ModbusRequestFC3(start_addr=0, quantity=10)
  request.quantity = 0x07D1

  request.quantity      0x7d1        the packet says 2001
  request.serialize()   030000000a   the bytes still say 10
```

Probing all 26 request and response classes by mutating each named field and
re-serializing: 25 store twice. The 26th carries no named field at all rather
than keeping one copy.

Equality broke on the same cause. Packet equality compares the instance
dictionary, which held both copies, so a packet whose field was changed did
not equal one built with the new value.

### What forces the decision now

Nothing in the library mutates a packet after construction, so no current
behaviour was wrong. That changes the moment a mutation feature exists, and
the review of the architecture direction note put mutation on the roadmap.
The defect had to be fixed before the feature that would fire it, not after.

### Why synchronising is the wrong shape

The obvious repair is to update the payload whenever a named field is
written. It works, and it leaves two copies in the object. Every future
constructor, every `deserialize`, and every later field added to a class then
carries an obligation nothing checks, and the failure is silent in exactly
the way this one was.

## Decision

| # | Rule |
| --- | --- |
| 1 | The named fields are the single source; the payload is derived |
| 2 | A class declares its fields in wire order as `PDU_FIELDS` |
| 3 | A layout ending in a sequence names that field as `PDU_TAIL` |
| 4 | Assigning the derived payload raises, naming the fields to set |
| 5 | The generic PDU declares no fields and stores its payload |
| 6 | A trailing sequence is canonicalised to a tuple at construction |

### 1 to 3. The class states its own shape

```text
  class ModbusRequestFC3          class ModbusResponseFC3
      PDU_FORMAT = ">BHH"             PDU_FORMAT = ">BB{0}H"
      PDU_FIELDS = (                  PDU_FIELDS = ("byte_count",)
          "start_addr",               PDU_TAIL   = "values"
          "quantity",
      )
                    |                               |
                    v                               v
      data -> (start_addr,            data -> (byte_count,) +
               quantity)                       tuple(values)
```

The payload is computed on every read, so a field changed after construction
reaches the wire. Deleting the second copy is also what repairs equality: a
property lives on the class, so the payload leaves the instance dictionary
and only the named fields remain to compare.

### 4. The derived view is not writable

Assigning the payload on a class that derives it raises, and the message
names the fields to set instead. There is nothing correct such an assignment
could do: accepting it would either be discarded on the next read or
reintroduce the copy this record removes.

This is a break in the public surface, taken deliberately. The alternative is
an assignment that silently does nothing, which is the failure mode the whole
record exists to end.

### 5. The generic PDU is the exception, and says so

A class modelling no function code has no named fields to read, so it stores
what it was given. It declares that rather than inheriting it, because an
inherited empty declaration cannot be told apart from a class nobody has
looked at.

### 6. One packet, not two that serialize alike

A trailing sequence is stored as a tuple whatever the caller passed. Without
it a packet built from a list and one built from a tuple compare unequal
while emitting identical bytes, which is the equality defect in a second
form.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Update the payload whenever a named field is written | The smallest diff and the one most likely to be reached for. It keeps both copies, so every later constructor and every new field carries an unchecked obligation, and the failure stays silent. |
| Keep the payload writable and distribute an assignment back into the named fields | Preserves the existing surface, which is worth something. It also has to split a flat payload across scalars and a tail, guess where the boundary is for an irregular class, and answer what a partial assignment means. |
| Make the payload the source and derive the named fields | Symmetric, and it inverts which half is authoritative. The named fields are what the specification names, what the docstrings document and what a caller sets, so deriving them from a flat tuple would put the readable half downstream of the opaque one. |
| Freeze the packet so no field can change after construction | Removes the defect entirely and forfeits the product. Mutation is a roadmap feature for a library whose purpose is exercising other implementations, so an immutable packet is the wrong object. |
| Leave it until mutation is built | Defensible, since nothing in the library mutates a packet today. It leaves a defect that reproduces from the public surface and would then have to be fixed under a feature rather than on its own. |

## Consequences

- Assigning the payload is a break. A caller doing it got no effect before
  and gets an error now, which is the intended direction and is still a
  break in a public surface.
- A class added later must declare its fields or inherit the storing
  behaviour silently. A test asserts every concrete class declares its own,
  and it caught the generic PDU failing exactly that on first run.
- The payload is computed per read rather than once per construction. For a
  library whose frames are tens of bytes this is not worth measuring, and
  it is a real change in where the cost sits.
- A trailing sequence comes back as a tuple even when a list went in. That
  is visible to a caller reading the field back.
- Nothing on the wire changes. The per-function-code suites assert their
  frames against the published vectors and were untouched.
- The declaration mechanism this establishes is what the constraint work
  reused for its own per-class bounds, so the two read alike on the page.

## Related

- Issue #228 -- the defect this record answers
- Issue #229 -- the raw-bytes payload the generic PDU's storing case serves
- Issue #224 -- the direction-note review that put mutation on the roadmap
- ADR-031 -- the record whose per-class declarations follow the same shape
- ADR-036 -- the record covering what the stored payload accepts
