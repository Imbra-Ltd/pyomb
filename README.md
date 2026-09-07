# pyomb

[![CI](https://github.com/Imbra-Ltd/pyomb/actions/workflows/ci.yml/badge.svg)](https://github.com/Imbra-Ltd/pyomb/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

_A Python Modbus library for rapid prototyping, device simulation and protocol
testing._

Use pyomb to communicate with a device, run a local simulator, or build and
inspect Modbus packets. Start with a small Python script, then add custom
behavior, response delays and deliberate protocol errors as your experiment
grows.

Work with packet objects or raw bytes, with control over how messages are
constructed and sent. The core uses only Python's standard library; serial
communication is available through an optional extra.

## Features

- **Modbus communication:** Connect over TCP, TLS, serial RTU or RTU-over-TCP,
  with configurable timeouts, retries and reconnection.
- **Scriptable server:** Define register maps, attach Python handlers and
  model device state. Script response sequences, delays, exception replies,
  malformed responses and disconnects.
- **Scriptable client:** Build request sequences to prototype integrations
  and exercise devices or local simulators from ordinary Python scripts.
- **Packet codecs:** Build, encode and decode TCP and RTU packets, including
  RTU checksum generation and verification.
- **Wire controls:** Send and receive raw bytes, configure TCP write chunks
  and control RTU timing. Inject delays, corruption, truncation and connection
  failures to test how a peer recovers.
- **Constraint checking:** Inspect protocol violations separately from
  serialization, so deliberately invalid packets remain possible.
- **Custom packet types:** Register additional request and response classes
  with the PDU parser.
- **Test scenarios:** Compose exchanges and assert responses, exceptions,
  timeouts, disconnects and response times.
- **Packet inspection and observation:** Inspect decoded fields and raw
  bytes, and observe traffic through public hooks carrying direction and
  timing. Exchange records using an open capture format.
- **Lightweight core:** No runtime dependencies for TCP, TLS or packet
  processing. Install the serial extra when you need serial communication.

## Quick start

Prerequisites: Python 3.10 or newer.

Install from PyPI:

```bash
pip install pyomb
```

Save this as `quickstart.py` and run it with `python quickstart.py`. It starts
a local server, reads one holding register and shuts both peers down. No
physical device is needed; the operating system chooses a free local port.

```python
from pyomb import ModbusClientSimulator, ModbusServerSimulator

server = ModbusServerSimulator(host="127.0.0.1", port=0)
server.start()
client = ModbusClientSimulator(host="127.0.0.1", port=server.port)

try:
    client.connect()
    header, response = client.request(fc=3, read_address=0, read_count=1)
    print(response)
finally:
    client.disconnect()
    server.stop()
    server.join(timeout=10)
```

The simulator returns its default register value, `65535`. Alongside the
connection logs, the response prints as:

```text
PDU: (FC: 03, Data: (2, 65535))
```

Change `read_address` or `read_count` to try another request, then add a
register map or Python handler to model your device's behavior.

For serial RTU communication, install the optional serial dependencies:

```bash
pip install "pyomb[serial]"
```

The [releases page](https://github.com/Imbra-Ltd/pyomb/releases) carries release
artifacts and a CycloneDX software bill of materials (SBOM).
For installation from a checkout, see [Development setup](#development-setup).

## Usage

The [examples guide](examples/README.md) contains additional runnable patterns
and their output. Those scripts run offline and are exercised by CI.

### Script the server

In the quick start, insert one or both of these lines after `server.start()`:

```python
server.set_delay(0.2)
server.set_fail(True)
```

The first adds a 200 ms response delay. The second makes the server return a
Modbus exception response. Reset them with `server.set_delay(0)` and
`server.set_fail(False)` to restore normal replies. For custom processing,
attach a Python callback with `server.set_data_handler(handler)`.

### Send a fragmented message

For a Modbus server already listening on `localhost:502`, configure sends in
8-byte chunks. TCP can combine or split writes, so these settings do not fix
the boundaries of network packets. The receiver reassembles the response
using the length declared in its header.

```python
import socket

from pyomb.packets import ModbusHeader, ModbusRequestFC1
from pyomb.packets import ModbusTcpRequest, ModbusTcpResponse
from pyomb.stream import ModbusTcpStream

pdu = ModbusRequestFC1(start_addr=0, quantity=1)
header = ModbusHeader(unit_id=1, length=len(pdu) + 1)
request = ModbusTcpRequest(header=header, pdu=pdu)

with socket.create_connection(("localhost", 502), timeout=5) as sock:
    stream = ModbusTcpStream(sock=sock, frag_size=8)
    stream.send(request.serialize())

    response = ModbusTcpResponse.deserialize(stream.receive())
    print(response)
```

A response carrying one byte of coil data looks like:

```text
MODBUS TCP RSP -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 4, Unit-ID: 1) | PDU: (FC: 01, Data: (1, 255))
```

For a version that starts its own local server, see
[fragmented_send.py](examples/fragmented_send.py).

### Serialize and deserialize a packet

Work directly with packet objects when you need to choose the header or
payload fields yourself. This example needs no connection:

```python
from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest

pdu = ModbusRequestFC1(start_addr=0, quantity=1)
header = ModbusHeader(unit_id=1, length=len(pdu) + 1)  # Includes the unit ID
packet = ModbusTcpRequest(header=header, pdu=pdu)

packet_bytes = packet.serialize()
restored = ModbusTcpRequest.deserialize(packet_bytes)
print(restored)
```

The round trip reproduces the original frame:

```text
MODBUS TCP REQ -> | HEADER: (Trans-ID: 0, Prot-ID: 0, Length: 6, Unit-ID: 1) | PDU: (FC: 01, Data: (0, 1))
```

### Inspect protocol violations

The Modbus Application Protocol caps Read Holding Registers at 125 registers
per request, so a quantity of 126 is one past the edge:

```python
from pyomb.packets import ModbusRequestFC3

request = ModbusRequestFC3(start_addr=0, quantity=126)

for finding in request.violations():
    print(finding)

print(request.serialize().hex())
```

The violation is reported, and the packet still serializes:

```text
ModbusRequestFC3.quantity is 126; the specification requires 0x0001 to 0x007D
030000007e
```

`violations()` reports findings without changing serialization. Call
`validate()` when you want a `ModbusPacketError` instead. Each finding names
its source, field, value and rule, so tests can inspect it without matching
message text.

## Project structure

```text
src/pyomb/              # The library
  packets/              # Codec, split by data-flow stage
    base.py             # Constraints and the abstract packet bases
    pdu.py              # PDU classes, one pair per function code, and the parser
    framing.py          # MBAP header, CRC helpers, TCP and RTU frame wrappers
  stream.py             # Transport: length-driven framing and fragmentation
  tls.py                # TLS settings and SSL context construction
  client_simulator.py   # Client simulator and request builder
  server_simulator.py   # Server simulator, select loop and response factory
  errors.py             # Modbus exception codes as a Python hierarchy
  logger.py             # Logger that writes to stdout and optionally a file
  defines.py            # Protocol constants
tests/                  # Tests for the library; a bare pytest runs this tier
  helpers/              # Doubles and reflection helpers shared across the tiers
  integration/          # Opens real sockets and starts threads; pytest -m integration
checks/                 # Gates over this repository's own conventions, not shipped
examples/               # Runnable usage patterns, executed by CI
scripts/                # Certificate generation
docs/                   # Guides, decisions, journal, audits
  design/               # Architecture and product design notes
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
Quick start. The core has no runtime dependencies; the optional serial extra
adds PySerial.

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
