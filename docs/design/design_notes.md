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
reliably, so the boundary is worked out from the content instead -- see
section 27.

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
SerialTransport
MemoryTransport
CustomTransport
```

This abstraction should remain independent from Modbus.

## 7. Serial Transport

Serial communication should be implemented behind the generic transport
interface.

``` python
client = ModbusClient(
    transport=SerialTransport(
        port="COM3",
        baudrate=19200,
        parity="E",
    ),
    framer=RtuFramer(),
)
```

The transport implementation should hide the underlying serial library.

PySerial is a good candidate for the platform-specific serial
implementation, but it should be an optional dependency:

``` text
pyomb
    zero runtime dependencies

pyomb[serial]
    pyserial
```

PyOMB's architecture should depend on its own `SerialTransport`
abstraction rather than directly exposing `serial.Serial`.

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
a timing question. It is a content question, and section 27 carries the
mechanism. The timing concepts below stay useful for generating traffic,
which is what the rest of this section is about.

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
    transport=SerialTransport("COM3"),
    framer=RtuFramer(),
)
```

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

## 27. RTU Frame Splitting

Section 5 says how a message is separated on the wire. This section says
how a reader finds that separation when the wire is RTU.

An RTU frame carries no length field and no start marker, only a trailing
CRC. A boundary therefore has to be worked out from the content: look the
PDU class up from the function code, ask it how long its frame is, and
check the CRC there. The size depends on the direction, and the byte that
would supply the direction does not.

A server echoes the request's function code unchanged in a normal
response, so the same byte appears in both directions. Only an exception
response differs, carrying the code with its top bit set. The two
directions are laid out differently:

``` text
function code 0x03
  as a request    >BHH       fixed, 5 bytes
  as a response   >BB{0}H    2 bytes, plus the byte count it declares
```

So the direction is needed to get the length, and the obvious way to get
the direction -- alternating request, response, request -- needs frames
that have already been split.

### The CRC breaks the circle

Nothing has to resolve the direction in advance if the checksum settles
it. An oracle predicts a side, the splitter sizes on the prediction, and
the CRC at the computed boundary reports whether the prediction was
right. A wrong prediction puts the boundary in the wrong place, so the
CRC fails there, and that failure is the signal to discard a byte and
start again.

``` text
   +-------------------+     side     +--------------------+
   |      oracle       | -----------> |      splitter      |
   |  predicts a side  |              |   sizes on it      |
   +-------------------+              +--------------------+
             ^                                  |
             |                                  v
             |                        +--------------------+
             |     a frame, or one    |        CRC         |
             +---- byte to discard ---|    adjudicates     |
                                      +--------------------+
```

This is what removes the need for length heuristics. A rule such as "a
read request is always eight bytes" answers the same question, less
reliably, and is wrong in the case below.

### Worked example

The specification's Read Holding Registers response, slave 0x11 returning
three registers. Both sizings are shown against the same eleven bytes.

``` text
  Sized as a request -- fixed >BHH, so the unit is 5 bytes

      11 03 06 AE 41 56 | 52 43 | 40 49 AD ...
      \_______________/   \___/
       CRC computed       read as the CRC     96 5D expected
       over these                             52 43 found      rejected

  Sized as a response -- 2 bytes plus the declared count of 6

      11 03 06 AE 41 56 52 43 40 | 49 AD |
      \________________________/   \___/
       CRC computed over these     the CRC  49 AD expected
                                            49 AD found        accepted
```

Read as a request the reader stops at offset 8 and compares against
register data. It discards the leading byte and tries again. Read as a
response it takes the declared byte count, stops at offset 11, and the
CRC lands.

### Two objects, because only one of them guesses

ADR-052 settles that an RTU reader is told which side it decodes rather
than inferring it per message. A sniffer that infers looks like a
reversal of that, and is not, provided the inferring lives in a second
object.

``` text
ModbusRtuSplitter(side=...)   told at construction; a client reading its
                              server, or a server reading its client.
                              No heuristics and no clock

ModbusRtuSniffer()            supplies the side from the oracle below;
                              passive monitoring, where nobody has told
                              anyone anything
```

The splitter is still told which side it decodes. The sniffer is the
thing doing the telling, so this stacks a decision on ADR-052 rather than
correcting it.

### The splitter loop

``` text
1. Fewer than four bytes held -- the shortest legal frame -- wait
2. Look the PDU class up from the function code, in this splitter's side
3. Ask expected_size(). None means the count field has not arrived; wait.
   A raise means the layout states no size at all -- see below
4. The frame runs 1 + size + 2 bytes. Fewer held than that, wait
5. CRC over all but the last two matches those two -- emit the frame,
   drop those bytes, go again
6. It does not -- drop the leading byte, count the discard, back to 1
```

The splitter opens no socket and no serial port, so it belongs beside the
packet classes rather than in the transport module. A serial byte source
feeds it; section 7 covers that half.

### Diagnostics and Encapsulated Interface cannot be sized

Function codes 0x08 and 0x2B lead with a sub-function and an interface
type. Those discriminate; they do not count, so no byte of the prefix
says where the frame ends and `expected_size` raises rather than
guessing. A splitter that knows only the six steps above stops dead on
the first one to cross the bus.

| Option | Costs | Risks |
| --- | --- | --- |
| Raise to the caller | nothing | one such frame stalls a sniffer permanently |
| Try every length in a window | one CRC per candidate | about one false accept in 65,536 per candidate |
| Treat as unsplittable, resync past it | nothing | that frame is lost, the stream survives |
| A sub-function table for 0x08 | one table | covers most sub-functions, not all |

The proposal is the last two together: size what the table knows, discard
and resynchronise past what it does not, and count the discarded bytes so
the loss is reportable rather than silent.

### The oracle

Certainties first, alternation second.

``` text
  checked before the state is consulted
    fc >= 0x80    ->  response  (only a server sends an exception)
    addr == 0x00  ->  request   (broadcast; no answer follows)

  +-----------+
  |  SYNCING  |  try the predicted side, then the other;
  +-----------+  whichever CRC lands wins
        |
        | a side confirmed
        v
  +------------------+  --- emits a request --->  +------------------+
  | EXPECT_REQUEST   |                            | EXPECT_RESPONSE  |
  +------------------+  <-- emits a response ---  +------------------+
        ^                                                  |
        +----------------- timeout ------------------------+
```

Two cases stay ambiguous whatever the oracle does, and both are
properties of the protocol rather than gaps in this design:

``` text
Read Coils, three bytes of data
  request    11 01 00 13 00 25 0E 84
  response   11 01 03 CD 6B B2 00 64
  both are eight-byte frames with a valid CRC, so length separates
  nothing here

Write Single Coil, Write Single Register
  the specification defines the response as an echo of the request, so
  the two directions are the same bytes
```

Alternation resolves both. A single frame in isolation does not.

### Which timing is usable

The specification separates frames by roughly 3.5 character times of
silence. A program cannot observe that: a UART, a USB converter and a
driver buffer have each buffered the bytes before the process sees them,
so arrival times are not transmission times. That is why the boundary
above comes from content, and it is why section 9's detection claim is
corrected there rather than restated here.

A response timeout is a different measurement. At a second or so it sits
well above the buffering noise, and it recovers a state machine left
waiting on a server that never answered. The clock is injected, so the
recovery is testable without sleeping.

The deliberate-violation half of section 9 is untouched. Emitting
non-compliant timing to exercise somebody else's client needs no reliable
receive timing at all, and it is what a simulator is for.
