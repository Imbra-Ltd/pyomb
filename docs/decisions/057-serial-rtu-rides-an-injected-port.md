---
id: "057"
status: Accepted
date: 2026-09-10
category: protocol
supersedes: []
superseded_by: []
---

# ADR-057: Serial RTU rides an injected port

**Upstream:** none. With the domain skin off: a library that has to work
with any driver for a device class takes the open handle from the caller
and names the two methods it needs, rather than choosing a driver and
wrapping it.

## Context

RTU support stops at the codec. `adu/rtu.py` serializes a frame and
verifies its checksum, `ModbusPdu.expected_size` sizes one from its first
bytes, and nothing assembles the two into reading the next frame off a
serial line.

The reader that did was removed as paid functionality, together with the
sniffer. The removal took one class too many. A client or server reading
its own peer is told which direction the frames travel, uses no heuristic
and no clock, and cannot find a boundary without the splitter. Only the
sniffer infers a direction nobody supplied.

Two facts the records that left with the sniffer established still hold.
An RTU frame declares no length, so its end is worked out from the content:
the PDU class named by the function code states the size, and the checksum
adjudicates that boundary. The specification separates frames by silence on
the line, and a program cannot observe that silence, because a UART, a USB
converter and a driver each buffer the bytes first.

Serial transport is in scope and unscheduled, with `pyserial` behind an
extra named for the capability, and `pyproject.toml` declares no runtime
dependency on purpose. RS-422 is full duplex; RS-485 two-wire is half
duplex on a shared bus. At the library level they differ in two things
only: whether a transceiver echoes what it sent, and whether a server sees
requests addressed to other slaves.

## Decision

1. **The library opens no port and imports no serial library.** A caller
   hands over an object that is already open and satisfies `BytePort`:
   `read(size) -> bytes` and `write(data) -> int`. `read` returns between
   one and `size` bytes, or none once the port's own timeout elapses; a
   port that raises `TimeoutError` instead is the same event. Baud,
   parity, stop bits, the RS-485 driver-enable turnaround and the read
   timeout belong to the port. pyserial's `Serial` satisfies the protocol
   unchanged, and so does `socket.makefile("rwb", buffering=0)`.
2. **The stream carries no timeout.** The port's read timeout is the
   response timeout. A port with no timeout blocks forever, and one with a
   zero timeout reports silence whenever nothing is waiting; the protocol's
   docstring names both as unsupported.
3. **A reader is told its side.** `ModbusRtuSplitter(side)` decodes
   requests or responses, never both: a normal response echoes the
   request's function code, and the two directions size differently.
   `read_rtu_frame(stream, side)` and `RtuRead` are public, so a reader
   outside this library sizes a frame through exported names only.
4. **`ModbusRtuStream(port, side, echo=False)` reads exact counts.** A read
   the size of the largest frame blocks for the whole timeout on a port
   that already holds a short one. So the stream reads what the next
   verdict needs: the head, then one byte at a time until the count field
   arrives, then the remainder. Short non-empty reads continue. Every
   `OSError` from the port becomes `ModbusNetworkError`.
5. **Silence with nothing held is a timeout.** The stream raises
   `ModbusTimeoutError`, a `ModbusNetworkError`, and never returns an empty
   frame, because a serial line does not close. Silence with bytes held
   means no more are coming, so an incomplete verdict is now a rejection:
   leading bytes are discarded and the rest re-scanned. Only when nothing
   lands is the silence a framing error, reported with the count discarded.
6. **A layout the registry cannot size falls back to silence.** Diagnostics,
   the encapsulated interface and every function code the registry does not
   know state no size. An endpoint expecting one frame then reads until the
   port goes quiet, bounded at the 256-byte ADU maximum, and hands the whole
   buffer to the checksum first. Only where that rejects is what was held
   scanned, the way silence with a sizable head is. Silence is the last
   resort where content cannot size, and the one departure from the record
   that left. After a discard an unsizable head is noise, and is discarded
   rather than waited on.
7. **Echo is a stream option, off by default.** With `echo=True` the stream
   reads its own frame back after every write, looping until it has the
   length or the port goes quiet. A mismatch drains the port, resets the
   splitter and raises `ModbusNetworkError` naming a collision or a stale
   reply.
8. **The line between free and paid.** Everything this record names ships
   here under MIT. `ModbusRtuSniffer`, `RtuSyncState` and `RtuSniffedFrame`
   ship from the private package, which reaches sizing through
   `read_rtu_frame` and `RtuSide` alone.
9. **`pyomb[serial]` installs pyserial, and nothing here imports it.** The
   extra is a convenience for a caller. The examples job installs no extras,
   and the example drives an in-memory port.

```text
  the caller opens the port         this library
  +--------------------------+      +-----------------------------------+
  | serial.Serial(...)       |      | ModbusRtuStream(port, side)       |
  | socket.makefile("rwb")   |----->|   reads exact counts              |
  | any read/write object    |      |   ModbusRtuSplitter sizes on side |
  +--------------------------+      |   the checksum adjudicates        |
                                    +-----------------------------------+
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Ship a `SerialTransport(port="COM3", baudrate=...)` that imports pyserial | Binds the library to one driver and to a runtime dependency it declares it does not have; a caller on another library gets nothing |
| Split frames on inter-frame silence | The gap is real on the wire and unobservable through a driver, measured before; content sizes every frame the registry knows |
| Refuse any layout the registry cannot size | A serial client could never read a device-identification reply or any vendor function code, which is what a simulator exists to exercise |
| Scan every offset of a silence-framed buffer straight away | An unsizable frame that arrived alone is then judged on up to 256 checksums instead of one, which raises the false-accept rate from about one in 65,536 to about one in 250; the scan is kept for what the one checksum rejects |
| Return an empty frame on silence, as the TCP stream does on a close | A serial line never closes, and a receiver loop that stops on an empty frame would stop at the first idle second |
| Leave echo handling to the caller's port | Every RS-485 user with an echoing transceiver writes the same wrapper, and gets the collision diagnosis wrong |

## Consequences

- `pyomb.transport` exports `BytePort`, `RtuSide`, `MIN_RTU_FRAME`,
  `RtuRead`, `read_rtu_frame`, `ModbusRtuSplitter` and `ModbusRtuStream`;
  `pyomb` re-exports them and `ModbusTimeoutError`.
- RTU over TCP works through a socket's file object without a class of its
  own; the integration tier proves it over a socket pair.
- The simulators still speak TCP. Making them speak RTU needs the RTU
  envelope, matching by slave id and function code, and a server that
  ignores requests to other slaves; that is its own issue.
- The private package retires its own copy of the splitter in favour of
  importing it; its sniffer keeps its own buffer and calls `read_rtu_frame`
  once per side.
- A multi-drop server whose master sends two unsizable requests back to
  back loses both to the checksum rather than mis-framing them.
- A fault layer that violates serial timing on purpose stays possible,
  because sending needs no reliable receive timing.

## Related

- #231, #391 -- the byte source and the splitter this record delivers
- #384, #386 -- the removal, and the correction that redrew the line
