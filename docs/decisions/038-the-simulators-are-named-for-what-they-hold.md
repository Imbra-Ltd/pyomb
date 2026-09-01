---
id: "038"
status: Accepted
date: 2026-09-01
category: repository
supersedes: []
superseded_by: []
---

# ADR-038: The simulators are named for what they hold

**Upstream:** filed as braboj/solid-ai-templates#1404 against
`templates/stack/python-lib.md`. With the domain skin off: a package binding a
public name through a module `__getattr__` already owns the mechanism a
deprecation alias needs, so renaming an exported symbol costs a map entry
rather than a shim module. The template documents the deferral and stops
before that second use.

## Context

Two modules promise a client and a server. Neither holds one.

| Module | Lines | What it holds |
| --- | --- | --- |
| `omb_client.py` | 900 | `OmbClientSim`, `RequestFactory`, `run_client()` |
| `omb_server.py` | 1058 | `OmbServerSim`, `ResponseFactory`, `run_server()` |

Both classes are simulators and every other surface says so. `SECURITY.md`
states it as a scope boundary:

> Both endpoints are simulators intended for testing Modbus implementations.
> They are not hardened for production control networks.

The `omb_` prefix is the second defect and the smaller one. Inside a package
already called `pyomb` it repeats the package name, and it is the last
survivor of the naming pass that settled that name.

### What the rename reaches, measured today

```bash
git grep -c -E 'OmbClientSim|OmbServerSim|omb_client|omb_server' \
  -- . ':(exclude)docs/solid-ai-templates'
```

28 files, 115 lines:

| Surface | Files | Lines | The part an import error would not report |
| --- | --- | --- | --- |
| `src/` | 3 | 17 | logger names, `self.name`, the `_DEFERRED` map |
| `tests/` | 14 | 59 | the leak guard's thread name, the watched-module tuple |
| `examples/` | 2 | 5 | -- |
| `docs/` | 6 | 22 | a merged decision record's frozen-module table |
| `README.md` | 1 | 5 | the project structure tree |
| `CHANGELOG.md` | 1 | 3 | released entries, which are not edited |
| `pyproject.toml` | 1 | 4 | two lint keys, two type-checker module lists |

The string sites are what makes this larger than a rename. A missed import
fails collection; a missed string leaves the leak guard watching a thread
name nothing produces, which passes.

### Two corrections to the issue as filed

The issue asks that the two header TODOs proposing this rename be deleted by
the change resolving them. They were deleted under an hour after it was
filed, by the pass that emptied the header TODO blocks. `git grep -n TODO --
src/` now prints nothing, so that criterion is already met, and not by this
work.

The issue counts ten integration test modules. Fourteen test modules name a
simulator, and two of them do it only in a string.

### What the public contract is today

The package docstring names one equally-public submodule, `pyomb.packets`.
The simulators reach the flat API through the deferred binding instead, so
the two submodules are no longer public. The class names are.

That splits the break in two. Renaming the modules breaks the import form the
suite uses and the README showed before 0.3.0. Renaming the classes breaks
the form documented today.

## Decision

```text
  before                            after
  ------                            -----
  pyomb/omb_client.py               pyomb/client_simulator.py
      OmbClientSim                      ModbusClientSimulator
  pyomb/omb_server.py               pyomb/server_simulator.py
      OmbServerSim                      ModbusServerSimulator

  from pyomb import OmbClientSim         resolves, warns, gone at 0.7.0
  from pyomb.omb_client import ...       ModuleNotFoundError at 0.6.0
```

1. **The modules are named for the simulator each holds.** `omb_client.py`
   becomes `client_simulator.py` and `omb_server.py` becomes
   `server_simulator.py`. Neither file moves in this change.

2. **The classes are renamed with them.** `OmbClientSim` becomes
   `ModbusClientSimulator` and `OmbServerSim` becomes
   `ModbusServerSimulator`. The `Modbus` prefix matches every other name the
   package exports, and `Simulator` is spelled out because `Sim` is an
   abbreviation the domain does not use unexpanded.

