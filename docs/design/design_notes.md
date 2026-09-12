# PyOMB Architecture Direction

> **Updated 2026-09-07.** At the owner's direction, this note now separates
> the open `pyomb` library from the proposed paid `pyomb-workbench`
> application. It describes design direction, not implemented APIs or a
> release commitment. ADR-035 records the earlier scope decision; capture,
> replay, proxy operation and PCAP integration remain outside this library.
> Modbus ASCII, validation modes, deterministic fuzzing and the conformance
> framework remain excluded as recorded below. Existing section numbers
> are preserved so earlier references still resolve.

## 1. Project Philosophy

PyOMB is a **simple Modbus library for rapid prototyping, device simulation
and protocol testing**. It keeps a testing-first approach and full control
of the wire while supporting ordinary Modbus communication.

The guiding principle should be:

> **PyOMB should make every valid Modbus interaction easy to produce and
> every invalid Modbus interaction possible to produce deliberately.**

Rapid prototyping is part of the identity: a new user should reach a first
working exchange or simulated device in minutes. Simple common operations
and detailed wire control should coexist, so the same small prototype can
grow into a device simulation or a test for an unusual failure.

A useful positioning is:

> **PyModbus: Talk Modbus correctly.**\
> **PyOMB: Start in minutes. Prototype, simulate and test with wire control.**

### Rapid prototyping: start in minutes

The first experience should need only the documented Python prerequisites,
installation and one small, runnable example. A local client/server example
should work without a physical Modbus device or a separately managed service.

- Provide complete examples that start a local simulator, exchange a request
  and show a value. Let the operating system assign a free local port, and
  make cleanup part of the example.
- Give common operations sensible defaults and short constructors. A caller
  should not need to assemble every transport, framer and channel by hand.
- Make a small register map and a simple response handler enough to prototype
  a device. Expose advanced timing, transport and fault settings when needed.
- Let users extend the same Python script from a normal exchange to stateful
  behavior and deliberate faults, without adopting an application framework
  or buying a workbench license.

Treat starting in minutes as a usability target to validate. Observe a new
user following the quick start from the documented prerequisites to the
first visible result, and record elapsed time and setup obstacles. The note
does not claim a measured onboarding time today.

### Open library and paid application

`pyomb` remains an independently useful open library under its MIT license.
Python users can build and run their own tests, control both simulated peers,
and deliberately produce invalid traffic without a workbench license.

`pyomb-workbench` is a proposed paid application in a separate product
repository. Its product concept lives in the `imbra-explore` knowledge base.
Capture, proxy and replay belong to one integrated application, with the
workflow: capture a problem, reproduce it in the lab, and compare the fix.

``` text
pyomb                         OPEN -- this repository
|-- Packet encoding, decoding and inspection
|-- Transport and wire controls
|-- Scriptable client and server
|-- Python handlers, response sequences and faults
`-- Public observation hooks and capture format
             ^
             | imports the public API
             |
pyomb-workbench               PAID -- separate product repository
|-- Sniffer and session recording
|-- Proxy with configurable fault rules
|-- Session replay and comparison
|-- Visual device and scenario editor
|-- Device profiles and recording-to-simulator conversion
`-- Test reports
```

This diagram assigns responsibilities; it does not claim every item exists.
The codec, TCP stream, TLS settings and configurable simulators already ship.
The richer handler and sequence APIs below, public observation hooks, and a
capture format are proposed extensions. The workbench is a product concept.

The workbench should consume the library's public API and share its protocol
implementation. Reusable protocol improvements belong in `pyomb`; capture
backends, session storage, application interfaces and commercial dependencies
belong in the workbench. Nothing in the library should import the workbench.

Add hooks or shared formats when a concrete scripting or workbench workflow
requires them. Document a capture format publicly so ordinary scripts can
read and produce it; recording and replay applications remain separate.

## 2. Main Capabilities

PyOMB should eventually provide four major operating modes:

