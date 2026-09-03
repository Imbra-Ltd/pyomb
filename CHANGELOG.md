# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version
numbers follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `TlsSettings` and `TlsRole`, exported from `pyomb`. The settings record
  carries one simulator's certificate material and TLS options, builds the
  context for either side, and reports which of its settings weaken the
  secure baseline. Like the simulators it is bound on first access rather
  than on import, because it reaches `ssl`. See #194, ADR-041

### Changed

- The two simulator modules and their classes are renamed for what they hold.
  `omb_client.py` becomes `client_simulator.py` and `omb_server.py` becomes
  `server_simulator.py`; `OmbClientSim` becomes `ModbusClientSimulator` and
  `OmbServerSim` becomes `ModbusServerSimulator`. Neither file held a client
  or a server: this library provides neither, and the `omb_` prefix repeated
  the name of the package containing it. `RequestFactory` and
  `ResponseFactory` keep their names. See #274, ADR-038
- `from pyomb.omb_client import ...` and `from pyomb.omb_server import ...`
  raise `ModuleNotFoundError`. A submodule import resolves against the
  filesystem rather than the package, so keeping the old paths alive means
  shipping a module whose only job is to re-import -- and the two submodules
  stopped being public when the classes moved to the package root in 0.3.0.
  Import from `pyomb` instead, which is the documented form

- The simulator public API takes PEP 8 names, with no aliases. Seven methods,
  seven keyword parameters and the instance attributes behind them change at
  once, and every existing call breaks. A method alias is cheap and a keyword
  alias is not, so aliasing the methods alone would leave a call that resolves
  and then raises on its own keyword, naming a method the caller never wrote.
  See #192, ADR-039

  | Before | After |
  | --- | --- |
  | `sendRequest` | `send_request` |
  | `waitResponse` | `wait_response` |
  | `getPeers` | `get_peers` |
  | `setDelay` | `set_delay` |
  | `setConnLimit` | `set_connection_limit` |
  | `setFail` | `set_fail` |
  | `setDataHandler` | `set_data_handler` |
  | `readAddress`, `readCount` | `read_address`, `read_count` |
  | `writeAddress`, `writeCount` | `write_address`, `write_count` |
  | `connLimit`, `inactiveTimeout` | `connection_limit`, `inactive_timeout` |
  | `readList`, `startedEvent` | `read_list`, `started_event` |
  | `newConnEvent`, `quitEvent` | `new_connection_event`, `quit_event` |

- The server takes `host`, a string, where it took `ipAddress` as a 32-bit
  integer. `""` is the default and binds every interface, which is what
  `ipAddress=0` meant. A caller no longer converts a dotted quad by hand, and
  the two simulators now agree on what an address is. Passing an integer
  raises from the socket rather than being unpacked
- `frag_count` becomes `frag_size` on both simulators, and on the server's
  attribute, which was a third name for the same value. The transport already
  called it `frag_size` and sliced it as a byte width, so the transport's
  spelling is the correct one

- The TLS configuration is one object. Both simulators take `tls`, a
  `TlsSettings` record carrying the certificate material and every option;
  `secure`, `protocol`, `cert`, `key`, `ca_chain`, `ciphers`, `verify_mode`,
  `verify_hostname` and `ssl_options` are gone from both signatures. Passing
  an instance is what turns TLS on, so certificates can no longer be handed
  over and silently ignored. See #194, ADR-041

  ```python
  # before
  ModbusClientSimulator(secure=True, cert=CERT, key=KEY, ca_chain=CA)

  # after
  ModbusClientSimulator(tls=TlsSettings(cert=CERT, key=KEY, ca_chain=CA))
  ```

- Every option on `TlsSettings` defaults to `UNSET` rather than to a value.
  Unset means the baseline for the side the context is built for, which is
  what lets one object serve both: a client verifies the hostname and a server
  does not, and neither is a value the other could carry. `None` stays a legal
  value for `ciphers`, meaning the interpreter's own suite, which is why the
  sentinel is not `None`
