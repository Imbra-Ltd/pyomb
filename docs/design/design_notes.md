# PyOMB Architecture Direction

> **Pruned 2026-09-07.** This note is a proposal and binds nothing;
> ADR-035 settled what it contributes. Modbus ASCII is removed at the
> owner's direction, and every refused capability now carries a marker
> in place of its proposal: validation modes (ADR-031 rule 6), and
> deterministic fuzzing, capture and replay, proxy mode, PCAP export
> and the conformance framework (ADR-035 rule 2). The headings are
> kept so the section numbers cited by ADR-031, ADR-035 and ADR-036
> still resolve. ADR-035 describes this file as it stood before this
> pruning, including its length.

## 1. Project Philosophy

PyOMB is a **testing-first Modbus library that is also suitable for
production use**.

The guiding principle should be:

> **PyOMB should make every valid Modbus interaction easy to produce and
> every invalid Modbus interaction possible to produce deliberately.**

PyOMB should therefore not attempt to compete with general-purpose
Modbus libraries purely on convenience APIs. Its differentiation should
come from exposing and controlling the Modbus wire protocol while still
providing a clean production API.

A useful positioning is:

> **PyModbus: Talk Modbus correctly.**\
> **PyOMB: Find out what happens when Modbus isn't correct.**

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
simulation.

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

Tools for understanding existing Modbus communication:

-   packet inspection
-   protocol decoding
-   traffic mutation

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

**RTU** uses the unit address, PDU, CRC, serial timing, inter-character
timing, and inter-frame timing.

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

RTU frame detection depends partly on timing rather than a length field.

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

The server should support normal production-style handlers but also
deliberately abnormal behavior.

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

## 14. Scenario Framework

Testing behavior should eventually be expressible as scenarios.

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

Refused. ADR-035 rule 2 neither adopts nor tracks a capability that
traces to no requirement this project has stated. The heading is kept
so that the section numbers cited by the decision records still
resolve.

## 17. Proxy Mode

Refused. ADR-035 rule 2 neither adopts nor tracks a capability that
traces to no requirement this project has stated. The heading is kept
so that the section numbers cited by the decision records still
resolve.

## 18. Packet Inspection

Packets should be highly introspectable.

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

Refused. ADR-035 rule 2 neither adopts nor tracks a capability that
traces to no requirement this project has stated. The heading is kept
so that the section numbers cited by the decision records still
resolve.

## 20. Production API

Despite the testing-first design, normal Modbus operation should remain
simple.

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

## 25. Core Design Rules

1.  **PDU semantics must be independent of transport.**
2.  **Framing must be independent of byte transport.**
3.  **Testing faults must not contaminate production protocol logic.**
4.  **Malformed packets must be first-class objects.**
5.  **Serialization must not automatically imply validation.**
6.  **Normal production usage must remain simple.**
7.  **Fault injection should be deterministic and reproducible.**
8.  Refused by ADR-035 rule 2; the rule proposed here was that real
    traffic be capturable and replayable. The number is kept so the
    rules below it do not renumber.
9.  **Custom/vendor behavior should be easy to implement.**
10. **Avoid unnecessary runtime dependencies.**
11. **Convenience clients should wrap common primitives rather than
    duplicate implementations.**
12. **Wire-level visibility should remain available at every level.**

## 26. Target Identity

PyOMB should not become merely another Modbus client library.

Its identity should be:

> **A production-capable, wire-level Modbus protocol testing and
> simulation toolkit.**

The most important combination of capabilities is:

``` text
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

The long-term differentiator is simple:

> **If an implementation claims to speak Modbus, PyOMB should be able to
> determine how well it speaks Modbus --- including when the other side
> does everything wrong.**
