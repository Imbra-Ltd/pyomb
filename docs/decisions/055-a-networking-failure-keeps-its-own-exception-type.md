---
id: "055"
status: Accepted
date: 2026-09-10
category: protocol
supersedes: []
superseded_by: []
---

# ADR-055: A networking failure keeps its own exception type

**Upstream:** none. The rule is that a broad `except Exception` which
re-raises under one label discards whatever the caller could have matched
on, and is worth naming wherever a library re-labels an internal failure
into a status code or a category error.

## Context

Six places in `transport/stream.py` and `simulators/server_simulator.py`
caught any exception and relabeled it: `ModbusNetworkError` from
`ModbusTcpStream.send()`/`receive()`, from `ModbusTcpSender`/
`ModbusTcpReceiver.run_once()`, and `ModbusSlaveDeviceFailureError` from the
server's response dispatch. This library's message-handling code
(`adu/tcp.py`, `adu/rtu.py`, `pdu/common.py`) already narrows to the
exceptions each site can raise; the networking code was not part of that
fix (#426).

A caller catching for a specific defect saw the generic label instead. On
the server, a bug while building a response was indistinguishable on the
wire from a device legitimately refusing the request: both sent exception
code 0x04. A caller integrating against the simulator's error behaviour
could not tell a bug in this library from a device failure it was told to
simulate.

## Decision

1. **Re-raise an already-typed error unchanged** -- a site whose own call
   graph can raise a `ModbusBaseError` subclass MUST let it propagate
   rather than re-wrapping it in a different one.
2. **Catch only what the site can actually produce** -- the remaining catch
   narrows to the concrete exception the underlying operation raises
   (`OSError` for a socket call, `TypeError` for a fragmenting bug), never
   `Exception`.
3. **An error neither of the above covers is not caught** -- it propagates
   as itself. On the server a bug during response-building no longer sends
   exception code 0x04; the connection drops the same way any other
   unhandled failure from a data handler already does.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the broad catch, change only the message | The type, not the text, is what a caller matches on |
| Narrow every site to `ModbusBaseError` only, dropping `OSError`/`TypeError` too | A socket failure needs to become a typed `ModbusError`; a raw `OSError` reaching a caller expecting one is its own compatibility break |
| Keep the server sending 0x04 for every failure, narrowed or not | Indistinguishable from a real device failure; a bug is not one and should not be reported as one to an interoperability peer |

## Consequences

- A caller catching `ModbusNetworkError` around `ModbusTcpStream.send()` no
  longer catches a framing fault raised while fragmenting; it now surfaces
  as `ModbusPacketError`, which it always should have been.
- `ModbusTcpReceiver.run_once()` re-raises the stream's own exception
  subclass instead of a bare `ModbusBaseError`.
- The server no longer answers a peer with exception code 0x04 for an
  internal bug; the connection drops instead. A test asserting a 0x04
  response for every malformed-but-parseable request should assert one
  only for the cases this library's own factories can legitimately refuse.
- Six sites changed; #426 carries the full list and the regression test for
  each.

## Related

- #426