- A weakened setting is reported rather than only permitted.
  `TlsSettings.relaxations(role)` names each one, and both simulators log the
  list at construction, so a caller who weakened one setting believing they
  weakened another sees what the session will actually carry
- The cipher string stays in OpenSSL format and is passed through verbatim.
  A friendlier vocabulary would be a mapping this project owns against a
  suite list OpenSSL changes between versions
- `DEFAULT_CIPHERS` and `MINIMUM_TLS_VERSION` are gone from both simulators.
  The floor is `TlsSettings.MINIMUM_VERSION`, in one place rather than two,
  and is still applied after the caller's options

### Deprecated

- `OmbClientSim` and `OmbServerSim` still resolve from the package root and
  raise `DeprecationWarning` naming the new spelling. They are absent from
  `__all__`, so a star import no longer offers them. Both are removed in
  0.7.0; see #275

## [0.5.1] - 2026-09-01

Documentation for what 0.5.0 shipped. That release added constraint checking
to every packet component and named it nowhere a consumer would look: the
tagged tree's README mentioned neither method, so the sdist and the wheel
metadata both carried the capability undocumented. Nothing in the library
changes -- no source module is touched, and the wire output is identical.

### Added

- A runnable example and a README usage section for the constraint checking
  v0.5.0 shipped, showing a violation reported and the frame serialized
  anyway. The feature list named the capability and nothing demonstrated it,
  which left a reader to infer that the library refuses to send a bad frame --
  the opposite of what it does. See #266
- ADR-037 records the contract v0.5.0 shipped: a packet holds each value once,
  the payload is a view derived from the named fields on every read, and
  assigning that view raises rather than silently doing nothing. The record is
  written after the change rather than before it, which is later than the
  decision-log rule asks for. See #228, ADR-037

## [0.5.0] - 2026-09-01

The packet classes stop storing each value twice, which is what makes a
changed field reach the wire, and gain the specification's own bounds as data
a caller can query. Two names are deprecated and one architecture question is
settled. Nothing the library puts on the wire changes: every per-function-code
suite asserts its frames against the published vectors and none was touched.

### Added

- ADR-034 inverts how a rule from the pinned templates is adopted: a rule binds
  when someone can name the defect it would have caught in this repository, and
  is otherwise declined in one line with no record and no ticket. `CLAUDE.md`
  carries it in the precedence block. See ADR-034
- PLAYBOOK 3.24, on the docstring-example gate and the three examples frozen
  because they need a Modbus server nothing starts. See #247, #254
- ADR-035 settles what the architecture direction note contributes. Its six
  layers become vocabulary for responsibilities the three packages already
  carry, rather than a structure to build; six capabilities tracing to no
  requirement are refused outright; serial transport is in scope and
  unscheduled. Nothing on the wire changes. See #224, ADR-035
- A PDU payload may be given as bytes, which is documented and supported.
  Bytes carry any sequence, where the format string they replace describes
  only the layouts `struct` can write. See #229, ADR-036
- Packet constraints are declared per class and queried. Every packet
  component carries the bounds the specification puts on its own fields as
  `LIMITS`, and two methods read them: `violations()` returns findings and
  `validate()` raises. A component reports for the parts it holds, so asking
  a TCP request covers its header and its PDU too. `ModbusViolation` is the
  finding type and is exported. `serialize()` calls neither method and gains
  no parameter, because emitting a frame a device rejects is what a
  simulator is for. See #196, ADR-031
- `docs/audits/2026-09-01-360.md`, the third full audit of this repository and
  the first produced under the gate that requires one. Field-range checking
  was the previous report's one protocol failure and is closed, moving that
  dimension from B+ to A-. The overall grade stays B+ on the two dimensions
  that did not move: cognitive complexity is ungated for the third audit
  running, and nothing enforces the release pull request merging first. One
  new finding, #262. The two earlier reports are left as written. See #262

### Changed

- `ModbusPdu.pack` and `ModbusPdu.unpack` are deprecated and are removed in
  0.6.0. They warn and still work; the packet classes call internal helpers
  and emit nothing. Build the bytes and pass them as `data` instead. See
  #229, ADR-036

