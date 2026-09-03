# pyomb

[![CI](https://github.com/Imbra-Ltd/pyomb/actions/workflows/ci.yml/badge.svg)](https://github.com/Imbra-Ltd/pyomb/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

_A Modbus library built for testing other Modbus implementations._

Testing a Modbus device means sending it frames a well-behaved library will not
send: a response split across three packets, a length field that disagrees with
the payload, a checksum that does not match the bytes it covers.

General-purpose Modbus libraries hide the wire. They assemble frames correctly,
retry on your behalf, and give you back parsed values — which is what you want
in production and exactly what you cannot use when the device under test is the
thing you are trying to break.

pyomb exposes the wire. It is a Modbus TCP and RTU codec, a length-driven
stream transport with explicit fragmentation control, and a scriptable
server/client pair, for engineers who need to drive another implementation
through cases a compliant peer would never produce.

## Features

- Encode and decode Modbus TCP and RTU frames, with the checksum computed from
  the bytes on the wire rather than read from a stored field
- Send a message in fragments of a chosen size, to exercise a peer's
  reassembly
- Reassemble a fragmented message by its declared length, rather than trusting
  one socket read to deliver one frame
- Run a scriptable server simulator that answers requests over plain TCP or TLS
- Drive a client simulator that matches responses to requests by transaction
  identifier and discards anything else
- Raise Modbus exception codes as a Python exception hierarchy
- Ask a packet which of the specification's constraints it breaks, and still
  send it — the check reports, it never refuses, because putting a frame a
  device rejects on the wire is how you grade the device
- Depend on nothing outside the standard library

## Quick start

Prerequisites: Python 3.10 or newer.

pyomb is not on a package index. Every tagged release attaches a wheel to its
record on GitHub, so install that:

```bash
pip install https://github.com/Imbra-Ltd/pyomb/releases/download/v0.6.0/pyomb-0.6.0-py3-none-any.whl
```

The [releases page](https://github.com/Imbra-Ltd/pyomb/releases) carries an
sdist and a CycloneDX SBOM beside each wheel. Contributors install from a
checkout instead; see [Development setup](#development-setup).

Build a Modbus TCP request, serialize it, and read it back:

```python
from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest

pdu = ModbusRequestFC1(start_addr=0, quantity=1)
header = ModbusHeader(unit_id=1, length=len(pdu) + 1)  # +1 for the unit id
packet = ModbusTcpRequest(header=header, pdu=pdu)

print(packet.serialize().hex())
```

This prints the twelve bytes of the frame:

```text
000000000006010100000001
```

Reading them in order: transaction identifier `0000`, protocol identifier
`0000`, length `0006`, unit identifier `01`, function code `01`, start address
`0000`, quantity `0001`.

## Usage

The simulators log to standard output, so the runs below print protocol
description lines alongside the values shown.

Each of the four snippets below has a runnable counterpart in
[examples/](examples/), which CI executes on every change. The two that need a
server bind a port the operating system assigns rather than 502, which is what
lets them run without privileges; [examples/README.md](examples/README.md)
indexes them with the output each produces.

### Serialize and deserialize a packet

```python
from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest

pdu = ModbusRequestFC1(start_addr=0, quantity=1)
header = ModbusHeader(unit_id=1, length=len(pdu) + 1)
packet = ModbusTcpRequest(header=header, pdu=pdu)

packet_bytes = packet.serialize()
restored = ModbusTcpRequest.deserialize(packet_bytes)
print(restored)
```

The round trip reproduces the original frame:

```text
MODBUS TCP REQ -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 6, Unit-ID: 1) | PDU: (FC: 01, Data: (0, 1))
```

### Send a fragmented message

`frag_size` is the point of this example: the request leaves in 8-byte pieces,
and the response is reassembled from however many pieces arrive, by its
declared length rather than by one socket read. This needs a Modbus server
listening on port 502 — the server simulator below is one.

```python
import socket

from pyomb.packets import ModbusHeader, ModbusRequestFC1
from pyomb.packets import ModbusTcpRequest, ModbusTcpResponse
from pyomb.stream import ModbusTcpStream

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 502))

pdu = ModbusRequestFC1(start_addr=0, quantity=1)
header = ModbusHeader(unit_id=1, length=len(pdu) + 1)
request = ModbusTcpRequest(header=header, pdu=pdu)

stream = ModbusTcpStream(sock=sock, frag_size=8)
stream.send(request.serialize())

response = ModbusTcpResponse.deserialize(stream.receive())
print(response)
```

The reassembled response carries one byte of coil data:

```text
MODBUS TCP RSP -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 4, Unit-ID: 1) | PDU: (FC: 01, Data: (1, 255))
```

### Run the server and client simulators

```python
from pyomb import ModbusClientSimulator, ModbusServerSimulator

server = ModbusServerSimulator(port=502)
server.start()

client = ModbusClientSimulator(port=502)
client.connect()

header, pdu = client.request(fc=1, read_address=0, read_count=10)
print(header)
print(pdu)

client.disconnect()
server.stop()
```

Reading 10 coils returns two data bytes:

```text
HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 5, Unit-ID: 1)
PDU: (FC: 01, Data: (2, 255, 255))
```

### Ask a packet what it breaks

The Modbus Application Protocol caps Read Holding Registers at 125 registers
per request, so a quantity of 126 is one past the edge:

```python
from pyomb.packets import ModbusRequestFC3

request = ModbusRequestFC3(start_addr=0, quantity=126)

for finding in request.violations():
    print(finding)

print(request.serialize().hex())
```

The violation is reported and the frame still goes out:

```text
ModbusRequestFC3.quantity is 126; the specification requires 0x0001 to 0x007D
030000007e
```

The trailing `007e` is the disallowed quantity, on the wire. That is the
point: `serialize()` reaches neither `violations()` nor `validate()`, so
sending a frame a device should reject stays possible, which is how you find
out whether the device rejects it. `validate()` is the same check with the
opposite manners — it raises a `ModbusPacketError` where `violations()`
returns a tuple of findings. A finding carries `field`, `value`, `rule` and
`source`, so a harness can assert which bound was crossed rather than match
on the message text.

## Project structure

```text
src/pyomb/              # The library
  packets.py            # Codec: MBAP header, PDU classes, parser, frame wrappers
  stream.py             # Transport: length-driven framing and fragmentation
  client_simulator.py   # Client simulator and request builder
  server_simulator.py   # Server simulator, select loop and response factory
  errors.py             # Modbus exception codes as a Python hierarchy
  logger.py             # Logger that writes to stdout and optionally a file
  defines.py            # Protocol constants
tests/                  # Per-module tests and regression modules for the library
checks/                 # Gates over this repository's own conventions, not shipped
examples/               # Runnable usage patterns, executed by CI
scripts/                # Certificate generation
docs/                   # Guides, decisions, journal, audits
  design/               # Direction notes the project has not adopted
  specs/                # Vendor Modbus specifications and the protocol tutorial
assets/                 # Generated test certificates (gitignored)
.github/                # CI, CodeQL and release workflows, Dependabot config
.vscode/                # Shared editor settings that mirror the CI gates
pyproject.toml          # Packaging metadata and tool configuration
```

MBAP expands to Modbus Application Protocol, the header that precedes every
Modbus TCP protocol data unit (PDU).

## Development setup

```bash
git clone https://github.com/Imbra-Ltd/pyomb.git
cd pyomb
uv sync --locked --extra dev
uv run pre-commit install
uv run pytest
```

The `test` extra carries what the gates need — pytest, pytest-cov, ruff, mypy
and bandit — and is what CI installs. The `dev` extra adds the hook runner and
the build tools on top of it. `pre-commit install` is a one-off that puts the
same checks in front of every commit.

The toolchain is locked in `uv.lock`, and `--locked` installs exactly what it
records rather than re-resolving, so a contributor and CI run the same
versions. Installing the library needs no uv — that is the `pip install` in
Quick start, and there are no runtime dependencies to lock.

The TLS tests need a certificate chain, which is generated rather than
committed:

```bash
python scripts/gen_test_certs.py
```

No external service, database or broker is required. The full check set is
documented in [docs/PLAYBOOK.md](docs/PLAYBOOK.md).

## Configuration reference

pyomb reads no environment variables and no configuration file. Every setting
is a constructor argument on the object it affects — the port on the
simulators, the fragment size on the stream. The TLS material and its options
travel together as a `TlsSettings` record, which a simulator takes as `tls`;
passing one is what selects TLS, and passing nothing is plaintext.

The transport defaults are secure: the interpreter's default cipher suite, peer
certificates required, and hostname verification on the client. Weakening any
of them is an explicit field on that record, intended for interoperability
testing on a test network. Each weakening is logged when the simulator is
built, so a session says what it gave up.

Both endpoints are simulators for testing Modbus implementations. They are not
hardened for production control networks.

## Links

| Document | What it covers |
| --- | --- |
| [examples/README.md](examples/README.md) | Runnable usage patterns, with output |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to propose a change |
| [SECURITY.md](SECURITY.md) | How to report a vulnerability |
| [docs/ONBOARDING.md](docs/ONBOARDING.md) | Setup, verification and key files |
| [docs/PLAYBOOK.md](docs/PLAYBOOK.md) | Git, quality checks, maintenance, release |
| [docs/specs/Open_Modbus_Tutorial.md](docs/specs/Open_Modbus_Tutorial.md) | Protocol introduction |
| [docs/decisions/](docs/decisions/) | Architecture decision records |
| [docs/dev-journal.md](docs/dev-journal.md) | Session history and post-mortems |
| [CLAUDE.md](CLAUDE.md) | Conventions, and the shape the rewrite targets |

The Modbus specifications this library implements are in
[docs/specs/](docs/specs/) as published PDFs.

## License

MIT — see [LICENSE](LICENSE) for the full text.
