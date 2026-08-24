---
id: "002"
status: Accepted
date: 2026-08-17
category: repository
supersedes: []
superseded_by: []
---

# ADR-002: One project name, `pyomb`

**Upstream:** none — the naming rule is already generic in
`templates/stack/python-lib.md`; only the chosen name is project-specific

## Context

The project answers to four names. The repository is `protocol-modbus`, the
distribution declared in `setup.py` is `pyOMB`, the README titles it `pyOmb`,
and the import package is `modbus`. Issue #10 records the spread and asks for
unification without naming the target.

The import package is the worst of the four. `modbus` is a bare, generic name
on PyPI's flat namespace, and `import modbus` in a consumer's code says nothing
about which of several Modbus libraries is installed. It also collides with the
domain term used throughout the codebase and the specifications in `docs/`,
which makes prose about "the modbus package" ambiguous between the concept and
the module.

`CLAUDE.md` is written to drive a rewrite, and a file meant to drive one cannot
carry a placeholder for the name of the thing being rewritten.

## Decision

`pyomb` — lowercase — for the distribution on PyPI and for the import package.
Source moves to `src/pyomb/`.

The repository keeps the name `protocol-modbus`. GitHub redirects renamed
repositories, so this can change later at no cost, and the repository name is
the one of the four that no code imports.

## Alternatives considered

- **`modbus`** — rejected. Generic, likely contested on PyPI, and ambiguous
  against the domain term.
- **`pyOMB` as written today** — rejected. Mixed case in a distribution name is
  normalised by PyPI anyway, and PEP 8 asks for lowercase import packages, so
  the capitalisation survives only in prose where it invites the `pyOmb` and
  `pyOMB` split the README already shows.
- **`protocol-modbus`, matching the repository** — rejected. A hyphen cannot
  appear in an import package, so it would force a second name for the module
  and reproduce the split this decision removes.
- **Defer until the rewrite starts** — rejected. The name is the root of the
  `src/` layout, the packaging metadata and every import line, so deferring it
  blocks issues #10, #14 and #16 rather than sequencing them.

## Consequences

- Three names collapse to one; the repository name is deliberately left as the
  fourth and is cosmetic.
- `import modbus` becomes `import pyomb`, which is a breaking change for any
  consumer. The distribution has never been published, so there are none.
- Issue #10 gains a concrete target, and issues #14 and #16 can proceed
  against it.
- The name must be claimed on PyPI before the first release; issue #11 covers
  the release.

## Related

- #10 — unify the project name
- ADR-001 — the templates adoption that required a settled name
