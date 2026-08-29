---
id: "030"
status: Accepted
date: 2026-08-29
category: repository
supersedes: []
superseded_by: []
---

# ADR-030: Design notes live in docs/design

**Upstream:** filed as `none`. The general convention -- a repository needs a
home for what it is considering, separate from what it has decided -- is
reusable, and the upstream docs template names homes for decisions, history and
operations but not for proposals. One project wanting this once is not evidence
it generalizes; revisit if a second does.

## Context

`docs/` already separates four kinds of material. `decisions/` holds what the
project decided, `dev-journal.md` what it did, `specs/` what it borrowed, and
`audits/` what it measured on a date.

An architecture direction document arrived that is none of them. It proposes
four operating modes, a six-layer architecture and a roadmap, and the project
has adopted none of it. Filing it under `decisions/` would assert a decision
nobody took; leaving it untracked makes the review that produced its findings
cite a file no other reader can open.

## Decision

1. **`docs/design/` holds design notes** -- proposals and direction documents
   the project has not adopted.
2. **A design note binds nothing.** Where one disagrees with a decision record
   or the context file, those win.
3. **Adopting part of a note takes a decision record.** The note is not edited
   to record the adoption, and is not a second place to look for a rule.

```text
  docs/
    decisions/     what the project decided      binding
    design/        what it is considering        not binding
    audits/        what it measured on a date    observation
    specs/         what it borrowed              external
    dev-journal.md what it did                   history
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the note untracked | Cheapest, and it makes the review citing its findings point at a file nobody else can read. A document that a tracked issue argues about belongs in the tree. |
| Put it at `docs/design_notes.md`, with no directory | No new directory and no record needed, which is the whole appeal. It also hands the first note a name the second one has to share or break, and the split above is the thing worth stating once. |
| File the findings as issues and discard the note | The findings are already issues. The direction behind them is an 874-line argument that does not fit an issue body and is not a decision either. |

## Consequences

- A reader can mistake a note for a decision. Rule 2 is the only thing that
  prevents it, so a note that grows binding language is a defect in the note.
- The first note ships with known corrections outstanding. Its roadmap and its
  testing section are wrong as written, and the record of that is the tracked
  review rather than an edit to the note.
- The directory is scope for design notes only. A note that becomes binding
  leaves it for a decision record rather than being annotated in place.

## Related

- Issue #224 -- the review of the first note, and the findings it answers.
