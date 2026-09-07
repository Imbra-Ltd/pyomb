---
id: "052"
status: Accepted
date: 2026-09-07
category: protocol
supersedes: []
superseded_by: []
---

# ADR-052: An RTU reader is told which side it decodes

**Upstream:** filed as `none`. With the domain skin off: where a stream
format is not self-delimiting and its type tag does not encode direction,
a reader takes the direction from its construction rather than inferring
it per message. The pattern is thin on its own, and one project meeting
it is not evidence it generalizes.

## Context

An RTU frame carries no length. A reader splitting a serial stream has to
size each frame from its content, which means asking the class that models
the function code how long its frame is. That question needs to know
whether the frame is a request or a response.

The function code cannot answer it. The Modbus Application Protocol
v1.1b3 says of a normal response that the server "simply echoes to the
request the original function code", so the byte is identical in both
directions. Only an exception response differs, carrying the code with its
most significant bit set.

The two directions size differently, so the ambiguity is not academic:

```text
  wire byte 0x03
    as a request    >BHH        fixed, 5 bytes
    as a response   >BB{0}H     2 bytes plus the byte count it declares
```

Reading a response as a request takes 5 bytes where the frame is longer,
so the checksum fails at that boundary and the reader resynchronises onto
the middle of a frame.

### What the tree holds, measured today

| Claim | Command | Result |
| --- | --- | --- |
| The parser adds the direction | `grep -n "0x8000" src/pyomb/packets/pdu.py` | the response lookup is `func_code + 0x8000` |
| Eight layouts carry a count | `grep -c "PDU_COUNT = " src/pyomb/packets/pdu.py` | eight declarations plus the base |
| No transport reads a serial port | `grep -rn "import serial" src/pyomb/` | prints nothing |

## Decision

1. **A framer is constructed for one side** — it decodes requests or it
   decodes responses, and the side is a constructor argument rather than
   something read off each frame. A client-side framer decodes responses
   and a server-side one decodes requests.
2. **A passive monitor is separate work** — a reader watching a bus
   belongs to neither side and MUST NOT be served by guessing. It gets
   its own mechanism, tracked as its own issue, and this record does not
   design it.
3. **Nothing infers the direction from a checksum** — sizing a frame both
   ways and keeping whichever checksum passes is refused, for the reason
   in the alternatives below.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Track the transaction, so a request is followed by its response | The closest to a full answer, and it serves the participant and the monitor with one mechanism. It needs a resync rule and a first-frame rule that this project has no measurement for yet, and the participant case needs neither. Deferred to the monitor work rather than refused. |
| Configure the side and never build a monitor | Smallest surface. It contradicts the issue this serves, whose user story opens with watching traffic on a serial line, so it narrows the requirement rather than meeting it. |
| Size the frame both ways and keep whichever checksum passes | Needs no configuration and no state. A 16-bit checksum admits a wrong boundary about once in 65536, and both boundaries can pass at once with nothing to choose between them, so a reader would be wrong silently and rarely. |
| Split on the idle line the specification describes | What the wire actually does, and what a program on a general-purpose operating system cannot observe: a UART, a converter and a driver buffer each hold the bytes before a process sees them. |

## Consequences

- A framer needs an argument naming its side, so a caller has to know
  which it is. Every caller does: a client sends requests and reads
  responses, and a server does the reverse.
- Watching a bus is not possible until the monitor work lands. The
  library can decode a frame in either direction already; what it cannot
  do is find the boundaries without being told the side.
- The refusal to guess is a constraint on the splitter, not on the packet
  classes. A caller holding a complete frame reads it direction-free
  today, which is the half that is already built.
- A frame whose layout states no size is unaffected by this record. Two
  function codes lead with a discriminator rather than a count, and their
  size is not derivable from a prefix in either direction.

## Related

- Issue #231 — the serial work this decision serves
- Issue #358 — the record correction the splitter design is expected to
  produce
- ADR-035 — the record that put serial transport in scope
