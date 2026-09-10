---
id: "056"
status: Accepted
date: 2026-09-10
category: repository
supersedes: ["038"]
superseded_by: []
---

# ADR-056: The simulator modules drop the simulator suffix

## Context

A prior record named the client and server simulator modules for what they
hold: `client_simulator.py` and `server_simulator.py`. It considered and
rejected folding them into a `simulators/` sub-package, because no such
directory existed yet. Creating one was "a directory no requirement asks
for," and it would have left the package asymmetric against the then-flat
modules holding the codec and the transport.

A later record split those flat modules into packages of their own and
moved the two simulator files into a `simulators/` directory it created for
them, without revisiting their names. The premise the earlier record
rejected the sub-package on no longer holds, and the result is a name
repeated twice: `simulators/client_simulator.py`.

## Decision

1. **Drop the suffix.** `client_simulator.py` becomes `client.py`;
   `server_simulator.py` becomes `server.py`. The directory name already
   carries the word.
2. **Nothing else about the prior naming call changes.** The class names
   (`ModbusClientSimulator`, `ModbusServerSimulator`), `RequestFactory`,
   `ResponseFactory`, and the deferred-binding mechanism that resolves them
   from the package root are unaffected.
3. **No forwarding shim.** The submodule import path was never the public
   contract -- only the class names, resolved through `__getattr__` from
   the package root, are. Renaming the file changes an internal path a
   caller was never told to depend on.
4. **The old submodule paths break immediately, with no deprecation
   window.** `pyomb.simulators.client_simulator` and
   `pyomb.simulators.server_simulator` are gone as of this change. Anyone
   who imported either directly gets `ModuleNotFoundError`; the changelog
   states the new path.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the current filenames | The redundancy is real, and the constraint that justified them no longer exists |
| Carry a forwarding shim for the old submodule paths, as the flat-to-package move did | That move broke a path the project had documented as importable; this one breaks a path the project had already stated was not public |
| Rename the classes too, since the module names are changing | The class names were not the defect this record addresses, and renaming a name that is not wrong is churn |

## Consequences

- `src/pyomb/simulators/__init__.py` and `src/pyomb/__init__.py` resolve the
  same public names through updated internal paths; nothing observable from
  `import pyomb` changes.
- Every direct import of the old submodule path -- the test suite, the
  playbook -- breaks and needs updating in the same change.
- `complexipy-snapshot.json` re-keys its two frozen entries to the new
  filenames; the recorded values are unchanged.

## Related

- #440
