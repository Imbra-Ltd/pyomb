# ADR-004: Adopt ruff format across the tree

**Status:** Accepted
**Date:** 2026-08-18
**Upstream:** the AST-equivalence proof below is reusable —
`templates/base/core/testing.md` covers fingerprinting a refactor's output but
not proving a formatter's rewrite mechanical. Filed as
braboj/solid-ai-templates#1019.

## Context

ADR-003 adopted ruff as the linter and deliberately left `ruff format` out of
scope. Adopting it rewrites 53 of the 56 tracked Python files, and three
reasons argued for thinking first: it churns `git blame` across the whole
codebase days after a history rewrite had already cost the project its
provenance once; `CLAUDE.md` says every rule binds new and modified code, not
untouched code, and a blanket reformat is the opposite of that; and the
per-file lint freeze already contains formatting drift on untouched files
without rewriting them.

Against that, `templates/stack/python-lib.md` makes `ruff format --check` a CI
MUST, and Format has been the one mandated gate with nothing behind it. A
stated constraint with no check is decorative: it looks enforced and decays
silently, which is the failure `quality-gates-pair-check` names.

The two open risks were measured rather than argued.

- Running `ruff format` leaves `ruff check` green. No frozen entry needs
  widening, which ADR-003 forbids outright.
- The freeze shrinks from 220 rules to 205 across the same 54 files. The
  formatter clears D210, D208, D201, D214 and UP025 on its own, which is the
  direction ADR-003 calls the migration.
- The rewrite is mechanical. Parsing every tracked Python file before and
  after and comparing the syntax trees — with whitespace inside string
  constants collapsed, because the formatter re-indents docstring bodies — 55
  of 56 files produce an identical tree. `errors.py` differs only by losing a
  redundant `u` prefix on an empty string literal, which Python 3 ignores.

The cost was blame churn, which no measurement removes. The risk was an
unknown interaction with the lint freeze, which the measurement did remove.

## Decision

Adopt `ruff format`. Land it as two commits on one pull request: the rewrite
alone, then the gate and the regenerated freeze.

```text
   commit 1                      commit 2
   ruff format                   ruff format --check in CI
   53 files rewritten            freeze regenerated, 220 -> 205
        |                              |
        v                              v
   reads as the mechanical        from here an unformatted file
   change it is; 55 of 56         fails the pull request, so the
   files parse to an              tree cannot drift back
   identical syntax tree
```

The split is the point. A reviewer can confirm the 1095-insertion diff is
mechanical without also holding a configuration change in their head, and the
gate commit is small enough to read closely.

## Alternatives considered

- **Format only the files a change already touches** — rejected. No ruff
  mechanism does this, so it means running the formatter by hand and
  remembering to. `--check` can never be wired in while the tree is mixed, so
  the mandated gate would stay unwired indefinitely and the convention would
  rest on reviewer attention. That is the decorative constraint above, chosen
  deliberately.
- **Defer to the rewrite `CLAUDE.md` anticipates** — rejected. The cost is the
  same whenever it is paid, so this only defers it, and the rewrite has no
  date. Every change until then is reviewed against a tree the project has
  already decided to reformat.
- **Adopt the formatter but leave the gate off** — rejected. It buys the blame
  churn without buying the guarantee, which is the worst of the two.
- **Reformat and regenerate the freeze in one commit** — rejected. The
  mechanical diff would bury the configuration change, which is the same
  reasoning that kept the 2388-finding cleanup out of ADR-003's gate change.

## Consequences

- `git blame` on every reformatted line now points at the format commit.
  `git blame --ignore-rev` against that commit's hash recovers the previous
  attribution, and `.git-blame-ignore-revs` would make it automatic if the
  churn proves to be a nuisance in practice.
- Formatting stops being reviewable material. A pull request cannot carry a
  formatting argument, because the formatter has already settled it.
- The freeze got smaller for free. 15 of the 220 frozen rules were formatting
  violations the formatter fixes, so the lint debt is now 205 and none of the
  reduction cost a hand edit.
- The ruff pin in `pyproject.toml` now covers formatting as well as linting. A
  release that changes the formatter's output would fail the Format gate on
  untouched code the same way a new lint rule would, so the pin has to be
  bumped deliberately and may require a re-format commit.
- Contributors need `ruff format` before pushing, not just `ruff check`.
  `CONTRIBUTING.md` and `docs/PLAYBOOK.md` state both.

## Related

- #41 — the question this answers
- ADR-003 — the lint half, whose freeze this shrinks and does not widen
- #38 — wire the quality gates, of which Format is one row
