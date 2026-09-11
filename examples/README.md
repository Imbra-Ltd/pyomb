# Examples

Runnable usage patterns, one per journey rather than one per API surface. CI
executes every file in this directory against an install of the project with no
extras, so an example that stops working fails a pull request.

What that catches is an example that raises, so it is worth saying which ones
can. Four compare a result and exit non-zero when it disagrees: the round
trip, the checksum, the RTU exchange and the capture. Two more fail if the
server never reaches its accept loop or the reply will not parse, but do not
compare the values they print: the fragmented send and the simulator run.
The last two demonstrate rather than verify -- they build a thing and print
it, and a change in what they print is caught by review rather than by the
job.

Install the project first. From a checkout:

```bash
pip install .
```

Every example runs offline. The two that need a Modbus server start this
project's own simulator in-process rather than reaching for a host, one holds
both ends of a connection itself, and the RTU exchange holds both ends of an
in-memory line, so a reader with the repository and nothing else can run every
one of them.

## A note on ports

The three socket examples ask the operating system for a free port by passing
`port=0`, and read the assigned port back once the listener is up. The project
README's local quick start uses the same approach. Its fragmentation snippet
uses port 502 for an already running server; `fragmented_send.py` starts its
own simulator on an assigned port.

Using an assigned port avoids conflicts with an existing listener and the
privileges a fixed low port can require. Every printed port below is whatever
the operating system handed out on that run and differs on yours.

## The examples

### Serialize a request

```bash
python examples/serialize_a_request.py
```

Builds a read-coils request and prints the frame it puts on the wire. No
socket: the codec does not import one.

```text
000000000006010100000001
12 bytes
```

Read the frame in order: transaction identifier `0000`, protocol identifier
`0000`, length `0006`, unit identifier `01`, function code `01`, start address
`0000`, quantity `0001`.

### Round-trip a packet

```bash
python examples/round_trip_a_packet.py
```

Serializes a request, reads it back, and checks both that the round trip
reproduces the frame and that the frame matches a byte sequence written out by
hand from the specification. The second check is the one that would catch a
mistake the encoder and decoder share.

```text
MODBUS TCP REQ -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 6, Unit-ID: 1) | PDU: (FC: 01, Data: (0, 1))
round trip reproduces the frame: True
frame matches the written-out vector: True
```

### Checksum an RTU frame

```bash
python examples/checksum_an_rtu_frame.py
```

Walks two published RTU frames through the checksum: what it covers, what
value it produces, and which way round those two bytes are sent. No socket,
for the same reason as the two above.

```text
payload    : 11 03 00 00 00 02
crc value  : 0x9BC6
on the wire: c6 9b
full frame : 11 03 00 00 00 02 c6 9b

payload    : 01 04 02 ff ff
crc value  : 0x80B8
on the wire: b8 80
full frame : 01 04 02 ff ff b8 80

2 frames match their published bytes
```

Read the first frame's last two lines together. The checksum is `0x9BC6` and
it goes out as `c6 9b` -- low byte first, which is the one place in Modbus
where a multi-byte field is not big-endian. Every other field, including the
addresses and quantities in the examples above, is sent the other way round.

The comparison is against the complete published frames, checksum bytes
included, rather than against the 16-bit values. A value matches whichever
order it is packed in afterwards, so checking only the number would agree
with the byte-swapped frame a real device rejects. Either break makes this
example exit non-zero, which is what the run above is asserting.

### Read RTU frames off a port

```bash
python examples/read_rtu_frames_off_a_port.py
```

Sends a published request down one end of an in-memory line and answers it
from the other, through `ModbusRtuStream` on both ends. The port is any open
object with `read(size)` and `write(data)` — here two buffers, on a machine
with hardware `serial.Serial(...)` — so no serial library is installed for
this. The reply read back is compared against its published bytes, and the
example exits non-zero when they differ.

