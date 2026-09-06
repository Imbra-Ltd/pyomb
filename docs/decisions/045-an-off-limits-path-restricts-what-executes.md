---
id: "045"
status: Accepted
date: 2026-09-06
category: process
supersedes: []
superseded_by: []
---

# ADR-045: An off-limits path restricts what executes, not what it says

**Upstream:** candidate against `templates/base/core/git.md`, not yet filed.
With the domain skin off: a rule that gates a path by blast radius should say
which content carries that radius. Every such path holds prose as well, and an
unqualified reading prices a comment fix at a written proposal.

## Context

Section 2.5 declares two paths off-limits and requires a proposal before any
change inside them. The proposal carries a rollback strategy and the coverage
that would catch a regression.

Both reasons given are about execution. A release workflow fires on a tag that
cannot be taken back and no suite runs it. A submodule pointer replaces every
rule the project binds, in a one-line diff nothing else reports.

Neither reason reaches a comment. A workflow's comments are read by people;
the runner never sees them. The pointer is a revision and carries no prose at
all.

The comment-length migration met this in September 2026. Measured on
2026-09-06, before the sweep:

| File | Lines | Comment blocks over the bound |
| --- | --- | --- |
| `ci.yml` | 309 | 16 |
| `release.yml` | 142 | 5 |
| `codeql.yml` | 92 | 7 |

The tracked epic bundled those files with `pyproject.toml` in one slice and
recorded that the slice needs its own proposal. Under the unqualified reading
that is right, and it prices a comment edit at the ceremony a tag-firing
change owes.

That ceremony cannot be paid honestly here. A rollback strategy for a comment
is `git revert`, and the regression coverage is that nothing executes. Writing
either teaches the next reader that a proposal is a form to fill in.

## Decision

1. **The restriction binds executable content** — steps, commands, flags,
   permissions, triggers, action pins and the submodule revision. A change
   confined to comments and prose inside an off-limits path is ordinary work
   and needs no proposal

2. **A directive spelled as a comment is executable** — a tool that reads a
   `#` line changes behaviour when the line changes, whatever it looks like.
   Ownership of the class sits with whoever edits it: check what reads the
   line before treating it as prose

3. **The diff is the classifier, not the file** — a change is prose when
   removing every comment line from it leaves nothing. A diff touching a
   comment and a step is an executable change entire

4. **The summary still names the path** — the reviewer's attention is the
   control that survives this narrowing, and it is the cheap half. The
   pre-pull-request check reads path names rather than content, so it still
   reports the hit, and a prose-only hit is discharged by the summary saying so

```text
  diff inside an off-limits path
            |
            +--> comment lines only ---> name the path in the summary,
            |                            open the pull request
            |
            +--> anything else --------> propose first:
                                           + rollback strategy
                                           + regression coverage
                                           + path named in the summary
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Leave the rule unqualified | Every comment fix in a workflow costs a proposal whose two required parts are unwritable. A ceremony performed on a change that cannot regress trains the next author to perform it on one that can |
| Exempt the whole file class instead of the diff | A workflow is off-limits for what it executes, and that reason does not weaken because an author intends only to touch comments. The diff is what is reviewed, so the diff is what the rule reads |
| Automate the classification as a gate | A hit is an escalation trigger rather than a failure, so the surrounding check is deliberately ungated. Adding a gate here re-decides that, and a comment-versus-directive call is a judgement in any case |
| Strip the workflow comments entirely so the question never arises | The file then explains nothing where it is read. A comment at the step is what stops the next author deleting a flag that carries a measured reason |
| Record nothing and narrow section 2.5 alone | The section holds one rule per line and cannot carry why execution is the axis. The next reader restores the unqualified wording, which is what a record exists to stop |

## Consequences

- A prose-only change inside an off-limits path is a branch like any other,
  still named at the top of its summary
- The proposal is reserved for changes that can break something, which is what
  makes it worth writing when one arrives
- The narrowing depends on a judgement no check makes: whether a `#` line is
  read by a tool. A project adding a comment-directive linter inherits a class
  of lines that look like prose and are not
- Section 2.5 states the restriction unqualified today and is corrected in the
  same change, so the declared list and this record cannot disagree
- The comment bound now reaches the workflows through the configuration corpus
  of `checks/test_comment_length.py`, so a long block there fails a gate rather
  than waiting for a migration slice

## Related

- ADR-023 — the record that declared the two paths and the proposal step
- Issue #320 — the comment-bound epic whose last configuration slice met this
