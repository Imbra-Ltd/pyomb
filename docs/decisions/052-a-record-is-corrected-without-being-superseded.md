---
id: "052"
status: Accepted
date: 2026-09-08
category: process
supersedes: []
superseded_by: []
---

# ADR-052: A record is corrected without being superseded

**Upstream:** filed as `none` for now, because the rule set this would
target is being reworked to require fewer records. With the domain skin
off: a corpus of immutable records carrying one relation between them
uses it for two different acts. Marking a record replaced in order to
withdraw one of its claims tells every later reader that the decisions
still standing in it are dead.

## Context

A decision record here is immutable once merged. A claim inside one that
turns out to be wrong is corrected by writing a new record, never by
editing the record that carries it and never by appending to it. That is
right for a decision that changed and wrong for a decision that did not.

### What the directory holds, measured today

| Claim | Command | Result |
| --- | --- | --- |
| The corpus | `ls docs/decisions/[0-9]*.md \| wc -l` | 51 records |
| Written since 2026-08-17 | `grep -h "^date:" docs/decisions/[0-9]*.md \| cut -c7-13 \| sort \| uniq -c` | 31 in August, 20 in September |
| How they are labelled | `grep -h "^status:" docs/decisions/[0-9]*.md \| sort \| uniq -c` | 46 Accepted, 5 Superseded |
| Nothing indexes them | `ls docs/decisions/ \| grep -vc "^[0-9]"` | 1, the template |

Fifty-one records in twenty-three days. A reader looking for what governs
a subject reads filenames, so a status is the strongest signal a record
carries about whether it is worth opening.

### Two acts, one relation

Two corrections have already happened here, and each took a different
route because only one route was available.

The first withdrew an evidence table from the record that adopted the
platform scanner. Four of that record's five decisions are live, the
correcting record says so in its own Decision section, and the corrected
record is marked `Superseded` regardless.

```bash
git grep -l "ADR-012" -- . ':!docs/solid-ai-templates' | wc -l    # 10
```

Ten tracked files name it: three audit reports, the journal, the
playbook, the changelog, the context file and two other records. Every
one of those pointers resolves to a document labelled dead.

The second narrowed one rule of the record that refuses a design note's
vocabulary. That corrected record keeps `status: Accepted`, which is
right, and nothing in it points at the narrowing. Its own author recorded
the cost: a reader of the narrowed rule does not meet the record that
narrows it.

So the corpus carries both failures at once. Where a link exists it says
the wrong thing, and where it would say the right thing it does not
exist.

## Decision

| # | Rule |
| --- | --- |
| 1 | A correction is a second relation, carried in the front matter |
| 2 | A corrected record keeps its status and every word it merged |
| 3 | One pair of records takes one relation, never both |
| 4 | The pair is optional, and an absent field means none |
| 5 | The schema check reads a correction from both sides |
| 6 | The record already marked replaced on its evidence stays as merged |

```text
   a claim inside a merged record turns out to be wrong
                          |
          +---------------+---------------+
          |                               |
   a decision in it                every decision
   no longer holds                 in it still holds
          |                               |
          v                               v
   supersedes / superseded_by      corrects / corrected_by
   status -> Superseded            status unchanged
          |                               |
          +---------------+---------------+
                          |
              both are front matter, and the
              schema check reads each side
```

### 1. The relation is metadata

Front matter is the source of truth for how records relate, and it is the
one part of a merged record this project already edits. Recording a
supersession updates both sides after both have merged. A correction is
the same kind of edit and takes the same narrow exception.

Two fields carry it. `corrects` lists the records a record corrects, and
`corrected_by` lists the records that correct it. Both hold zero-padded
ids, quoted, in the form the two link fields already use.

### 2. What a correction may change

A correction withdraws a claim a record argues from, or narrows how far
one of its rules reaches. Every decision in the corrected record still
holds, so its status stays `Accepted` and not one word of its prose
moves.

