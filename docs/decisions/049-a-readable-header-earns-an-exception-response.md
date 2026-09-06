---
id: "049"
status: Accepted
date: 2026-09-07
category: protocol
supersedes: []
superseded_by: []
---

# ADR-049: A readable header earns an exception response

**Upstream:** `none`. The rule is that a decoder splits its failures by what
the caller can still do about them, rather than by where they happened. That
is close to being general, but the split here is drawn by one wire format's
framing rules, and a template rule stated without them would not say where any
other decoder should cut.

## Context

The server simulator dropped the connection of any peer whose frame it could
not parse. Surviving the frame was the fix that mattered -- the thread used to
die with it -- but the sender still got nothing back.

A Modbus server that cannot satisfy a request is expected to answer. The
Application Protocol specification v1.1b3 defines an exception response for
exactly this: the function code with 0x80 added, then a one-byte exception
code. A client meeting a closed socket instead sees a network fault, and
cannot tell a malformed request from a crashed server.

That matters more here than in a general server. This library exists to
exercise somebody else's client, and how a client handles an exception
response is a thing worth testing. Before this change the simulator could not
produce one for a frame that failed to parse.

Whether an answer is possible depends on the MBAP header, the first seven
bytes. It carries the transaction, protocol and unit identifiers, all three of
which a response has to echo unchanged. `ModbusTcpRequest.deserialize` read
the header, checked its length field and parsed the PDU inside one `try`, so
every failure reached the caller as the same `ModbusPacketError` and the three
cases could not be told apart.

## Decision

1. **Split the decoder's failures by what survives** — a PDU that will not
   parse behind a header that did MUST raise `ModbusPduParseError`, carrying
   that header and the function code. Every other failure keeps raising the
   plain `ModbusPacketError`.

2. **A contradicting length field is not answerable** — where the MBAP length
   disagrees with the bytes received, the frame boundary is unknown and the
   stream is desynchronized, so no reply can be built from what follows.

3. **An absent PDU is not answerable** — the function code is the first PDU
   byte. A frame carrying none names no code an exception response could
   report.

4. **The server answers what it can** — on `ModbusPduParseError` the simulator
   MUST reply with exception code 0x03, illegal data value, echoing the
   carried header, and MUST keep the connection. It drops the peer only where
   nothing survived to echo.

```text
   bytes in
      |
      v
+-------------------+  unreadable   +---------------------------+
|  MBAP header      |-------------->|  ModbusPacketError        |
|  bytes 0..6       |               |  nothing to echo -> drop  |
+-------------------+               +---------------------------+
      | parsed                                   ^
      v                                          |
+-------------------+  contradicts the ADU       |
|  length field     |----------------------------+
+-------------------+                            |
      | agrees                                   |
      v                                          |
+-------------------+  empty PDU                 |
|  PDU              |----------------------------+
+-------------------+
      | unparsable
      v
+------------------------------------------+
|  ModbusPduParseError(header, fc)          |
|  -> exception response 0x03, keep the peer|
+------------------------------------------+
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Answer every parse failure | The three identifiers a response echoes live in the header. With no readable header there is nothing to echo, so the reply would invent a transaction identifier the client never sent |
| Keep one error type and have the server re-read the header itself | The server would re-implement the parse it just asked the codec for, and the two copies would disagree the first time either moved |
| Return a result object rather than raise | Every existing caller catches `ModbusPacketError`. A return type change is a break for all of them, where a subclass is a break for none |
| Answer with 0x01, illegal function | The function code was read successfully. What failed was the rest of the PDU, which is what 0x03 names |
| Treat a contradicting length as answerable | The declared length is how a reader finds the end of the frame. Answering on a length that disagrees means guessing where the next frame starts |

## Consequences

- `ModbusPduParseError` joins the public API and `__all__`. It subclasses
  `ModbusPacketError`, so a caller written before the split keeps working.
- `errors.py` gains its first import, a `TYPE_CHECKING` one for the header
  annotation. A real import would close a cycle, since the codec imports the
  errors.
- The simulator gains an `answer` method, which the normal path and the
  parse-failure path both send through. Two copies of the echo rules were the
  alternative.
- A test asserting that the sender of a malformed frame is retired now asserts
  the opposite. Its stated reason -- that a swallowed failure would spin the
  read loop -- no longer applies, because the server replies once rather than
  swallowing.
- A peer that sends garbage in a loop now gets a reply per frame rather than
  one disconnection. That is the specified behaviour and it is more work per
  bad frame; the connection limit and the inactivity sweep are what bound it.
- The split says nothing about the RTU packet classes, which have no MBAP
  header and frame by silence on the line. Serial transport will need its own
  answer.
