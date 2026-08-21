# ADR-013: A CodeQL baseline comes from the default branch, not a pull request

**Status:** Accepted
**Date:** 2026-08-21
**Supersedes:** ADR-012
**Upstream:** filed as braboj/solid-ai-templates#1043 against
`templates/base/core/review.md`. With the domain skin off, the convention is
that a measurement taken at the wrong scope answers a different question than
the claim it is offered for — the section already covers a measurement in the
wrong unit and a silently partial extraction, and a diff-scoped tool run is a
third axis that looks like neither.

## Context

ADR-012 adopted CodeQL and chose the `security-extended` suite over the
default one. It chose by measuring, which was right, and recorded this:

| suite | python rules | actions rules | findings |
| --- | --- | --- | --- |
| default | 43 | 17 | 0 |
| `security-extended` | 50 | 23 | 0 |

It then reasoned: thirteen more rules, no additional noise, so take the wider
suite.

Both rows were measured on pull-request refs. CodeQL scopes what it reports on
a pull request to the change, so those zeros meant "this branch introduces
nothing", not "the tree is clean". Minutes after ADR-012 merged, the first
analysis of `main` reported three findings on the same code:

```text
  ref=refs/pull/75/merge   /language:python   rules=50   results=0
  ref=refs/heads/main      /language:python   rules=50   results=3
```

Same suite, same commit, same rule count. The only difference is the scope the
number was computed over.

The three are now #76 — `py/insecure-protocol`, high, in shipped source, on
the library's TLS path — and #77, two medium `py/bind-socket-all-network-
interfaces` alerts. Bandit reports nothing at any of the three sites, which is
the case for running both scanners rather than either.

## Decision

1. The evidence table in ADR-012 is withdrawn. Both of its rows measured a
   diff, so neither is a baseline, and the "no additional noise" justification
   built on them does not stand.
2. `security-extended` is kept, on a different and sounder argument. Extended
   is a superset of the default suite, so it cannot report fewer findings, and
   the first full-tree run under it found a high-severity defect that bandit's
   clean run missed entirely. The suite is justified by what it caught, not by
   what it failed to report on a diff.
3. The baseline for this repository is the first full-tree analysis on `main`:
   three open alerts, tracked as #76 and #77. Every later count is read against
   that, not against zero.
4. A CodeQL count is recorded only with the ref it was computed on. A figure
   with no scope attached gets read as a baseline by whoever finds it next,
   which is exactly how this happened.
5. Everything else in ADR-012 stands unchanged and is not restated here: the
   workflow's isolation, its fan-in, the two languages, and the three bandit
   rules ADR-012 carried forward from ADR-007. This record supersedes ADR-012
   on the evidence, not on the design.

```text
  what a run reports, by ref

  refs/pull/N/merge   ->  findings introduced by this change
                          zero means "adds nothing"

  refs/heads/main     ->  findings in the tree
                          zero means "clean"

  the two are not comparable, and only the second is a baseline
```

## Post-mortem

- **Symptom:** ADR-012 stated that both query suites report zero findings on
  this tree. The tree carries three, one of them high severity in shipped
  source.
- **Root cause:** both measurements were taken from pull-request analyses,
  where CodeQL reports against the diff. The numbers were accurate for what
  they measured and were written up as a property of the codebase.
- **Why missed:** nothing looked wrong. Two suites, two plausible rule counts,
  a consistent zero, and a conclusion that followed from it. The project's
  verification rules prompt for a measurement in the wrong unit and for a
  silently partial extraction; neither asks what population a number covers,
  and a diff-scoped run resembles neither failure. The rule count differing
  correctly between suites made the run look sound.
- **Fix:** this record. The table is withdrawn, the suite is re-justified on
  the finding it produced, and the real baseline is written down with its ref.
- **Prevention:** decision 4 above, and the upstream filing that would have
  caught it. Concretely, the baseline command is the one PLAYBOOK 3.8 already
  prints, and it takes a ref:

  ```bash
  gh api "repos/Imbra-Ltd/pyomb/code-scanning/analyses?ref=refs/heads/main" \
    --jq '.[0] | {category, results_count, ref}'
  ```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Leave ADR-012 as it stands and correct the record on #71 | What the project did for #22, where a closed issue carried the correction. It does not fit here: #22's error was in a ticket, and this one is in an `Accepted` decision record that a future reader would take as measured fact. `base-docs` asks for a same-day supersession precisely when data that should have informed a record refutes it. |
| Edit ADR-012's table in place | Merged ADRs are immutable, and this is a substance change rather than a formatting one. Editing it would also destroy the only evidence of how the mistake was made, which is the part worth keeping. |
| Re-measure the default suite on `main` and repair the table | The honest version of the original comparison, and it needs a full-tree run of a suite the project is not going to adopt. The comparison no longer decides anything: extended is a superset, so it cannot do worse, and it has already earned its place. Buying a number to fill a table is not worth a branch. |
| Drop back to the default suite pending a proper comparison | Would remove the only scanner configuration known to have found a real defect here, on the grounds that the paperwork behind choosing it was wrong. |
| Treat the three alerts as this record's business and fix them here | An ADR is not a fix. #76 and #77 carry them, with reproduction and acceptance criteria; #76's TLS finding needs a test that fails against current code, which is a change of its own. |

## Consequences

- ADR-012's status flips to `Superseded by ADR-013`, one hour after it was
  accepted. That is uncomfortable and correct: the alternative is a record
  stating a measured fact that is not one.
- The repository has a real security backlog for the first time, of three
  alerts. Two are probably intentional and one is not, and #77 exists so that
  "probably intentional" gets written down rather than assumed.
- CodeQL paid for itself inside an hour, on a tree where bandit reports zero at
  full strictness. ADR-007 read that zero as evidence the tree was clean; it
  was evidence that bandit's rule set does not cover TLS configuration.
- PLAYBOOK 3.8 gains the ref on its baseline command, so the next reader
  measures the tree rather than a diff.
- Citations of ADR-012 stay where they are. It is superseded on its evidence
  and remains the record of the design, so pointing a reader at it is still
  correct — decision 5 exists to make that safe.

## Related

- ADR-012 — adopted CodeQL and measured the suite choice on the wrong refs,
  superseded by this one on that point alone
- ADR-007 — the decline this pair of records reopened, and the clean bandit run
  that was read as more than it said
- #76 — the high-severity TLS finding the corrected baseline exposed
- #77 — the two bind-to-all-interfaces alerts awaiting triage