``` text
                         PyOMB

          ┌───────────────┬───────────────┐
          │               │               │
       CONNECT         SIMULATE          TEST
          │               │               │
     Production       Client/server    Negative tests
     Modbus use       simulation       Fault injection
          │               │               │
          └───────────────┴───────┬───────┘
                                  │
                               OBSERVE
                                  │
                            Decode / Inspect
```

### CONNECT

Normal production Modbus communication:

-   Modbus TCP
-   Modbus TLS
-   Modbus RTU
-   RTU-over-TCP
-   Custom/vendor function codes
-   Timeouts
-   Reconnection
-   Retry policies
-   Synchronous operation

### SIMULATE

Programmable Modbus clients and servers for device and system
simulation. Their Python scripting interfaces remain in the open library.
Visual behavior editing and generating device profiles from recordings
belong in the workbench.

### TEST

Protocol testing capabilities including:

-   malformed frames
-   invalid CRC
-   invalid MBAP fields
-   fragmentation
-   timing violations
-   truncation
-   corruption
-   connection failures
-   boundary testing

### OBSERVE

Library functions for understanding supplied Modbus bytes and observing
communication through its own transports:

-   packet inspection
-   protocol decoding
-   proposed observation hooks exposing direction, raw bytes and timing

Passive sniffing of external traffic, capture setup, session storage and
searchable timelines belong in the workbench. Packet mutation remains a
library testing capability under TEST.

## 3. Architectural Layers

The architecture should separate protocol semantics from framing and
byte transport.

``` text
┌──────────────────────────────────────────────────────────┐
│                 Testing / Scenarios                      │
│ faults │ assertions                                      │
├──────────────────────────────────────────────────────────┤
│                    Client / Server                       │
│ sync │ retries │ reconnect │ datastore │ TLS             │
├──────────────────────────────────────────────────────────┤
│                         PDU                              │
│ function codes │ requests │ responses │ exceptions       │
├──────────────────────────────────────────────────────────┤
│                       Framing                            │
│ TCP │ RTU │ raw/malformed                                │
├──────────────────────────────────────────────────────────┤
│                    Channel / Wire                        │
│ fragmentation │ delays │ corruption │ timing │ faults    │
├──────────────────────────────────────────────────────────┤
│                      Transport                           │
│ TCP │ TLS │ Serial │ Memory │ Custom                     │
└──────────────────────────────────────────────────────────┘
```

The fundamental processing pipeline becomes:

``` text
PDU
 │
 ▼
Framer
 │
 ▼
Channel / Wire
 │
 ▼
Transport
```

Each layer should have one clear responsibility.

## 4. PDU Layer

The PDU layer represents Modbus operations independently of transport.

``` python
request = ReadHoldingRegisters(
    address=100,
    quantity=10,
)
```

The same request should work with TCP or RTU.

Core function-code support should eventually include at least:

       FC Operation
  ------- -------------------------------
       01 Read Coils
       02 Read Discrete Inputs
       03 Read Holding Registers
       04 Read Input Registers
       05 Write Single Coil
       06 Write Single Register
       15 Write Multiple Coils
       16 Write Multiple Registers
       22 Mask Write Register
       23 Read/Write Multiple Registers
       24 Read FIFO Queue
    43/14 Read Device Identification

Custom/vendor function codes should be easy to implement. Raw PDUs
should always remain possible:

``` python
RawPDU(
    function_code=0x41,
    data=b"\x01\x02\xff\x73",
)
```

## 5. Framing Layer

Framing answers:

> How are Modbus messages represented and separated on this transport?

The primary framers would be:

``` text
TcpFramer
RtuFramer
```

**TCP** uses the MBAP header and its length field.

**RTU** uses the unit address, PDU and CRC. The specification separates
frames by silence on the line, but a program cannot observe that timing
reliably, so the boundary is worked out from the content instead.

The Modbus PDU should not need to know which framer is being used.

## 6. Transport Abstraction

