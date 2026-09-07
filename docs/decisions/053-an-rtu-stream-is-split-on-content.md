---
id: "053"
status: Accepted
date: 2026-09-07
category: protocol
supersedes: []
superseded_by: []
---

# ADR-053: An RTU stream is split on content, not on silence

**Upstream:** not filed; the issue is owed. With the domain skin off: a wire
specification describes the wire, and a program observes the wire through
buffering layers. A delimiter the specification defines in time may therefore
be unobservable. Check what the host can measure before designing on the
specification's model. The candidate file is
`templates/base/core/quality.md`.

## Context

A Modbus RTU frame carries no length field and no start marker, only a
trailing checksum. The specification separates one frame from the next by a
gap of roughly 3.5 character times of silence on the line.

A program cannot measure that gap. A UART, a USB converter and an operating
system driver each buffer the bytes before the process sees them, so arrival
times are not transmission times.

pymodbus refuses to use timing and records why in its RTU framer. Both
comments below were read at `pymodbus/framer/rtu.py` on the `dev` branch on
2026-09-07, rather than taken from an earlier reading:

> due to the USB converter and the OS drivers, timing cannot be quaranteed
> neither when receiving nor when sending

> the RTU frame does not have a fixed prefix only suffix, therefore it is
> necessary to decode the content of the frame to get length etc.

Its mechanism has three steps. It looks the packet class up from the function
code, asks that class for the frame size, and verifies the checksum at the
boundary the size implies.

Sizing needs the direction, and the function code does not carry it. A normal
response echoes the request's function code unchanged. The two directions are
laid out differently, so one byte implies two different lengths.

Length does not separate them either. Measured on this tree:

``` text
ModbusRequestFC1.expected_size   -> 5    frame 8 bytes
ModbusResponseFC1.expected_size  -> 5    frame 8 bytes, byte count 3
```

A read request and a read response carrying three bytes of coil data are both
eight-byte frames with a valid checksum.

## Decision

1. **Split on content** -- a reader MUST size each frame by asking the PDU
   class the function code names, and MUST verify the checksum at that
   boundary. Receive timing MUST NOT be a framing input.

2. **The checksum adjudicates** -- a boundary the checksum rejects MUST
   discard exactly one byte and resume the search. The reader MUST report how
   many bytes it discarded, so a lossy line is visible rather than silent.

3. **A layout stating no size resynchronises** -- where no byte of the prefix
   says where the frame ends, the reader MUST discard rather than stall. The
   Diagnostics sub-function table states a width for all but one
   sub-function, so the class answers for the rest.

4. **A response timeout is permitted** -- a wait of about a second sits
   orders of magnitude above the buffering noise. It MAY return a state
   machine to expecting a request. Its clock MUST be injectable.

5. **Framing and transport are not coupled by timing** -- rule 1 leaves the
   RTU reader needing bytes and nothing else, exactly as the TCP reader does.
   A package split MUST NOT be argued from a coupling that does not exist.

6. **Deliberate violation is unaffected** -- emitting non-compliant timing to
   exercise another implementation needs no reliable receive timing, and
   stays in scope.

``` text
   +-------------------+     side     +--------------------+
   |      oracle       | -----------> |      splitter      |
   |  predicts a side  |              |   sizes on it      |
   +-------------------+              +--------------------+
             ^                                  |
             |                                  v
             |                        +--------------------+
             |     a frame, or one    |      checksum      |
             +---- byte to discard ---|    adjudicates     |
                                      +--------------------+
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Split on inter-frame silence | The gap is real on the wire and unobservable through a driver, so the mechanism cannot be built |
| Separate the directions by frame length | An eight-byte frame is a legal read request and a legal three-byte read response, measured above |
| Infer the direction inside the splitter | An inferring reader is a separate object, so the sizing mechanism stays testable without a clock or a heuristic |
| Raise on a layout that states no size | One Diagnostics frame would stall a passive reader permanently |
| Try candidate lengths until a checksum lands | About one false accept in 65,536 per candidate, against a frame the sub-function table already sizes |

## Consequences

The splitter needs no clock and no serial port. It lives beside the packet
classes and is tested against byte strings.

A frame the layout cannot size is lost rather than recovered. Return Query
Data, a reserved sub-function and an unmodelled function code are the three
cases, and the discard count is the only report of that loss.

Rule 5 removes the timing argument for splitting the packet and stream
modules. It does not decide that split, which now needs a reason of its own.

Rule 4 leaves a timeout unimplemented. Nothing here waits on a response yet.
The rule exists so the next reader does not conclude that every timing
measurement is unusable.

## Related

- ADR-052 -- the record settling how a reader learns its direction
- ADR-035 -- the record whose package-split argument named inter-frame silence
