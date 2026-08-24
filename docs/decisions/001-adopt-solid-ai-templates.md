# ADR-001: Adopt solid-ai-templates in the hybrid model

**Status:** Accepted
**Date:** 2026-08-17
**Upstream:** none — the decision is about consuming the templates, not a
convention to contribute back

## Context

The repository has vendored `braboj/solid-ai-templates` as a submodule at
`docs/solid-ai-templates/` since before the 2026-08-13 audit, but nothing
consumed it. The audit recorded this as finding 7: no `CLAUDE.md`, no ADRs, no
ONBOARDING or PLAYBOOK, with `generated/stack-python-lib.md` named as the
ready-made basis.

Four agent-assisted sessions between 2026-08-15 and 2026-08-17 produced eight
defect fixes. Their post-mortems in `docs/dev-journal.md` name recurring causes
that no code change prevents:

- a suite that only round-trips through its own codec
- work verified on one operating system
- claims asserted from memory rather than read from the file that would
  falsify them

Those are conventions, and conventions need somewhere to live that an agent
reads on every turn.

The templates offer three consumption models. Inline copies every rule into the
project file; reference keeps the project file lean and relies on the agent
reading the templates; hybrid inlines the rules whose violation is silent or
expensive and references the rest.

## Decision

Adopt the templates through a `CLAUDE.md` generated from the `stack-python-lib`
chain, in the **hybrid** model.

The submodule pin is the governing revision. Read rules with
`git -C docs/solid-ai-templates show HEAD:<path>`, never from `origin/main` and
never from the working tree after a bare fetch.

Precedence when authorities disagree, highest first: an explicit instruction in
the session, `CLAUDE.md`, `docs/decisions/`, the pinned templates,
`docs/audits/`.

## Alternatives considered

- **Inline** — rejected. The templates' own guidance reserves it for projects
  that do not vendor the repository. This one does, so inlining would duplicate
  rules that already sit on disk, and the copies would drift.
- **Reference** — rejected. It relies on the agent reading every referenced
  file, and the templates state plainly that there is no guarantee of this. The
  rules most worth having are the ones whose violation is silent, which is
  exactly the wrong set to lose to a skipped read.
- **No adoption, conventions in prose** — rejected. It is the status quo that
  produced the recurring causes above.

## Consequences

- `CLAUDE.md` carries a mandatory startup block listing the twelve template
  files in the resolved chain, and the agent must read them before responding.
- Git conventions change: work moves to branches and pull requests. Every
  commit up to and including this one landed directly on `main`.
- The target toolchain becomes ruff and mypy strict against today's flake8 and
  no type checking, with a `src/` layout and `pyproject.toml`-only packaging.
  The gap is tracked in the issue list, not enumerated in `CLAUDE.md`.
- The end-of-session audit in `templates/base/workflow/scope.md` becomes
  binding, which is what produced this ADR and the ONBOARDING and PLAYBOOK
  documents alongside it.
- The submodule is pinned three commits past `v2.44.0`, a mid-flight revision.
  The templates require pinning a released tag, so the next bump moves to a tag
  and is a separate change.

## Related

- `docs/audits/2026-08-13-360.md` — finding 7
- ADR-002 — the project name the rewrite settles on