Transport answers:

> How are bytes physically or logically transferred?

A minimal abstraction could resemble:

``` python
class ByteTransport(Protocol):
    def open(self) -> None: ...
    def close(self) -> None: ...
    def read(self, size: int) -> bytes: ...
    def write(self, data: bytes) -> int: ...
```

Implementations could include:

``` text
SocketTransport
TlsTransport
MemoryTransport
CustomTransport
```

This abstraction should remain independent from Modbus.

A serial transport is not on that list, and section 7 says why: an open
port already satisfies the protocol above, so the library takes one rather
than building one.

## 7. Serial Transport

Built, and not the way the rest of this section originally proposed. The
decision record on serial RTU carries the reasoning; what follows is what
shipped.

The caller opens the port and hands it over. `ModbusRtuStream` takes any
object with `read(size)` and `write(data)`, which is the byte-transport
protocol above:

``` python
port = serial.Serial("COM3", baudrate=19200, parity="E", timeout=1.0)
stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)
```

A wrapper owning `port`, `baudrate` and `parity` was rejected. It binds the
library to one driver and to a runtime dependency the project declares it
does not have, and it serves a caller on another serial library not at all.
Injection also makes RTU-over-TCP fall out for free: a socket's
`makefile("rwb", buffering=0)` is a port.

PySerial therefore stays optional, and nothing under `src/` imports it. The
extra is a convenience for installing it alongside:

``` text
pyomb
    zero runtime dependencies

pyomb[serial]
    pyserial
```

Baud rate, parity, stop bits, the RS-485 driver-enable turnaround and the
read timeout belong to the port. The library never sees them, which is why
it can work with whichever serial library the machine has.

## 8. Channel / Wire Layer

This is where much of PyOMB's differentiation should live.

The channel sits between framing and transport and controls **how bytes
actually reach the peer**.

For normal production communication:

``` text
frame
  ↓
write entire frame
```

For testing:

``` text
frame
  ↓
fragment
  ↓
delay
  ↓
corrupt
  ↓
truncate
  ↓
transport
```

Example:

``` python
channel.write(
    frame,
    fragments=[1, 3, 2, 5],
    delays=[0.01, 0.5, 0.02],
)
```

Possible wire manipulations should eventually include:

-   arbitrary fragmentation
-   per-fragment delays
-   byte corruption
-   truncation
-   duplication
-   garbage insertion
-   slow transmission
-   connection termination
-   multiple ADUs in one TCP write
-   arbitrary TCP segmentation
-   serial timing violations

This keeps fault injection out of the normal protocol/client
implementation.

## 9. RTU Timing Control

RTU makes the Channel abstraction particularly valuable.

An RTU frame carries no length field, and detection was proposed here as
a timing question. It is a content question: the function code names a
class, that class states how long the frame is, and the checksum at that
boundary confirms the answer or rejects it. The timing concepts below stay
useful for generating traffic, which is what the rest of this section is
about.

PyOMB should understand concepts such as:

``` text
character time
t1.5
t3.5
inter-character timeout
inter-frame timeout
frame timeout
```

A normal RTU client should generate compliant timing automatically.
Testing should allow intentional violations.

This enables tests for:

-   excessive inter-character delay
-   insufficient inter-frame delay
-   truncated frames
-   incorrect CRC
-   noise before frames
-   noise after frames
-   back-to-back frames
-   broadcast handling
-   responses to broadcasts
-   malformed function payloads

## 10. Validation Modes

Refused. ADR-031 rule 6 states there is no validation mode: every
component declares its own constraints, `violations()` reports them and
`validate()` raises. One rule this section proposed was adopted rather
than refused -- serialization never validates, which is ADR-031 rule 4.

## 11. Packet Mutation

Mutation should become a first-class concept.

``` python
packet = ReadHoldingRegisters(
    address=100,
    quantity=10,
)

mutant = packet.mutate(
    transaction_id=0xffff,
    length=0,
)
```

