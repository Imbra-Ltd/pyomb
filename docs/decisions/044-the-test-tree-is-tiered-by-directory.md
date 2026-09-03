---
id: "044"
status: Proposed
date: 2026-09-03
category: repository
supersedes: []
superseded_by: []
---

# ADR-044: The test tree is tiered by directory

**Upstream:** candidate, not yet filed, against
`templates/base/core/testing.md`. With the domain skin off: a suite tiered by
directory needs its helpers reachable from every tier, and the import mode
that resolves a bare helper import is the one that refuses two modules sharing
a basename. The rule naming the tier layout states neither constraint, so a
project adopting it meets both at the moment files move.

## Context

The suite is one flat directory. Measured on 2026-09-03 with `git ls-files`:
71 test modules and 5 helpers, 12009 lines across the modules.

Three populations share that directory and answer different questions:

| Population | Modules | Lines | What it exercises |
| --- | --- | --- | --- |
| codec and unit | 48 | 6719 | the library, no input or output |
| integration | 7 | 1192 | real sockets and worker threads |
| repository gates | 16 | 4098 | this repository's own conventions |

A bare `pytest` runs all three. Every invocation builds TLS contexts, binds
and accepts on loopback, and scans the tracked Markdown for line width.

The gates are the odd population. They ship inside the source archive,
because the include list carries `/tests` whole. A consumer running `pytest`
against that archive runs this project's Markdown rule over their own
checkout.

Two import facts constrain any layout. Both were measured against pytest
9.1.1, the pinned version, rather than inferred:

- `--import-mode=prepend` puts only a module's own directory on the search
  path. A helper in `tests/` is therefore invisible from `tests/codec/`, and
  the failure is `ModuleNotFoundError` at collection
- The same mode refuses two modules sharing a basename. Collection stops with
  an import file mismatch naming both paths

The second fact is what decides the shape. A layout mirroring the source tree
wants one test module per source module in each tier, and three source
modules carry tests in both tiers, so three basenames would repeat.

## Decision

1. **The tier comes from the directory** — a single collection hook derives
   it. No test carries a hand-written tier marker, so a marker cannot drift
   from where the test sits

2. **`tests/` becomes a package** — an `__init__.py` in `tests/` and in each
   subdirectory. This is what makes a nested layout possible: the package
   root is on the search path, so a module resolves from any depth. It also
   makes a repeated basename legal, which leaves a future mirror open rather
   than foreclosed

3. **Helpers live in `tests/helpers/`** and are imported by dotted path.
   Fourteen bare imports across five helpers are rewritten. Two of the five
   have importers in more than one bucket, so co-locating each helper with
   its callers is not available

4. **The buckets follow the subject, not the import list** — a simulator test
   imports the codec to build a frame, and a transport test imports the codec
   too, so the most specific subject wins

5. **The repository gates leave `tests/` for `checks/`** — they exercise no
   source module and never will. Moving them out stops them shipping, with no
   change to the include list and no exclude pattern to anchor

6. **The import mode stays `prepend`** — the package in rule 2 removes the
   only reason to change it

7. **The default run is the fast tier, and the pipeline names each one** —
   a bare `pytest` opens no socket

```text
  tests/                     default tier -- a bare pytest runs this
    helpers/            5    imported by dotted path from any depth
    codec/             14
    pdu/               13    one module per function code
    transport/         10
    simulators/         7
    integration/        7    opt-in -- opens sockets, starts threads
  checks/              16    the repository, not the library
```

The three remaining subjects are `tls`, `errors` and the package surface, four
modules between them. They stay flat in `tests/` rather than taking three
directories of one or two files.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| One test module per source module | Three source modules carry tests in both tiers, so three basenames repeat and collection stops. It also merges 3828 lines of codec tests into one module |
| Merge the 13 function-code modules into it | They map to sections of the published protocol specification, not to a source file. Spec coverage is the axis a reader navigates by, and one file per code is what keeps it visible |
| `--import-mode=importlib` | Permits the repeated basename and breaks all fourteen bare helper imports. The escape is a search-path edit, which this project's rules forbid in the suite |
| Keep the gates at `tests/gates/` and narrow the include list | The anchoring test reads the include list only, so an exclude added here is covered by nothing |
| Stay flat and gate the heavy tier on markers | A marker drifts from where the test sits, which is the failure deriving the tier from the directory exists to prevent |
| Three directories for the small subjects | Four modules across three directories reads as structure without being any |

## Consequences

- Fourteen helper imports are rewritten in the change that moves the files.
  Both failure modes are loud at collection, so the migration cannot half-land
  and report green
- The manifest comment stating that `tests/` deliberately carries no
  `__init__.py` becomes false and goes in the same change
- Moving the gates breaks two imports of `changelog.py`. The helper moves to
  `checks/` with its only two callers
- The pipeline definition must change, and that path is off-limits. It needs
  its own proposal, carrying a rollback strategy and the coverage that would
  catch a regression, before any file moves
- The source archive stops carrying the gates. A consumer running the shipped
  suite no longer scans their own checkout
- The coverage denominator changes when the gates leave the measured tree, so
  the floor is re-read against the new figure rather than assumed
- The context file states that tests mirror the source tree one file per
  module. At 48 unit modules against 8 source modules that has never held, and
  rule 4 replaces it. The claim is corrected in the same change
- A repeated basename becoming legal is a capability, not a licence. Nothing
  here asks for one

## Related

- Issue #172 — the epic this record answers, carrying the derived split
- Issue #210 — a bind warning from three negative controls, which the
  integration tier collects in one directory
