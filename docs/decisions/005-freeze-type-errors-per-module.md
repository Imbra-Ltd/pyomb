---
id: "005"
status: Accepted
date: 2026-08-18
category: tooling
supersedes: []
superseded_by: []
---

# ADR-005: Freeze existing type errors per module

**Upstream:** the same retrofit-ratchet shape ADR-003 already filed upstream as
braboj/solid-ai-templates#1014, so this went there as a comment rather than a
second issue. The refinement it contributes is that a retrofit freezes at the
granularity of the finding, never of the analysis producing it. Disabling a
strict sub-flag also stops the checker looking, which would have discarded the
findings in #51 instead of recording them.

## Context

`CLAUDE.md` and `templates/stack/python-lib.md` name `mypy src/ --strict` as
the type gate. Nothing has ever run it. Under `--strict` the tree produces 711
errors across six of its eight modules; `__init__.py` and `defines.py` already
pass.

The `python-lib` template describes staged adoption for exactly this case:
start non-strict with `ignore_missing_imports`, then flip
`disallow_untyped_defs` and `strict_optional` per module, converging on
`--strict`. Measuring before applying it showed the staged path does not fit
this project.

- Plain `mypy src/` reports no issues at all, once one annotation is added.
  mypy asked for that one by name: `ModbusPduParser._registry`, which it could
  not infer as `dict[int, type[ModbusPdu]]` from an empty literal.
- The library has no third-party dependencies. `ignore_missing_imports` would
  suppress nothing, because nothing is missing.

So the template's first rung is already reached, and adopting it would gate
nothing — including for new modules, which is the half that matters.

The 711 findings are also narrower than the count suggests. There are four
distinct error codes, and two of them dominate.

| Module | Frozen codes |
| --- | --- |
| `errors.py`, `logger.py`, `omb_server.py` | `no-untyped-call`, `no-untyped-def` |
| `omb_client.py` | `assignment`, `no-untyped-call`, `no-untyped-def` |
| `packets.py`, `stream.py` | `no-untyped-call`, `no-untyped-def`, `override` |

`no-untyped-def` and `no-untyped-call` are the annotations the tree does not
carry yet, which is the debt the ruff docstring freeze already records from
the other side. `override` and `assignment` are not that: they are 123 Liskov
violations in the PDU hierarchy and one socket attribute assigned `None`
against an inferred non-optional type. Both are real findings, filed as #51 so
that a line in a configuration file is not their only record.

## Decision

Turn `strict` on globally and freeze the six legacy modules with
`disable_error_code`, each listing exactly the codes it emits today. This is
ADR-003's per-file lint freeze in the shape mypy offers, and it is governed by
the same two rules: a module is never added to make the gate pass, and an
existing entry is never widened.

```text
                    code in the module's frozen entry?
                       |                        |
                      yes                       no
                       |                        |
                gate stays quiet           gate fails
                       |                        |
     +-----------------+                        +-----------------+
     |                                                            |
     a legacy finding, already                     a new finding, or any
     counted, unchanged                            finding in a new module
     (existing module cannot get worse)            (no entry, so it is held
                                                    to the whole of strict)
```

The ratchet was verified rather than assumed: a throwaway module carrying one
unannotated function fails the gate, and the tree is green again once it is
removed.

`mypy` is pinned to a minor range in `pyproject.toml`, for the reason ruff is.
The freeze records one version's error codes, so a release that reports a new
one would fail the gate on untouched, frozen modules.

## Alternatives considered

- **The template's literal staged path** — rejected on measurement. Non-strict
  with `ignore_missing_imports` is already green here, so it would gate
  nothing today and nothing on a new module either. The staged path is written
  for a project whose dependencies ship no usable stubs; this one has no
  dependencies.
- **Fix all 711 first** — rejected, on ADR-003's reasoning. It contradicts the
  rule that untouched code is not rewritten, and a 711-error annotation pass
  inside a gate change is a diff no reviewer can separate from a behavioural
  one.
- **Disable the strict sub-flags for the legacy modules** — rejected. Turning
  off `disallow_untyped_defs` for a module also stops mypy looking inside
  those functions, so it would have hidden the `override` and `assignment`
  findings entirely rather than recording them. Freezing by error code keeps
  them counted and visible.
- **Run mypy only on files a change touches** — rejected. No mypy mechanism
  does this, and a whole-module view is what makes `no-untyped-call` mean
  anything.
- **Leave the gate off until the rewrite** — rejected. It is the arrangement
  that has held so far, and it is why a documented MUST has never run.

## Consequences

- A module added from here is held to the whole of `--strict` from its first
  commit, which is what matters for the rewrite `CLAUDE.md` anticipates.
- The freeze is an explicit backlog, and a small one to read: four codes, six
  modules. Shrinking a list is the migration, and the gate holds each gain.
- `mypy src/ --strict` — the command `CLAUDE.md` documents — passes, because
  the per-module overrides apply on top of it. A contributor running the
  documented command sees what CI sees.
- The two findings that are not missing annotations are tracked in #51, not
  only in `pyproject.toml`. Closing that issue shrinks the freeze by the
  `override` and `assignment` entries.
- The mypy pin has to be bumped deliberately, and a bump may require
  re-freezing newly reported codes.

## Related

- ADR-003 — the lint freeze this copies, whose two governing rules it inherits
- ADR-004 — the format gate, wired in the pull request before this one
- #38 — wire the quality gates, of which Type check is one row
- #51 — the `override` and `assignment` findings this freeze records