Higher-level mutation helpers could eventually provide:

``` python
packet.corrupt("mbap.length")
packet.corrupt("crc")
packet.truncate(2)
packet.duplicate_byte(5)
```

Systematic mutations should also be possible:

``` python
for mutant in packet.mutations():
    client.send(mutant)
```

This creates structured negative testing rather than relying exclusively
on random fuzzing.

## 12. Fault Injection

Fault injection should operate independently from packet semantics.

Examples:

``` python
client.send(packet, truncate=3)
client.send(packet, disconnect_after=4)
```

or through composable channel objects:

``` python
channel = FaultChannel(
    transport,
    faults=[
        Delay(byte=4, seconds=0.1),
        Corrupt(byte=7),
    ],
)
```

This allows protocol correctness and transport behavior to be tested
independently.

## 13. Scriptable Server

The scriptable server belongs in the open library, alongside the scriptable
client. Python handlers should control register values, state, response
sequences, delays, malformed responses and disconnects. These capabilities
should remain usable from ordinary test scripts without the workbench.

The existing configurable server is the starting point. The fluent APIs
below illustrate proposed extensions; they are not current callable APIs.

``` python
server.when(
    Request(fc=3, address=100)
).respond(
    HoldingRegisters([1, 2, 3])
)
```

Testing:

``` python
server.when(
    Request(fc=3)
).respond(
    MalformedResponse(length=0xffff)
)
```

More advanced sequences should be possible:

``` python
server.when(fc=3).sequence(
    Timeout(),
    Timeout(),
    ExceptionResponse(6),
    MalformedResponse(),
    NormalResponse(),
)
```

This makes it possible to test recovery behavior of PLCs, SCADA systems,
gateways, and Modbus libraries.

The workbench should use this same execution engine for its visual device
editor, curated device profiles and recording-to-simulator conversion.
For example, responding normally twice and then timing out is library
behavior; deriving that behavior from a recording is a workbench workflow.

## 14. Scenario Framework

Python tests should remain free to compose library operations and assertions.
The scenario API below is a proposal for making those scripts easier to read.
It does not require the paid application. Visual scenario editing, managing
test campaigns, comparing runs and producing reports belong in the workbench.

``` python
scenario = Scenario("invalid-length")

scenario.connect()

scenario.send(
    ReadHoldingRegisters(0, 10)
    .mutate(length=0xffff)
)

scenario.expect(
    Disconnect(timeout=2)
)
```

Useful expectations include:

-   response received
-   specific exception returned
-   timeout
-   disconnect
-   connection remains alive
-   correct transaction ID
-   maximum response time
-   correct register count

A particularly useful robustness assertion is:

``` python
expect(server).stays_alive()
```

after deliberately malformed traffic.

## 15. Deterministic Fuzzing

Refused. ADR-035 rule 2 neither adopts nor tracks a capability that
traces to no requirement this project has stated. The heading is kept
so that the section numbers cited by the decision records still
resolve.

## 16. Capture and Replay

Session recording and replay belong in `pyomb-workbench`. The application
should record or import an exchange, reproduce a selected peer's behavior,
and compare the resulting responses with the original evidence.

The library supplies packet decoding, explicit byte transmission, wire
controls and programmable peers. Observation hooks and a shared capture
format should be added when this workflow needs them. The format should
carry raw bytes, direction, timestamps and connection identity; decoded
fields are derived information. Undecodable or malformed bytes must survive.

The workbench owns persistent sessions, capture import, replay scheduling,
peer-role selection, request matching, identifier adaptation and comparisons.
Replay needs explicit choices about device state, response waits and intended
timing. Reusing a capture does not promise identical TCP segmentation or
exact timing on a different host.

The existing buffered receiver consumes a connected socket and holds parsed
packets. It is not a passive sniffer or a durable session recorder. Simple
recording and resend examples can remain in the library's examples without
making it responsible for the workbench's complete replay workflow.