### Fixed

- Changing a value on a packet changes the bytes it sends. Every concrete
  class stored each value twice, as the named attribute and as a combined
  payload built once at construction, and only the second was serialized --
  so setting a quantity of 2001 on an FC3 request still emitted a frame
  asking for 10, with nothing raised. The classes now declare their fields
  and derive the payload from them on every read. Two packets carrying the
  same values compare equal, which was broken for the same reason. Assigning
  the derived payload raises and names the fields to set instead. No wire
  output changes. See #228
- A packet built from bytes survives a round trip. It carried the same frame
  as the packet read back from its own output while comparing unequal to it.
  See #229, ADR-036

## [0.4.4] - 2026-09-01

No change to what the library does on the wire. This release carries a
release-cadence decision, a gate over the package's own examples, and five
corrections to statements the tree was making about itself.

### Added

- The package's docstring examples are executed by the default test run. They
  are the part of the documentation a reader is most likely to copy and nothing
  ran them, which is how an example asserting a property its class does not
  provide sat on `main` unnoticed. Three transport examples open a socket to a
  server nothing starts and are exempt by name, one docstring at a time rather
  than by excluding their module, so a fourth example in the same file stays
  gated. See #247

### Changed

- The 360-degree audit is owed before a minor or major release. A patch
  release owes nothing, where every release previously owed either a report or
  a document declining one. See #243, ADR-033

### Fixed

- `ModbusHeader`'s docstring example passes a protocol id of zero, the only
  value a Modbus TCP frame may carry, where it previously passed 2. Both `Args`
  blocks now state that. No behaviour changes. See #232
- The release-audit gate's two coverage floors match the corpora they guard,
  three dated reports and nine release entries, where they sat at two and six.
  A floor below its corpus still catches a total enumeration failure and stops
  catching a partial one. See #249
- `ModbusTcpPacket`'s docstring example asserts what the class provides. It
  compared a hand-built packet against a deserialized one and failed, because
  deserializing yields a generic PDU by design; it now compares the frames,
  which do survive the round trip. No behaviour changes. See #246
- The mypy freeze comment states the count it actually hides, 597 rather than
  594, and says the figure is a dated measurement so the next reader
  re-measures instead of trusting it. See #248
- ADR-032's upstream line names the filing it refers to rather than promising
  one. See #241
- The reason recorded for cutting the changelog entry before the tag names the
  tree the tag points at, which is what the generated source archives carry.
  It named the sdist, which has never carried `CHANGELOG.md`, so the reason was
  falsifiable in one command while the step it justifies is sound. See #207

## [0.4.3] - 2026-08-31

No change to what the library does on the wire. This release carries a gate
change, a decision record and documentation.

### Changed

- The release-audit gate accepts a record dated the day the previous release
  shipped, where it previously required a later one. A record older than that
  release, and no record at all, both still fail. The strict form made two
  releases on one calendar day unreachable, because no record can be dated
  later than today. See #239, ADR-032
- The Python editor guides draw a ruler at 88 columns, ruff's ceiling,
  alongside the one at the preferred width. See #237

### Added

- ADR-031 settles how a packet field constraint enters the library: declared
  per class and queried, rather than enforced by a mode. It records the
  decision only -- the work is #196 and is not in this release. See #227
- PLAYBOOK 1.7, on writing an issue or pull request body for a reader who has
  not seen the code. See #230

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

[Unreleased]: https://github.com/Imbra-Ltd/pyomb/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/Imbra-Ltd/pyomb/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Imbra-Ltd/pyomb/compare/v0.4.4...v0.5.0
[0.4.4]: https://github.com/Imbra-Ltd/pyomb/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/Imbra-Ltd/pyomb/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/Imbra-Ltd/pyomb/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/Imbra-Ltd/pyomb/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Imbra-Ltd/pyomb/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Imbra-Ltd/pyomb/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Imbra-Ltd/pyomb/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Imbra-Ltd/pyomb/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Imbra-Ltd/pyomb/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Imbra-Ltd/pyomb/releases/tag/v0.1.0