```text
device read : MODBUS RTU REQ: (Slave ID: 17, PDU: (FC: 03, Data: (107, 3)), CRC: 34678)
master read : MODBUS RTU RSP: (Slave ID: 17, PDU: (FC: 03, Data: (6, 44609, 22098, 17216)), CRC: 44361)
on the wire : 11 03 06 ae 41 56 52 43 40 49 ad
the reply matches its published bytes
```

### Report a constraint violation

```bash
python examples/report_a_constraint_violation.py
```

Asks two read-holding-registers requests which of the specification's
constraints they break, and serializes the one that breaks a constraint. No
socket, for the same reason as the two above.

```text
quantity=125 reports 0 violations
ModbusRequestFC3.quantity is 126; the specification requires 0x0001 to 0x007D
  field=quantity value=126
serialized anyway: 030000007e
validate() raises: ModbusRequestFC3.quantity is 126; the specification requires 0x0001 to 0x007D
```

The Modbus Application Protocol v1.1b3 caps Read Holding Registers at 125
registers per request, so 125 reports nothing and 126 is one past the edge.
The bound is the document's, not this library's.

The last two bytes of the serialized frame are `007e`, the quantity the
specification does not allow. That the frame goes out at all is the behaviour
being shown: the check reports and never refuses, because sending a frame a
device should reject is how you find out whether it does.

### Send a fragmented message

```bash
python examples/fragmented_send.py
```

Sends the request in 8-byte pieces and reassembles the reply by the length its
header declares, rather than by whatever one `recv()` happened to return. The
server simulator runs in-process on an operating-system-assigned port.

On Windows, the bundled server can close the connection with `WinError 10035`
while receiving a fragmented request. This local example can fail on that
path. The README's transport snippet can instead target a separate Modbus
server that accepts fragmented requests.

Both simulators log to standard output, so the run prints protocol lines around
the two shown here. Trimmed to the parts the example is about:

```text
server listening on port <assigned>
MODBUS TCP RSP -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 4, Unit-ID: 1) | PDU: (FC: 01, Data: (1, 255))
```

The response carries one byte of coil data.

### Capture a burst of packets

```bash
python examples/capture_a_burst_of_packets.py
```

Sends three requests in a single shot with `ModbusTcpSender` and captures
them at the far end with `ModbusTcpReceiver`. Both ends are held here rather
than pointed at a device: a listener on an assigned port, a second socket
connected to it, and the accepted connection as the receiving end.

```text
listening on port <assigned>
sent 3, captured 3
MODBUS TCP PCKT -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 6, Unit-ID: 1) | PDU: (FC: 01, Data: (0, 0, 0, 1))
MODBUS TCP PCKT -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 6, Unit-ID: 1) | PDU: (FC: 01, Data: (0, 8, 0, 16))
MODBUS TCP PCKT -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 6, Unit-ID: 1) | PDU: (FC: 03, Data: (0, 0, 0, 2))
```

The three captured packets are the three that were sent, in order, with the
length field recomputed by the sender rather than carried from the caller.

What ends the capture is the sending socket closing. `run_once` reads until
the peer goes away or `stop` is called, so a monitor that keeps the
connection open drives it from its own thread; this example takes the
simpler route.

### Run the simulators

```bash
python examples/run_the_simulators.py
```

Starts both simulators and reads 10 coils across them. Trimmed the same way:

```text
server listening on port <assigned>
HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 5, Unit-ID: 1)
PDU: (FC: 01, Data: (2, 255, 255))
```

Two data bytes for 10 coils: eight in the first and two in the second, so the
leading `2` counts bytes rather than coils and the last byte is only partly
meaningful.

## What is not here

TLS. Both simulators support it, and a working example would need a
certificate chain — which `scripts/gen_test_certs.py` mints, and which no
reader should be handed pre-made in a repository. The secure path is covered
by `tests/integration/test_tls_integration.py` and documented in the project
README's configuration reference, which is where a capability that cannot be
demonstrated safely belongs.
