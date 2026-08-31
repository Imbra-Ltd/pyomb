# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version
numbers follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.2] - 2026-08-31

### Added

- `docs/design/`, a home for direction notes the project has not adopted,
  separate from the records that bind it. Its first note argues for a
  transport and framer architecture, validation modes and a wire-control
  layer. It is committed as written, with its corrections tracked rather than
  applied. See #224, ADR-030

### Changed

- Markdown is no longer held to printable ASCII. A document is written for a
  reader, so a diagram drawn in box-drawing characters is content rather than
  drift, and the pinned templates scope their own ASCII rule to identifiers.
  Control characters stay a defect everywhere, because one NUL makes git call
  a file binary and blinds the line-ending gate. Source is unchanged. What
  this gives up is homoglyph detection in prose. See #222, ADR-029
- The four published Modbus specifications and the imported protocol tutorial
  move to `docs/specs/`, separating material this project reads from material
  it writes. `docs/` gave the same visual weight to a 1996 Modicon reference
  guide and to the playbook. The fourth PDF, PI-MBUS-300 Rev J, was on no list
  in `CLAUDE.md` and is now declared alongside the other three rather than
  carried unexplained. Nothing ships in the distribution either way -- the
  sdist include list names neither path. See #175, ADR-028

## [0.4.1] - 2026-08-29

### Added

- A release now fails its own pull request when the newest 360-degree audit
  does not postdate the release before it. The audit step sits between two
  gated steps and was gated by nothing, so four releases were cut without one
  and only the fourth skip was written down anywhere. The gate reads the
  changelog's dated entries rather than `git tag`, because CI checks out
  shallow and a tag-based rule would find nothing and report a clean tree from
  it. Declining the audit stays available and now takes a dated `-skipped`
  record naming the release and the reason. See #206, ADR-027
- `docs/audits/2026-08-29-360.md`, the second full audit of this repository.
  Every critical finding the first one raised is closed: secret scanning, push
  protection and Dependabot are enabled, CodeQL and bandit both run, every
  action is pinned to a commit SHA, and `main` is protected with the
  administrator exemption off. The overall grade moves from C- to B+, and the
  2026-08-18 report is left as written because its grade is an observation of
  that date. See #206

## [0.4.0] - 2026-08-28

### Added

- `ModbusModeError`, exported from the package root, for an operation refused
  because the component and its caller disagree about which of them is driving.
  Nothing reaches the wire on that path, so none of the existing branches fit:
  `ModbusProtocolError` carries Modbus exception codes, `ModbusNetworkError` is
  sockets and `ModbusPacketError` is frames. It subclasses `ModbusBaseError`, so
  an existing `except Exception` still catches what it replaces. See #180

### Changed

- `ModbusTcpSender` and `ModbusTcpReceiver` keep the threading contract their
  shape has always advertised. Both were built with a lock and a stop event and
  neither used them fully: the sender never acquired its lock, and neither class
  ever read its stop event, so `stop()` returned having changed nothing a later
  call could observe. The sender's lock now covers the fragment settings and the
  send loop together, so two callers cannot interleave fragments and put a
  malformed frame on the wire; the receiver's covers its packet list and its
  fragment setting. `run_once()` reads the stop event in both. A caller that set
  the event and then called `run_once()` used to get a full run and now gets
  none, and a setter now waits for a send in progress. See #190, ADR-026

### Fixed

- The server's manual-accept refusal raises `ModbusModeError` rather than the
  base `Exception`. A caller had no way to catch that refusal without catching
  everything, in a library whose own rules say it should never have to, and the
  test covering it could only pin the message -- which matched a `TypeError`
  from a typo on the same line just as well. `TRY002` comes off the module's
  entry in the lint freeze, the finding it froze being gone. See #180
