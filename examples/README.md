# Examples

Runnable usage patterns, one per journey rather than one per API surface. CI
executes every file in this directory against an install of the project with no
extras, so nothing here can rot quietly.

Install the project first. From a checkout:

```bash
pip install .
```

Every example runs offline. The two that need a Modbus server start this
project's own simulator in-process rather than reaching for a host, so a reader
with the repository and nothing else can run all four.

## A note on ports

The two socket examples ask the operating system for a free port by passing
`port=0`, and read the assigned port back once the listener is up. The project
README shows port 502 instead, which is the registered Modbus port and what a
real device listens on.

The difference is deliberate, not a simplification. On Linux a port below 1024
needs privileges, so an example fixed at 502 could not run in CI, and an
example CI does not run is one nobody notices breaking. Every printed port
below is therefore whatever the operating system handed out on that run and
differs on yours.

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

### Send a fragmented message

```bash
python examples/fragmented_send.py
```

Sends the request in 8-byte pieces and reassembles the reply by the length its
header declares, rather than by whatever one `recv()` happened to return. The
server simulator runs in-process on an operating-system-assigned port.

Both simulators log to standard output, so the run prints protocol lines around
the two shown here. Trimmed to the parts the example is about:

```text
server listening on port <assigned>
MODBUS TCP RSP -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 4, Unit-ID: 1) | PDU: (FC: 01, Data: (1, 255))
```

The response carries one byte of coil data.

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
reader should be handed pre-made in a repository. The secure path is covered by
`tests/test_tls_integration.py` and documented in the project README's
configuration reference, which is where a capability that cannot be
demonstrated safely belongs.