The test is whether a reader acting on the corrected record today would
act wrongly. Where they would, a decision has changed and the existing
relation is the right one.

### 3. One pair, one relation

A record does not both replace and correct the same record. Naming one
record in `supersedes` and in `corrects` says its decisions are dead and
live at once, so the check refuses the pair rather than picking a
meaning.

### 4. Absent means none

Both fields are optional, unlike the supersession pair, which every
record carries even when empty. Requiring them would cost fifty-one
metadata edits against a field that is empty in all but two of them.

What that buys is a distinction between "not corrected" and "correction
not considered", and nothing consumes it. A reader meets the field on the
records where it has something to say.

### 5. Both directions are checked

`checks/test_decision_frontmatter.py` already fails a supersession named
from one side only. It gains the same assertion for a correction, and one
refusing a pair of records that carries both relations at once.

The gate goes where the pair is rather than into a module of its own. It
reads the same corpus and parses the same block, so a second module would
duplicate both and give a reader two places to look.

### 6. The record already marked replaced stays as merged

One record is marked `Superseded` for a correction to its evidence alone.
Under rule 2 it would read `Accepted` today, and it stays exactly as it
merged.

The record that corrected it states in three places that it supersedes
it, and that the corrected record's status flips. Editing metadata to
satisfy this rule would leave immutable prose contradicting the front
matter beside it, which is worse than the label it repairs.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Leave the rules as they are | Nothing to build, and it keeps both observed failures: a live record labelled dead, and a correction that no reader of the corrected record meets. At two records a day the label is what a reader navigates by, so a wrong one costs most here. |
| An errata file keyed by record id | One file, appended to, and every record stays byte-identical. It adds a second document class to a directory four gates already read, and a reader of a record still meets nothing unless something links the two -- so it needs this record's mechanism anyway. |
| A dated correction written inside the corrected record | The reader meets the correction where the error is, which is the strongest possible placement. It also edits a closed record, which the inherited rule forbids outright, and it destroys the evidence of what was believed on the day the record merged. |
| A front-matter field listing issue numbers | Cheapest to add, machine-readable, and it puts a durable correction in the tracker. The tracker is a view over the code host and has to be replaceable without losing anything, and one of the two corrections here already sits in a closed issue. |
| Require the pair on every record, empty by default | Consistent with the supersession fields, and honest about absent versus empty. It costs fifty-one metadata edits across immutable records to separate two states that nothing reads apart. |
| Split the class: decisions immutable, observations in findings docs | The mechanism already exists in the bound templates and needs no schema change at all. It reaches only records written afterwards, and both corrections here are about records that merged before the question was asked. |

## Consequences

- The pair of records behind the second correction gains the fields, so a
  reader of the narrowed rule now meets the record that narrows it. That
  is the first link of its kind in this corpus.
- A correction still costs a record. What changes is what the corrected
  record says about itself, which is the half the rate makes expensive.
- The schema grows two optional fields and the check grows two
  assertions. No record is migrated, and no gate outside the schema check
  reads either field.
- A reader of the one record marked replaced on its evidence still meets
  a dead label. Rule 6 pays that cost rather than making metadata
  contradict prose that cannot be edited.
- Nothing detects a correction that is never recorded. A person writing a
  record that withdraws a claim is what sets the field, which is the same
  gap every revisit trigger in this corpus has.
- The project carries a further recorded divergence from the pinned
  templates, which route a refuted premise to the issue and the pull
  request and give the corrected record nothing. A reconciliation that
  touches those rules must say whether this one still holds.

## Related

- ADR-019 -- the front-matter schema these two fields extend, and the
  metadata exception they take
- ADR-017 -- the boundary between an edit that changes a claim and one
  that does not
- ADR-035 and ADR-051 -- the pair the new fields are first applied to
- ADR-012 and ADR-013 -- the supersession rule 6 leaves as merged
- Issue #359 -- the spike this record answers
- Issue #358 -- the correction that sits in a closed issue rather than in
  the record it corrects