## 17. Proxy Mode

The inline proxy belongs in `pyomb-workbench`. It should combine observation,
recording and conditional fault rules against real implementations, using
the library's raw-byte, mutation and wire-control capabilities.

The workbench owns both connection lifecycles, bidirectional forwarding,
bounded buffering, rule execution and the record of each intervention.
Unmodified forwarding should preserve application bytes, including malformed
traffic. Rules that wait for a complete frame can change timing; this is
different from forwarding arriving bytes immediately.

Reusable delays, fragmentation, packet modification and simulator faults
remain available through the open Python API. A managed proxy service and
its rule editor are application responsibilities.

## 18. Packet Inspection

Packets should be highly introspectable through the open library. Decoding
supplied bytes and reporting field values or violations require no paid
application. Programmatic register maps and simulator state belong in the
open library. Searchable session views, visual register-map editors and
curated device-specific interpretation profiles belong in the workbench.

Suggested API:

``` python
packet.raw
packet.hex()
packet.fields
packet.explain()
packet.hexdump()
```

For example:

``` text
Modbus TCP Request
─────────────────────────────────────
00 01       Transaction ID       1
00 00       Protocol ID          0
00 06       Length               6
01          Unit ID              1
03          Function             Read Holding Registers
00 64       Address              100
00 0A       Quantity             10
```

## 19. PCAP / Wireshark Integration

Passive capture and PCAP import/export belong in `pyomb-workbench`.
Capture backends and external-stream reconstruction should remain outside
the library's runtime dependencies. The workbench passes extracted Modbus
bytes to the shared codec and retains the original capture evidence.

The library should expose enough packet information for external tools to
use it through the public API. Adding a capture backend or a file-format
adapter does not require duplicating the protocol implementation.

## 20. Production API

Normal Modbus operation should fit a short prototype script. Common client
and server constructors should supply sensible defaults; explicit layer
composition remains available for callers who need more control.

``` python
with ModbusTcpClient("10.0.0.10") as client:
    values = client.read_holding_registers(
        address=100,
        count=10,
        unit=1,
    )
```

Convenience classes such as:

``` text
ModbusTcpClient
ModbusRtuClient
```

should be thin constructors around the common architecture, not
independent implementations.

For example:

``` python
ModbusRtuClient("COM3")
```

should conceptually construct:

``` python
ModbusClient(
    transport=ModbusRtuStream(port=serial.Serial("COM3"), side=RtuSide.RESPONSE),
    framer=RtuFramer(),
)
```

Opening the port is the convenience such a constructor adds, and section 7
is why that is the only part it adds: the transport itself takes a port
rather than the settings to build one.

## 21. Protocol/Transport Composition

The architecture naturally permits combinations beyond the common cases.

RTU-over-TCP:

``` python
ModbusClient(
    transport=SocketTransport("10.0.0.1", 502),
    framer=RtuFramer(),
)
```

Virtual testing:

``` python
ModbusClient(
    transport=MemoryTransport(),
    framer=RtuFramer(),
)
```

This makes protocol testing possible without physical serial hardware.

## 22. Conformance Testing

Refused. ADR-035 rule 2 neither adopts nor tracks a capability that
traces to no requirement this project has stated. The heading is kept
so that the section numbers cited by the decision records still
resolve.

## 23. Property-Based Testing

Property-based testing should be extensively used internally.

For example:

``` python
deserialize(serialize(packet)) == packet
```

for all valid packet combinations.

Tools such as Hypothesis can be development dependencies without
becoming PyOMB runtime dependencies. Maintaining a lightweight or
zero-dependency core remains desirable.

## 24. Recommended Development Direction

A possible roadmap is:

  Version   Main Goal
  --------- --------------------------------------------------
  0.4       Transport/framer architecture + raw packet model
  0.5       Mutation API
  0.6       Production TCP client cleanup + core FC coverage
  0.7       Serial transport + Modbus RTU
  0.8       Advanced RTU timing
  0.9       Programmable server behavior
  0.11      Fault injection
  1.0       Stable public API and production/test platform

