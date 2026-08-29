---
id: "028"
status: Accepted
date: 2026-08-29
category: repository
supersedes: []
superseded_by: []
---

# ADR-028: Vendor specifications live in docs/specs

**Upstream:** filed as `none`. The general convention -- third-party reference
material sits in its own subdirectory, separate from the documents a project
authors and maintains -- is reusable, and the upstream docs template sets the
standard document set without saying where borrowed material goes. One project
wanting this once is not evidence it generalizes; revisit if a second does.

## Context

`docs/` held eleven entries of five different kinds with nothing grouping
them. Four published PDFs, an imported tutorial, three guide documents, two
directories of project records, and a submodule.

The four PDFs are 2.18 MB of that. They are not shipped, because the sdist
include list names `/src/pyomb`, `/tests`, `/README.md` and `/LICENSE` and
nothing else, so the cost is reader attention rather than artifact size.

The directory gave the same visual weight to a 1996 Modicon reference guide
and to `PLAYBOOK.md`. Nothing distinguished material this project wrote from
material it borrowed.

One PDF was undeclared. `PI_MBUS_300.pdf` appeared on no list in the context
file, and outside the submodule it was named in exactly one place -- a test
fixture recording a known-binary path. Its cover page identifies it as the
Modicon Modbus Protocol Reference Guide, PI-MBUS-300 Rev J.

## Decision

1. **Borrowed material lives in `docs/specs/`** -- the four published
   specification PDFs and the imported protocol tutorial. It is material this
   project reads and does not maintain.
2. **The project's own documents stay at the top level of `docs/`** -- the
   guides, the journal, the decision records and the audit reports. What
   separates the two is authorship, not file type.
3. **The fourth PDF is declared, not deleted** -- the context file's
   specification list names all four, PI-MBUS-300 included. A file the
   repository carries and no document mentions is the state this record
   removes.
4. **There is no `docs/` index** -- the README's "Project structure" section
   maps the tree and is the single source of truth for it. A second index in
   `docs/` would be a copy that drifts, and the upstream docs template
   requires none.

```text
  docs/
  +-- ONBOARDING.md          written here
  +-- PLAYBOOK.md            written here
  +-- dev-journal.md         written here
  +-- decisions/             written here
  +-- audits/                written here
  +-- specs/                 read here, maintained elsewhere
  |   +-- 4 published PDFs
  |   +-- Open_Modbus_Tutorial.md
  +-- solid-ai-templates/    submodule, governed by its own repository
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Delete `PI_MBUS_300.pdf` as unreferenced | It is a genuine Modbus specification and the earliest of the four. 176 KB is a low price for the reference that defines the function codes the others assume |
| Add a `docs/README.md` index | A second map of the same tree, drifting from the README's the first time either is edited. The tree is eight entries and reads without one |
| Name the directory `docs/vendor/` | Accurate for the PDFs and wrong for the tutorial, which is imported prose rather than a vendor document. `specs` is what a reader looks for |
| Leave the layout flat and document the kinds instead | Prose describing a pile does not stop it being a pile, and the next document added would land in the same undifferentiated list |

## Consequences

- Two test fixtures named the pre-move paths and are updated in the same
  change. One is a width exemption that fails loudly, and one is a control
  string that would have gone stale silently -- the second is the reason the
  move and the fixture edit cannot be separate changes.
- The README structure block, its document table, the context file, the
  onboarding guide and the playbook all name the new paths.
- One merged decision record names the tutorial's pre-move path. It is left as
  written: a merged record's claims are fixed, and the width gate reads its
  exemption from the test rather than from the record, so nothing depends on
  the stale path.
- Adding a specification is now an unambiguous placement rather than a
  judgement call, which is most of what the grouping buys.
- The four PDFs stay in the repository and in its clone size. Grouping them
  does not make them smaller, and moving them out of version control would
  break the one property that makes them useful -- being there.

## Related

- ADR-018 -- the width rule and the tutorial exemption whose path this moves.
- Issue #175 -- the entry inventory and the two constraints on the fix.
