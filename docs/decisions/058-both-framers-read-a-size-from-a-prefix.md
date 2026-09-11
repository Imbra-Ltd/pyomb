---
id: "058"
status: Accepted
date: 2026-09-11
category: repository
supersedes: []
superseded_by: []
corrects: ["035"]
---

# ADR-058: Both framers read a size from a prefix, so framing keeps no module

**Upstream:** filed as `none` for now, because the rule set this would target
is being reworked to require fewer records. With the domain skin off: a
revisit trigger names the event that reopens a decision and the reason that
event will matter. The event can arrive while the reason turns out false, and
a reader honouring the trigger without testing its premise reopens a decision
on an argument nobody holds any more.

## Context

A merged record refuses a design note's six-layer vocabulary as a structure
and keeps it as names. Its first rule carries a revisit trigger firing on a
second transport, and states why that event would matter:

> Framing and transport genuinely separate at that point, because an RTU
> framer splits on silence and a TCP framer splits on a declared length.

A later record narrowed that trigger to its transport half and left the
premise alone, deferring the correction to whoever designed the serial frame
splitter. The splitter has now been designed. This is that re-read.

### What the tree holds, measured today

| Claim | Command | Result |
| --- | --- | --- |
| A second transport shipped | `wc -l src/pyomb/transport/*.py` | four modules, 1503 lines |
| The RTU framer reads a size | `grep -c "expected_size" src/pyomb/transport/rtu.py` | 1, inside `read_rtu_frame` |
| The TCP framer reads a size | `grep -n "def get_message_length" src/pyomb/transport/stream.py` | line 143 |
| The RTU framer reads no clock | `grep -n "^import" src/pyomb/transport/rtu.py` | `enum`, `logging`, no `time` |
| The modules the rule named | `ls src/pyomb/packets.py src/pyomb/stream.py` | neither exists |

### The premise the trigger rests on

Silence is what the specification puts between two RTU frames on the wire. It
is not what a program can measure. A UART, a converter and a driver buffer
have each held the bytes before the process sees them, so arrival times are
not transmission times.

So the shipped splitter reads content instead. It looks the PDU class up from
the function code, asks that class for the size its layout implies, and lets
the checksum adjudicate the boundary. That is a pure function of bytes.

## Decision

| # | Rule |
| --- | --- |
| 1 | The second-transport trigger is discharged and does not re-arm |
| 2 | The silence premise is withdrawn; both framers read a prefix |
| 3 | Framing keeps no module of its own |

```text
  what the trigger predicted        what the second transport shipped
  -------------------------         ---------------------------------
  RTU framer  -> a clock            RTU framer  -> function code, then
  TCP framer  -> a length field                    expected_size, then CRC
  two shapes, so two homes          TCP framer  -> MBAP length field
                                    one shape, so one home
                                                |
                                                v
                                    transport/  stream <- rtu
```

### 1. The trigger is spent

The event the trigger named has happened, this record is the re-read it
asked for, and the answer is that nothing moves. A trigger is discharged by
being answered once, not by being carried forward to the next transport.

A third transport is a new question and needs its own trigger, written by
whoever has a reason to expect a different answer. Re-arming this one would
schedule a re-read that this record has already performed.

### 2. Both framers read a size out of a prefix

The two framers were expected to differ in kind. They do not. Each reads a
few leading bytes, computes where the frame ends, and waits for exactly that
many bytes to arrive.

What differs is only where the size is written. Modbus TCP puts it in a
header field; Modbus RTU leaves it implied by the function code and the
layout that code names. Neither framer consults a clock, and the timeout that
ends a silent read belongs to the port the caller opens.

The premise is therefore withdrawn. It was a reasonable reading of the
specification and a wrong prediction about an implementation, and nothing
that rests on it survives.

### 3. Framing stays where it is

Rule 1 of the corrected record refuses a vocabulary the authority to mandate
a structure. That refusal is untouched here: no requirement asks framing for
a module, and the trigger that might have produced one has now answered no.

The modules the rule named are gone in any case. Both moved on independent
grounds, measured seams rather than layer words, which is the standard a
later record already set for a split.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Supersede the corrected record | Every one of its six rules is live, including the one this corrects. A record marked replaced to withdraw a premise tells each later reader the rest is dead, which the corpus already pays for once. |
| Leave the trigger armed for a third transport | Cheapest, and it keeps a re-read scheduled against a reason this record shows is false. The next reader would re-derive the same answer from the same wrong premise. |
| Correct the premise and say nothing about the trigger | Half the obligation. The trigger fired on this change, so a record that withdraws its reason and leaves it armed reads as an oversight rather than a decision. |
| Split framing out now that a second transport exists | Takes the trigger's prediction at face value. The measurement says the two framers have one shape, so the split would buy a module boundary no seam supports. |
| Record the correction on the issue that found it | That issue is closed, and a closed issue is where this correction has already been sitting. A reader of the rule meets the front-matter link and does not meet the issue. |

## Consequences

- Nothing in the tree changes. No file moves, no signature moves, and no test
  is touched. This record is metadata plus a reading.
- The corrected record gains a second entry in `corrected_by`, so a reader of
  its first rule now meets both the narrowing and this withdrawal.
- One revisit trigger leaves the corpus. It is the first to be discharged by
  the event it named rather than by a record that supersedes it.
- A reader of the corrected record still meets the silence premise in its
  prose, which stays as it merged. The front-matter link is the only thing
  that carries them to this page.
- The design note keeps the same claim in two of its sections. That note
  binds nothing, and the record governing design notes accepts the cost.
- Nothing detects the next trigger either. A person reading a rule when its
  event arrives remains the whole mechanism.

## Related

- ADR-035 -- the record whose first rule this one corrects
- ADR-051 -- the earlier correction, which narrowed the same trigger and left
  its premise for this one
- ADR-052 -- the correction relation this record is the second use of
- ADR-054 -- the layout change that removed the two modules the rule named
- ADR-057 -- the record for the transport whose landing fired the trigger
- Issue #358 -- the closed issue that recorded the falsified premise and
  deferred it to whoever designed the splitter
- Issue #231 -- the serial transport work the trigger named