The exact version numbers are less important than maintaining the
architectural progression.

The workbench has a separate validation step before a broad implementation:
try one paid pilot around a real failure, from capture import through lab
reproduction to a comparison report. This is a proposed next step; no pilot,
customer commitment, price or delivery date is established here. Add shared
library capabilities as that concrete workflow requires them.

## 25. Core Design Rules

1.  **PDU semantics must be independent of transport.**
2.  **Framing must be independent of byte transport.**
3.  **Testing faults must not contaminate production protocol logic.**
4.  **Malformed packets must be first-class objects.**
5.  **Serialization must not automatically imply validation.**
6.  **Normal production usage must remain simple.**
7.  **Fault injection should be deterministic and reproducible.**
8.  Capture and replay workflows belong in the workbench. Any shared
    observation hooks and capture format remain open for Python scripts.
9.  **Custom/vendor behavior should be easy to implement.**
10. **Avoid unnecessary runtime dependencies.**
11. **Convenience clients should wrap common primitives rather than
    duplicate implementations.**
12. **Wire-level visibility should remain available at every level.**
13. Scriptable clients, servers and reusable fault controls remain in the
    open library; application workflows use the same public API.
14. Make a first working exchange or simulated device possible in minutes,
    with sensible defaults and advanced configuration available when needed.

## 26. Target Identity

PyOMB should combine a quick start with the control needed for detailed
protocol experiments.

Its identity should be:

> **A simple Modbus toolkit for rapid prototyping, simulation and protocol
> testing, with full control of the bytes on the wire.**

The most important combination of capabilities is:

``` text
Quick start and sensible defaults
     +
Raw packets
     +
Transport abstraction
     +
Framing abstraction
     +
Wire/timing control
     +
Deterministic mutation
     +
Programmable simulation
     +
Fault injection
```

That creates a coherent platform where the same protocol implementation
can be used for normal production communication, device simulation,
debugging and robustness testing.

`pyomb-workbench` builds the paid capture, proxy, replay and reporting
workflows on this foundation. It should make reproducing and investigating
failures easier while leaving the library useful to independent Python users.

The long-term differentiator is simple:

> **If an implementation claims to speak Modbus, PyOMB should be able to
> determine how well it speaks Modbus --- including when the other side
> does everything wrong.**

## 27. Scriptable Client

Section 13 sketches the scriptable server. The scriptable client is the
half the architecture overview names alongside it and never sketches.
Section 14's scenario API is a different thing: it asserts on a response,
and an assertion ends a test where a reaction continues a session.

A real use case, not just a test convenience: a condition-monitoring
script polls a pump's holding registers on a schedule and has to act on
what it reads -- raise an alarm when a bearing temperature crosses a
limit, and retry rather than give up when the device answers with a busy
exception. Without a rule table the caller repeats the same branch after
every read, and the polling loop and the reaction logic grow into each
other.

The proposal is one vocabulary across both sides, dispatching differently
on each. On the server a matcher describes an incoming request and the
effect is the response to send. On the client a matcher describes a
response that arrived and the effect is a callback to run against it.

``` python
client.when(HoldingRegisters).then(
    lambda reply: alarm(reply) if reply.values[0] > LIMIT else None
)

client.read_holding_registers(address=100, count=3)
```

Useful client-side reactions include:

-   escalate on a specific exception code
-   re-read on a timeout, up to a bound
-   alarm on a register value crossing a threshold
-   record a transaction for later comparison

Matching on response type lets `when(Response)` react to every shape
while `when(ExceptionResponse)` reacts to one, needing no dispatch
machinery beyond an isinstance test, provided the concrete response
shapes share a base class.

