# ADR-003: Freeze existing lint violations per file

**Status:** Accepted
**Date:** 2026-08-17
**Upstream:** `templates/base/workflow/quality-gates.md` describes a ratchet for
cognitive complexity but not for a linter retrofit — filed as
braboj/solid-ai-templates#1014

## Context

`CLAUDE.md` and `templates/stack/python-lib.md` name ruff as the linter. CI ran
flake8 with a configuration that suppressed `F403`/`F405` globally, so the star
imports were invisible and every other rule family was simply absent.

Pointing ruff at the tree over the rule selection those documents imply
produces 2388 findings, 1497 of them after exempting the test suite from the
docstring rules. They are almost all legacy: undocumented public methods,
`.format()` calls that predate f-strings, `super(Class, self)`, unsorted
imports.

Three things constrain what may be done about them:

- `CLAUDE.md` states that every rule binds new and modified code, and that
  untouched code is not to be rewritten outside a tracked migration.
- A 2388-finding cleanup inside a gate change would bury the gate change, and
  no reviewer could separate a mechanical rewrite from a behavioural one.
- Suppressing the offending rule families globally, which is what the flake8
  configuration did for `F403`/`F405`, leaves new code ungated on exactly the
  rules the project says it wants.

The third is the trap. It looks like the cheap option and it is the one that
never ends, because nothing ever fails and so nothing is ever fixed.

## Decision

Enable the full rule selection, and record the violations that exist on the
day of adoption in a generated `per-file-ignores` table in `pyproject.toml`.
Each file is listed with exactly the rules it broke that day.

```text
                  rule in the file's frozen entry?
                     |                    |
                    yes                   no
                     |                    |
              gate stays quiet      gate fails
                     |                    |
   +-----------------+                    +------------------+
   |                                                         |
   a legacy violation, already                  a new violation, or any
   counted, unchanged                           violation in a new file
   (existing file cannot get worse)             (new file has no entry, so
                                                 it is gated on everything)
```

The table is generated from `ruff check --output-format=json`, never curated by
hand. Shrinking it is the migration: delete the entries naming a rule family,
fix what ruff then reports, and commit both together.

Two rules govern its use, stated in `CONTRIBUTING.md` and `docs/PLAYBOOK.md`:
a file is never added to the table to make the gate pass, and an existing entry
is never widened.

ruff is pinned to a minor range, because the table records one version's
findings and a release that adds rules to an already-selected family would fail
the gate on untouched code.

## Alternatives considered

- **Fix all 2388 first** — rejected. Contradicts the rule that untouched code
  is not rewritten, and buries the gate change under a mechanical diff no
  reviewer can separate from a behavioural one.
- **Ignore the offending families globally** — rejected. Leaves new code
  ungated on the rules the project says it wants. This is the flake8
  arrangement that hid the star imports, reproduced at fifteen times the
  scale.
- **Select only the rules the tree already passes** — rejected. Same effect as
  above, and the selection then encodes the legacy state rather than the
  target, so nobody can see what is owed.
- **Keep flake8 and add ruff beside it** — rejected. Two linters in one
  category, which `quality-gates-constraints` rules out, and flake8 cannot
  read `pyproject.toml`, so the configuration stays split.

## Consequences

- New files are held to the whole rule selection from their first commit, which
  is what matters for the rewrite `CLAUDE.md` anticipates.
- Existing files are pinned at their current state and cannot degrade.
- The table is an explicit, measurable backlog. Its size is the debt, and a
  cleanup is reviewable on its own because the gate change already landed.
- A file-level freeze does not newly gate an existing file when it is edited.
  That is the known cost of freezing at file granularity, accepted because the
  alternative is freezing at line granularity, which no ruff mechanism offers
  and which would churn on every edit.
- The ruff pin has to be bumped deliberately, and a bump may require clearing
  or re-freezing findings from newly added rules.
- `ruff format` is a separate question and is not adopted here; it would
  rewrite 53 of 56 files.

## Related

- #38 — wire the quality gates, of which this is the lint part
- #41 — whether to adopt `ruff format`
- #14 — the star imports, whose `F403`/`F405` entries this table now carries
- ADR-002 — the name and layout this configuration is written against