- A close that fails no longer escapes the client's teardown. `disconnect()`
  already treated `shutdown()` as able to fail, because a peer that has gone
  away is the ordinary case there rather than a fault, and did not treat
  `close()` the same way -- it sat in a `finally` with nothing catching it, so
  a raising close skipped the line clearing the socket attribute and left the
  client holding a socket it had already given up on. Whether a close raises is
  a platform difference: silent on Windows, `ENOTCONN` on Linux for the same
  reset socket. The regression test injects the fault from a double rather than
  waiting for a platform to supply it. See #193

## [0.3.1] - 2026-08-28

### Added

- The line-ending rule runs as a test rather than as two commands the playbook
  documented and nothing executed. No tracked file may reach the index
  carrying a carriage return, and nothing the project declares text may be
  stored as binary. The second is the case a count cannot see: a blob git
  classifies as binary stops being normalised, so its carriage returns enter
  the index unconverted while the count stays at zero, which is how this
  project's journal came to hold 1127 of them under a clean report. Which
  files are legitimately binary is read from git's own attribute column rather
  than listed in the test. See #122
- The changelog is pinned to the version the package reports, the way the
  README's wheel URL already was. A release whose `Unreleased` block was never
  cut now fails a pull request rather than shipping inside a tagged sdist that
  no later edit reaches. The compare links are checked alongside it: the
  unreleased range starts at the reported version, every version section
  carries a definition, and no definition names a version other than its own.
  See #123
- Every document gate asserts that its enumeration reached the corpus it reads,
  and a control discovers the gates and fails any that still reports clean once
  that corpus is emptied. Three of the six were measured blind: replacing the
  tracked-file listing with an empty result left the character-set rule, the
  readability limits and the frontmatter schema all green, and those three are
  the enforcement behind three divergences this project recorded. The control
  discovers its members rather than listing them, so a gate added later is
  covered without registering it anywhere. See #131, ADR-022

### Changed

- The ruff per-file freeze holds `src/` only. Retiring the `tests/` slice
  surfaced 77 findings across 39 entries, and the `scripts/` slice 28 across
  two, so the linter now gates files it previously exempted wholesale.
  Shrinking that table is the migration ADR-003 sanctions; what remains is
  eight entries over `src/`, plus the docstring exemption the test suite keeps,
  which is a convention rather than a freeze. See #168, #169, ADR-003
- Forty-four TODO comments are gone from the source. Seven became issues
  carrying verified evidence and the rest were deleted with the verdict
  recorded -- one was false, and one wrong in the other direction. They had sat
  in the module header blocks since the first import, so the wheel a consumer
  installs has carried them through every release until this one. See #174

### Removed

- `scripts/` is empty. Six of its eight files were unreachable from anything
  that runs, and three were not runnable as written: methods orphaned from
  their class, a class whose every method is `pass`, two helpers nothing
  imports. A stray text file was a stale draft of a docstring that disagreed
  with the shipped text about the PDU identifier range. See #150, ADR-024

## [0.3.0] - 2026-08-26

### Added

- `OmbClientSim` and `OmbServerSim` are exported from the package root, so
  `from pyomb import OmbServerSim` works alongside the submodule import that
  the README showed before. They are bound on first use rather than on
  import, which keeps the ssl import off a caller that only needs the codec:
  measured at roughly 13ms against the package's own 35ms. A new test module
  pins both halves -- that every name in `__all__` resolves, and that a plain
  `import pyomb` still loads neither simulator nor ssl
- An `examples/` directory of runnable usage patterns, each executed by CI
  against an installation built the way a consumer builds one, with no dev or
  test extras. A snippet that stops working now fails a pull request instead
  of misleading a reader. The examples bind a port the operating system
  assigns rather than the registered Modbus port, so they run without
  privileges and cannot collide with a real device; see ADR-021

### Fixed