What `when()` accepts is the harder half, and three answers compete. A
declarative object -- `Request(fc=3, address=100)`, a field left unset
meaning any -- is printable, serialisable and comparable against another
rule. A bare class says "a response of this kind" and nothing about its
values. A predicate expresses every condition the other two cannot, and
can be rendered, diffed or checked for overlap by nothing at all.

Section 13 is what decides it, by putting the workbench's visual device
editor on this same engine: a lambda in the rule table is something no
editor can draw. So the declarative object should be the primary form, a
bare class should desugar to "any instance of", and a predicate should be
available wrapped in a label the editor renders in place of the body.
All three normalise to one matcher protocol when the rule is registered,
so each side dispatches through a single call rather than reading the
same field two incompatible ways.

One naming question stays open. Section 13 spells the server effect
`respond(...)`, which reads well where the effect is a response and badly
where it is a callback. A single verb on both sides is the point of
sharing a vocabulary, so either `then(...)` covers both cases or the two
sides keep separate verbs and share the shape only.

## 28. Transport-Layer Stimulus

An implementation can be correct at the PDU layer and wrong below it.
The common defects there are byte-stream defects: treating one read as
one frame, mishandling a declared length, or reading a graceful close as
an abort. Exercising those needs stimulus below the PDU, which the same
when/then vocabulary could express.

A real use case, not just a test convenience: a transparent
serial-to-Ethernet device server (Moxa NPort, Lantronix and similar)
forwards a serial byte stream onto a TCP socket without parsing it. At
9600 baud the bytes of one RTU frame arrive spread over milliseconds, so
the device server emits them across several TCP segments. A client that
treats one read as one frame works on a LAN against a PLC and fails
behind that device server, and that is the defect this stimulus exists
to find.

What decides the cost is not the vocabulary but the layer an event lives
at, because that decides whether the event is observable from the socket
API at all.

### Stream events

Fully reachable, and the richest of the three. Fragmentation already
exists in the wire layer. Coalescing is the more commonly broken
direction: two frames arriving in one segment, where an implementation
reading a fixed buffer parses the first and discards the tail. Also
useful are a declared length larger than the body followed by silence, a
length of zero, a length of 0xffff, and a byte-at-a-time trickle.

Deliberate fragmentation needs `TCP_NODELAY` on the sending side.
Otherwise Nagle coalesces the fragments back into one segment, and the
test passes without exercising the thing it names.

### Close events

Mostly reachable. A half-close via `shutdown(SHUT_WR)` sends FIN while
the read side stays open, testing whether a peer still delivers in-flight
responses or treats FIN as a dead connection. A FIN mid-frame tests
whether a truncated frame is reported as a close or as a protocol error.
`SO_LINGER` set to zero sends RST instead, testing whether a peer
distinguishes an abort from a graceful close. Simultaneous close, FIN
retransmission and FIN_WAIT_2 behaviour stay out of reach.

Remote sites meet these cases without anyone injecting them. A cellular
router or a VPN with a NAT idle timeout drops a quiet Modbus session, and
the peer learns of it as a FIN or an RST on its next poll rather than as
a clean shutdown.

### Handshake events

The thinnest of the three. Withholding `accept()` fills the backlog so
that further SYNs go unanswered, testing connect timeout and retry.
Binding without listening makes the kernel answer with RST, testing the
connection-refused path. Accepting and immediately resetting tests a
handshake that succeeds and then aborts.

Everything shaped like a crafted SYN-ACK -- a chosen initial sequence
number, window, MSS or delay -- is unreachable from the socket API. What
reaching it costs is not a packet library but a state machine: answering
a SYN directly means owning sequence numbers, retransmission and
teardown, which is a TCP implementation rather than a handler. Such an
engine would sit behind the same vocabulary, run on a bench with
elevated privileges, and gate nothing.

### What stimulus does not supply

Producing stimulus is the cheap half. The expected response has to be
traced to the specifications under `docs/specs/`, and no amount of
transport control supplies it. A suite asserting that a peer agrees with
this library measures interoperability rather than correctness.
