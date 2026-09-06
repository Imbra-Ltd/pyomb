---
id: "048"
status: Accepted
date: 2026-09-06
category: tooling
supersedes: ["005"]
superseded_by: []
---

# ADR-048: The type freeze is retired

**Upstream:** filed as braboj/solid-ai-templates#1572 against
`templates/base/workflow/quality-gates.md`. The generic
rule: a checker's retrofit freeze is retired in the dependency order of
what it suppressed, because a caller's findings do not clear while the
callee is unannotated, and the count alone does not show that order.

## Context

The freeze was four `[[tool.mypy.overrides]]` blocks, each switching off
two codes for one module: `no-untyped-def`, a definition missing
annotations, and `no-untyped-call`, typed code calling an untyped one.

Emptying all four and rerunning the checker reported 514 errors:

```bash
mypy --no-incremental
```

By module, `packets.py` 330, `client_simulator.py` 81,
`server_simulator.py` 80, `stream.py` 42. Two codes only, and no third
kind of finding underneath them.

The order was not free. `no-untyped-call` is raised at the caller, so a
caller cannot clear while what it calls is unannotated. The slices
therefore followed the import graph rather than the error count.

## Decision

1. **Annotate every module and delete the table.** The blocks came off
   in four slices, in import order: the codec, the transport, then the
   two simulators, which import both and neither imports the other.

2. **Take the annotations from the contracts already written down.** The
   docstrings documented the types; the slices made them checkable
   rather than inventing them.

3. **Treat what the checker then reports as findings.** Filling in the
   signatures left a residue in every slice, and none of it was
   cosmetic:

   - a payload defaulting to `None`, which `len()` could not measure
   - an abstraction declaring instance methods that its one
     implementation and every caller used as classmethods
   - a local holding the payload on one path and the error text on
     another
   - a response variable typed by whichever branch came first

4. **Say where the checker cannot follow, rather than widening a type.**
   Two dispatches read a runtime tag the annotation cannot see: a
   function code selecting a request class, and a `try`/`except
   TypeError` asking whether a payload iterates. Both are narrowed at
   the site with `cast`, under a comment naming what guarantees it.

```text
       514 errors                      the order they came off in
  +------------------+
  | packets      330 |   ---->  packets ---> stream ---> simulators
  | client        81 |            330          42          161
  | server        80 |
  | stream        42 |          a caller cannot clear while the
  +------------------+          callee is still unannotated
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| One slice per module in error order | Puts the two simulators before the codec they call, so most of their findings do not clear and the slice reads as a failure. |
| Annotate with a permissive alias where the checker complains | Hides the same findings the freeze hid, behind a type instead of a config block. The public API bans it outright. |
| Keep the blocks and add annotations under them | The block suppresses the analysis, not the finding, so nothing would report that a module had become clean. |
| Take both freezes in one change | A gate that got cleaner and a gate that got stricter produce the same diff, and the lint table came off first for that reason. |

## Consequences

- Every module under `src/` is measured by `mypy --strict`, and a new one
  is held to it from its first commit without a configuration change.
- The residue those slices surfaced is fixed rather than recorded, so
  the behaviour changed in three small ways:

  - an empty payload where a PDU built with none held `None`
  - a parser abstraction whose two operations are classmethods
  - an FC15 request that consumes a generator once rather than
    half-reading it
- Two dispatches now carry casts. They mark a real weakness rather than a
  checker limitation: a caller that re-registers a function code breaks
  the tie the cast asserts.
- The table can no longer be regenerated, because rebuilding it would
  need the findings it suppressed and they no longer exist.
- Both retrofit freezes this project carried are now gone.

## Related

- #170 -- the epic that carried both freezes
- ADR-047 -- the lint half, retired first for the reason above
