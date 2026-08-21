# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version
numbers follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Tagged releases now carry their wheel, their sdist and a CycloneDX SBOM.
  `.github/workflows/release.yml` fires on a `v*` tag, refuses one that does
  not name the version the package reports, and attaches the distribution
  before generating the SBOM. The SBOM describes an environment holding only
  the built wheel, so it lists what a consumer installs rather than what CI
  built with. See ADR-011
- `v0.1.0` predates the workflow and keeps its empty asset list

### Changed

- Every packet class now serializes through `serialize()` and deserializes
  through the classmethod `deserialize(stream)`. The abstract base declared
  both with `**kwargs` and `ModbusPdu` redeclared them with a format
  parameter, so each of the 34 implementations narrowed what the base
  promised and a caller holding the abstract type could not call either
  operation. See ADR-009
- `ModbusPdu.serialize` and `ModbusPdu.deserialize` no longer take a `fmt`
  argument. Caller-supplied packing moved to `ModbusPdu.pack(fmt)` and
  `ModbusPdu.unpack(stream, fmt)`, which is a breaking change for anyone
  passing a format. The format is now required where it appears rather than
  falling back to the class default on an empty value
- `ModbusSenderAbc.run_once` no longer declares a `burst` parameter. Burst is
  a property of the sender rather than of one run, and the only implementation
  already carried it as state set through the constructor or `set_burst_mode`.
  Breaking for anyone implementing the abstract base with the old signature
- `ModbusStreamAbc.send` names its parameter `message` rather than `packet`,
  matching its own subtype and what every caller passes. Breaking only for a
  caller passing it by keyword through the abstract type
- Client operations that need a live socket report `ModbusNetworkError` after
  `disconnect()`, where they previously raised `AttributeError` from inside
  the library. `disconnect()` is now idempotent rather than raising on a
  client that already has none
- The development toolchain is locked in `uv.lock` and installed with
  `uv sync --locked`. Contributors install with uv rather than
  `pip install -e ".[dev]"`; installing the published library still needs
  only pip. See ADR-010

### Fixed

- The 122 Liskov violations the type checker reported across the PDU
  hierarchy. The findings behind the mypy freeze fall from 711 to 593, and
  `pyomb.packets` no longer suppresses the `override` code
- `ModbusPdu.serialize` and `ModbusPdu.deserialize` report `ModbusPacketError`
  rather than leaking a raw `TypeError`. Both built their format string from a
  length measured before the guard that converts was entered
- The mypy freeze carries no real findings. `override` left with the sender
  signature and `assignment` with the client's socket attribute, which now
  takes the optional type its own teardown always implied
- `logger.py` and the error branches of every packet class are covered. Suite
  coverage moves from 84% to 96%

## [0.1.0] - 2026-08-18

First tagged release. The library has not been published to PyPI, so there is
no upgrade path to describe and no consumer to break.

### Added

- Modbus TCP and RTU codec: MBAP header, the PDU class hierarchy, a parser
  that dispatches on function code, and frame wrappers for both transports
- Length-driven stream transport, reading a frame by its declared length
  rather than treating one socket read as one frame
- Fragmentation control on send, so a message can be split into pieces of a
  chosen size to exercise a peer's reassembly
- Server simulator over plain TCP or TLS, with a select loop that retires a
  dropped connection from every piece of its bookkeeping together
- Client simulator that matches each response to its request by transaction
  identifier and discards anything else
- Modbus exception codes as a Python exception hierarchy
- Certificate generator minting a throwaway TLS chain into an ignored
  directory

### Changed

- The distribution and the import package are both named `pyomb`, replacing
  the four names the project previously answered to. The import package was
  `modbus`, which is a breaking change for any consumer — the distribution has
  never been published, so there are none
- Source moved under `src/`, so the test suite runs against the installed
  package rather than the working directory
- Packaging metadata moved from `setup.py` to `pyproject.toml`

### Security

- Transport defaults require a verified peer certificate and hostname
  checking, with no custom cipher string. Relaxing any of them takes an
  explicit argument
- Test certificates are generated on demand rather than committed. An earlier
  committed chain was rotated; it was self-signed and installed in no trust
  store

[Unreleased]: https://github.com/Imbra-Ltd/pyomb/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Imbra-Ltd/pyomb/releases/tag/v0.1.0
