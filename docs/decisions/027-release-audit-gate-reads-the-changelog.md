---
id: "027"
status: Accepted
date: 2026-08-29
category: release
supersedes: []
superseded_by: []
---

# ADR-027: The release-audit gate reads the changelog, not the tags

**Upstream:** filed as `none`. The general shape is reusable: a gate needing
the date of the last release reads the project's own dated record rather than
git tags, because a shallow CI checkout carries none. One project meeting this
once is not evidence it generalizes; revisit if a second project hits it.

## Context

PLAYBOOK 5 step 2 says to run a 360-degree audit before a release. Four
releases were cut without one. Only the fourth skip was written down, in a
release pull request, and the first three left no trace at all.

The step reads as followed because its neighbours are gated. Step 4 fails until
the changelog entry is cut, step 5 until the README names the new wheel. An
operator running the sequence top to bottom feels the procedure checking the
work.

The obvious input for a gate is git tags: compare the newest audit against the
previous tag's date. CI cannot read them. The `test` job in `ci.yml` declares
no `fetch-depth`, so it takes the checkout action's shallow default and no tags
arrive with it.

A tag-based rule would find nothing in CI and report a clean tree from it. That
is the failure mode where a check runs, exits zero, and has measured an empty
set.

## Decision

1. **The changelog is the in-tree record of what shipped** -- the gate reads
   its dated `[X.Y.Z]` entries and never calls `git tag`. Every release writes
   one on the release branch, so the record is complete at any checkout depth.
2. **The newest audit MUST postdate the previous release, strictly** -- an
   audit dated the day that release shipped cannot be told from one written
   before it, and refusing both costs an operator one audit.
3. **The gate is unconditional** -- it detects no release branch. Its
   comparison tightens only when a new dated entry appears, which is step 4, so
   it stays silent between releases and fails on the branch cutting one.
4. **A skip is a document** -- a dated `-skipped` record naming the release and
   the reason clears the gate. Declining the step stays available; passing over
   it in silence does not.

```text
  docs/audits/                    CHANGELOG.md
  +---------------------+         +---------------------------+
  | YYYY-MM-DD-360.md   |         | ## [X.Y.Z] - YYYY-MM-DD   |
  | YYYY-MM-DD-360-     |         | ## [W.V.U] - YYYY-MM-DD   |
  |   skipped.md        |         +-------------+-------------+
  +----------+----------+                       |
             |                                  |
             | newest date       the entry after the reported version
             |                                  |
             +---------------+------------------+
                             |
                     newest > previous  ->  pass
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Compare against `git tag` or `git describe` | CI checks out shallow and fetches no tags, so the comparison reads an empty set and passes. Fetching tags in every job pays on every run for a weaker rule |
| Detect the release branch by name | A pull request is checked out detached, so the branch name is not reliably readable in CI. The version bump is the better signal and needs no name |
| Compare non-strictly, failing only when the audit predates the previous release | An audit dated the day that release shipped would then cover two releases, and nothing distinguishes it from one written the morning before |
| Mark step 2 unenforced in the PLAYBOOK instead | Honest, and the weaker of the two options the issue offered. It records that nothing checks the step rather than checking it, and four skipped releases are what that already produced |

## Consequences

- `tests/test_release_audit_is_current.py` carries the rule, its two coverage
  assertions and its negative controls.
- `tests/changelog.py` holds the section and link readers, which two gates now
  share rather than each parsing the same file.
- A release cut without a current audit fails CI on the release branch, before
  the tag rather than after it.
- The rule depends on the changelog entry carrying a date. That is gated
  beside it, so the dependency adds no new way to fail quietly.
- An audit is owed roughly once per release, which is more often than PLAYBOOK
  4.4 asked for before. A release that does not want one writes the skip
  record, so the cost of declining is a paragraph.
- The two floors this gate asserts are sized from a corpus that only grows, so
  neither needs a margin and both fail loudly if the enumeration breaks.

## Related

- ADR-022 -- the coverage-floor pattern this gate's enumeration tests follow.
- Issue #206 -- the four stale releases, and the two halves it separated.
