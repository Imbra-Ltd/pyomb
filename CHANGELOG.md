# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version
numbers follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

### Fixed

- The 122 Liskov violations the type checker reported across the PDU
  hierarchy. The findings behind the mypy freeze fall from 711 to 593, and
  `pyomb.packets` no longer suppresses the `override` code

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