3. **`RequestFactory` and `ResponseFactory` keep their names.** Each is
   accurate, neither is exported from the package root, and renaming a name
   that is not wrong is churn.

4. **The old class names resolve until 0.7.0.** Both MUST keep resolving from
   the package root, raising `DeprecationWarning` and naming the new spelling
   and the removal version. The resolver is the `__getattr__` that already
   binds them, so the alias is a map entry rather than a module.

5. **`__all__` advertises the new names only.** A deprecated spelling is
   supported and not recommended, and listing it makes a star import warn
   while presenting both as equally current. The alias therefore needs its
   own test: the check that every advertised name resolves cannot reach a
   name the list omits.

6. **The submodule paths break at 0.6.0 with no alias.** Python resolves a
   submodule import against the filesystem rather than the package
   `__getattr__`, so keeping `pyomb.omb_client` importable means shipping a
   shim module. The submodules are not public, so the shim would preserve a
   guarantee the project does not make.

7. **Re-keying a frozen entry is not widening it.** Two lint keys and two
   type-checker module lists name these modules by path. The rename changes
   the key and MUST NOT change the rule list behind it.

8. **This record precedes the move.** No file is renamed by the change that
   merges it. The rename is its own change, and it carries the string sites
   the table above names.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| `client.py` / `server.py` | Reads as the real thing, which is what the current names already wrongly imply. It renames toward the wrong meaning rather than away from it. |
| One `simulators.py` holding both | There is no real client and no real server for it to sit beside, so the module name would carry the distinction alone. It also puts 1958 lines in one file, undoing a separation the tree already has. |
| A `simulators/` sub-package | The closest to a full answer, and it names the concern once in the directory rather than twice in the filenames. It creates a directory no requirement asks for, and the codec and the transport are flat modules, so the package would be asymmetric for a naming gain. |
| `ModbusTestClient` / `ModbusTestServer` | What the two deleted TODOs proposed. It names the purpose rather than the thing, and a Modbus test client is what a reader would call a real client used for testing -- the confusion this decision exists to remove. |
| `ModbusClientSim` / `ModbusServerSim` | Shorter, and the smallest edit from the current names. `Sim` is an abbreviation the specifications never use, and length is not the constraint here: the longest name this adds is 21 characters against an existing 40. |
| A clean break with no alias | Cheap. The distribution reaches no package index, so a consumer is whoever downloaded a release artifact, and the changelog would carry it. It buys nothing: the resolver that would raise `AttributeError` is the same one that can return the class and warn. |
| The old names stay in `__all__` | Honest for a release where they still work. It also makes the export list advertise two spellings for one class, and a star import then warns for names the caller never asked for. |

## Consequences

- The implementing change touches 28 files. Fourteen are test modules, and
  the two string sites in them fail silently rather than loudly.
- 0.7.0 inherits an obligation to delete the aliases, the alias test and the
  rule above. Nothing watches it except the milestone.
- A merged decision record's table names both modules by their old paths.
  It is immutable and goes stale, and it is deliberately not edited.
- The changelog's released entries name the old class names. They record what
  those releases shipped and stay as written.
- The two issues waiting on this record can start. Both break the same public
  API, so they want the same release.
- A caller who wrote `from pyomb.omb_server import OmbServerSim` gets a
  `ModuleNotFoundError` at 0.6.0 rather than a warning. That is the loud
  failure, and the changelog is where it is announced.
- The deferral survives the rename and so does the measurement behind it. The
  `_DEFERRED` map gains a sibling rather than a replacement.

## Related

- Issue #173 -- the spike this record answers
- Issues #192 and #194 -- the simulator surfaces that follow it
- ADR-002 -- the naming pass whose last survivor is the `omb_` prefix
- ADR-005 -- the frozen-module table that names both modules by path
- ADR-035 -- the record that unblocked the three simulator issues