- The sdist include patterns are anchored to the repository root. An
  unanchored pattern matches at any depth, so it also selected the templates
  submodule's file of that name -- a source archive built from a populated
  checkout carried 57 files that belong to another project. Released archives
  were unaffected, because the release workflow checks out without
  submodules, which was the checkout configuration covering for the include
  list rather than a safeguard
- Every entry point that prints states its output encoding rather than
  inheriting the console's, so output is the same text on a console that does
  not default to UTF-8. The check reads both directions: a module with a
  `__main__` guard that prints sets the encoding, and nothing under
  `src/pyomb/` sets it outside such a guard

## [0.2.1] - 2026-08-24

### Added

- CodeQL analyses every pull request and every push to `main`, over both
  the Python source and the workflow files, on the `security-extended`
  suite. It is the platform half of the SAST gate ADR-007 declined while
  the repository was private, and it lives in its own workflow so the
  write scope it needs stays off the CI jobs. Bandit is unchanged, and
  remains the half that fails a build on a finding. See ADR-012, and
  ADR-013 for the baseline it corrects
- Every tracked file is checked for characters outside printable ASCII. The
  em dash is permitted in Markdown prose and nowhere else, which is the
  narrowest allowance that lets the documents stand as written. The first run
  found four defects sitting among several hundred deliberate em dashes: a
  Cyrillic capital Te opening a sentence where a Latin T belongs and renders
  identically, curly quotes around a quoted exception name, and an en dash
  standing in for a hyphen. See ADR-014

### Changed

- The README quick start installs the wheel from the latest release by URL,
  and a test pins that URL to the version the package reports. A bump that
  misses the README fails rather than pointing readers at the previous
  release's asset. See #73

### Security

- The client and server TLS contexts declare a minimum protocol version
  rather than inheriting whatever the linked OpenSSL and its security level
  allow. MB-TCP-Security v21 fixes the value rather than leaving it to taste:
  R-32 requires TLS 1.2 or better, and R-34 forbids negotiating down to TLS
  1.1, TLS 1.0 or SSL 3.0. The floor is applied after the caller's
  `ssl_options`, which are OR-ed in and so can only add a restriction — a
  caller may still pin a session above the floor, and neither a mask that
  omits the protocol switches nor no mask at all can drop below it. No
  exposure was observed, because the development platform's own floor is
  already TLS 1.2; the library stated nothing, so the value was right by
  accident of the platform and a consumer on a permissive build could have
  negotiated lower. See #83
- `SECURITY.md` records why the plain and the TLS listener both bind every
  interface, so a reader can tell a deliberate default from an oversight.
  See #84

## [0.2.0] - 2026-08-21

### Added

- Tagged releases now carry their wheel, their sdist and a CycloneDX SBOM.
  `.github/workflows/release.yml` fires on a `v*` tag, refuses one that does
  not name the version the package reports, and attaches the distribution
  before generating the SBOM. The SBOM describes an environment holding only
  the built wheel, so it lists what a consumer installs rather than what CI
  built with. See ADR-011
- `v0.1.0` predates the workflow and keeps its empty asset list
- The GitHub release record carries the distribution. `v0.2.0` is the
  first tag to run the workflow, so it is the first release with assets
  attached. Nothing uploads to a package index; see #70
- `OmbServerSim` accepts port 0, asking the operating system for a free port,
  and reports the assigned port on its `port` attribute once `start()`
  returns. The server previously bound whatever it was given without reading
  the result back, so a caller passing 0 got a listener it had no way to
  reach. See #61

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

[Unreleased]: https://github.com/Imbra-Ltd/pyomb/compare/v0.4.2...HEAD
[0.4.2]: https://github.com/Imbra-Ltd/pyomb/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/Imbra-Ltd/pyomb/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Imbra-Ltd/pyomb/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Imbra-Ltd/pyomb/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Imbra-Ltd/pyomb/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Imbra-Ltd/pyomb/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Imbra-Ltd/pyomb/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Imbra-Ltd/pyomb/releases/tag/v0.1.0
