# ADR-010: Lock the development toolchain with uv

**Status:** Accepted
**Date:** 2026-08-21
**Upstream:** filed as braboj/solid-ai-templates#1034 against
`templates/stack/python-lib.md`. With the domain skin off, the convention is
that a frozen-output lock file cannot serve a CI version or platform matrix,
and that a lock CI does not install from with a staleness-refusing flag records
a resolution nobody runs.

## Context

#15 asks whether this project needs a dev lock file. The library declares
`dependencies = []` and is standard library only by design, so the runtime side
needs nothing. The toolchain is where the exposure sits, and only part of it is
bounded:

```text
test = ["pytest", "pytest-cov", "ruff>=0.16,<0.17",
        "mypy>=2.3,<2.4", "bandit[toml]>=1.9,<1.10"]
dev  = ["pyomb[test]", "pre-commit", "build", "twine"]
```

Ruff, mypy and bandit carry minor ranges because each backs a freeze recorded
in `pyproject.toml` that a new rule or error code would break on untouched
legacy code; ADR-003 and ADR-005 carry that reasoning. The remaining five --
pytest, pytest-cov, pre-commit, build and twine -- float completely. CI and a
contributor's machine resolve those independently, so a pytest release that
changes collection, a coverage release that changes accounting, or a twine
release that changes metadata validation lands here with no version bump
anywhere in the repository and no way to say afterwards what a green run ran
against.

The template asks for a lock file in one line and names
`requirements-dev.lock`, which implies `pip freeze` output. That is the part
that does not fit. Frozen output has its markers already resolved, so it is
specific to the interpreter and platform that produced it, and this project
spans three: CI runs a 3.10/3.13 matrix on Linux, development is Windows. The
difference is real rather than theoretical -- 3.10 needs `tomli`, which 3.13
does not, and transitive pins diverge across the two.

So the question is not only whether to lock, but what kind of lock can be true
on every leg at once.

```text
                    resolved at lock time        resolved at install time
                    ---------------------        ------------------------
pip freeze          interpreter + platform       nothing
                    (one leg only)               -> wrong on the other legs

pip-compile         interpreter per invocation   nothing
  --python-version  (one file per leg)           -> N files kept in step

uv lock             the requires-python range    the leg's own markers
                    and target platforms         -> one file, every leg
```

## Decision

1. Lock the toolchain with `uv lock`, committing `uv.lock` at the repository
   root. The lock is universal: it is resolved across the whole
   `requires-python` range rather than for one interpreter, so a single file
   serves 3.10 CI, 3.13 CI and a Windows contributor, and each leg selects the
   markers that apply to it at install time.
2. Every CI job installs with `uv sync --locked`. The flag is the decision, not
   a convenience: uv refuses a lock that no longer matches `pyproject.toml`
   rather than quietly re-resolving, so a dependency edit that skipped
   `uv lock` fails the run instead of installing a set the lock does not
   record. This is `quality-gates-pair-check` applied to the lock -- the
   constraint and its check land together.
3. Every gate step runs under `uv run --no-sync`, so the install step above is
   the only place in a run where a dependency may be resolved.
4. Refreshing is `uv lock --upgrade`, recorded in PLAYBOOK 4.6, and the pip
   ecosystem is enrolled in Dependabot with
   `versioning-strategy: increase-if-necessary` so the refresh has a scheduled
   producer rather than depending on someone remembering.
5. pip remains the install path for a consumer. The lock covers the
   development toolchain; it says nothing about how the published package is
   installed, and `dependencies = []` means there is nothing there to say.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| No lock; bound the five floats with ranges | Cheapest, and it does stop a silent major bump, but a range is not a resolution: two runs a week apart still install different sets inside it, so "what did the green run run against" stays unanswerable. It also leaves the template rule declined rather than met. |
| `pip freeze > requirements-dev.lock` | The artifact the template names, and the one thing that cannot work here. Its markers are already resolved, so the file is true on the leg that produced it and misrepresents the other two. |
| `pip-compile` with `--python-version` per leg | Sound, and stays inside pip. Costs two lock files that must be refreshed in step, and neither describes the Windows machine the code is written on, so a contributor still resolves independently. |
| Poetry or PDM | Both produce a universal lock and would answer the question. Each also takes over dependency declaration and the build path, which is a far larger change than the problem justifies on a project whose `pyproject.toml` is already correct. |

## Consequences

- `uv` becomes a prerequisite for contributors and a CI step. It is one static
  binary with no Python of its own, installed in CI by a SHA-pinned action.
- A dependency edit is now two steps rather than one: change `pyproject.toml`,
  then `uv lock`. Forgetting the second fails CI at the install step with a
  message naming the fix, which is the intended cost.
- The five floating packages are now pinned in a file that is reviewed like
  any other, so a toolchain bump appears in a diff and lands deliberately.
- 62 packages are pinned where 5 were unbounded. The lock is large and mostly
  transitive, and it is read by diffing rather than by reading.
- An unrefreshed lock pins an ageing toolchain silently, which is the failure
  mode this trades for. Dependabot enrolment is what answers it, and until its
  first weekly run confirms it reads `uv.lock`, PLAYBOOK 4.6 is the manual
  path.
- The editable install a contributor had from `pip install -e ".[dev]"` is now
  a `.venv` that `uv sync` owns. Anything pointed at the old environment --
  a VS Code interpreter selection, most notably -- has to be repointed once.
