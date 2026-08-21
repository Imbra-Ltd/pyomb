# pyomb

A Python library for Modbus TCP and RTU: a codec, a stream transport, and a
scriptable client/server pair for exercising other implementations.

Quality conventions are defined in `docs/solid-ai-templates/` (submodule).

## Mandatory startup

You MUST read every file listed below IN FULL using the Read tool before you
respond. If you respond without reading them, you are violating project rules.

Read them at the pinned revision, never from `origin/main` and never from the
working tree after a bare fetch:
`git -C docs/solid-ai-templates show HEAD:<path>`

- `templates/base/core/quality.md`
- `templates/base/core/git.md`
- `templates/base/core/docs.md`
- `templates/base/core/readme.md`
- `templates/base/core/testing.md`
- `templates/base/core/review.md`
- `templates/base/core/config.md`
- `templates/base/core/examples.md`
- `templates/base/workflow/quality-gates.md`
- `templates/base/workflow/scope.md`
- `templates/base/workflow/ai-workflow.md`
- `templates/base/workflow/issues.md`
- `templates/platform/github.md`
- `templates/stack/python-lib.md`

The list resolves both axes of `templates/manifest.yaml` — the stack chain and
the platform for the code host — plus the two workflow templates the session
protocol needs and no stack declares; see ADR-008.

Precedence when authorities disagree, highest first: an explicit instruction
in the current session, then this file, then `docs/decisions/`, then the
pinned templates. Ask rather than guess when this file and a template
conflict. Where a dated audit report exists, it ranks below all of them: an
audit is an observation from one day, not a standing rule.

This file describes the target, which the code does not yet meet. Every rule
binds new and modified code; do not rewrite untouched code to match it outside
a tracked migration issue. The open issues are the authority on what is
outstanding — read them rather than inferring the gap.

## 1. Project

### 1.1 Identity

- Model: hybrid
- Owner: Imbra Ltd — Branimir Georgiev
- Repo: `github.com/Imbra-Ltd/pyomb` (private)
- Stack: Python 3.10+, `pyproject.toml`, ruff, mypy, pytest
- Distribution: PyPI as `pyomb`, imported as `pyomb`
- Specifications: Modbus Application Protocol v1.1b3, Modbus Messaging
  Implementation Guide v1.0b, MB-TCP-Security v21 — all in `docs/`

### 1.2 Project structure

The directory map lives in the README "Project structure" section; never
duplicate it here. Create that section if it is missing.

- Wire encoding and decoding goes in the codec package; nothing there may
  import a socket
- Anything that reads or writes a socket goes in the transport package
- The client and server simulators depend on the codec and the transport, and
  nothing depends on them
- Tests mirror the source tree one file per module; regression tests for a
  fixed defect get their own module named for the behaviour, not the issue
- Source lives under `src/` — check `pip uninstall -y pyomb && pytest
  --collect-only`, which MUST fail with `ModuleNotFoundError`
- No `sys.path` manipulation in tests — check `grep -rn "sys.path" tests/`,
  which MUST print nothing

### 1.3 Commands

```bash
pip install -e ".[dev]"          # install with dev dependencies
pre-commit install               # run the gates before every commit
pytest                           # run tests
mypy                             # type check; settings in pyproject.toml
bandit -c pyproject.toml -r src scripts tests   # static analysis
ruff check src tests scripts     # lint
ruff format src tests scripts    # format
python -m build                  # build distribution
twine check dist/*               # validate wheel and sdist metadata
cyclonedx-py environment <venv>  # SBOM; the release workflow runs it
python scripts/gen_test_certs.py # mint the throwaway TLS chain
```

## 2. Code conventions

### 2.1 Git

- Work on a branch; never commit directly to `main`
- Branch naming: `feat/<scope>`, `fix/<scope>`, `docs/<scope>`, `chore/<scope>`
- Commits: `<type>(<scope>): <summary>`, imperative mood, subject under 80
  characters
- One concern per PR; review the diff against `main` before merging
- Repeat the closing keyword before every issue number: `Closes #a, closes #b`
- Never write a closing keyword next to an issue number the change does not
  resolve — GitHub matches the bare substring even when negated
- Never force-push, including `--force-with-lease`; a deny rule in this
  environment blocks it, so hand the command to the owner instead
- Read the CI run for a push before describing the change as good — a local
  run is evidence about one platform only. Check: `gh run list --limit 1`
- Never commit `.venv/`, `__pycache__/`, `*.egg-info/`, `dist/`,
  `.mypy_cache/`, or `assets/certificates/`
- Always commit `uv.lock`, and run `uv lock` in the same change as any
  dependency edit — CI installs with `--locked` and fails on a stale lock;
  never reach for `--frozen` to get past it. See ADR-010
- Bump the templates submodule to a released tag, never to a branch tip

### 2.2 Python

- PEP 8 names throughout; no camelCase on any public symbol
- Every public symbol carries a Google-style docstring stating its contract
- Annotate all public functions and class members; no `Any` in the public API
- Raise a specific `ModbusError` subclass; never bare `except:` or
  `except Exception:` outside a top-level loop that logs and continues
- No mutable default arguments
- Export the public API explicitly from `__init__.py` with `__all__`; no star
  imports anywhere. Check: `grep -rn "import \*" src/`, which MUST print
  nothing
- One name for the project across repository, distribution and import package

### 2.3 Protocol rules

These are the ones that have already cost this project a defect each. Violating
any of them produces frames a real device rejects while this library's own
tests pass.

- Every multi-byte field is big-endian except the RTU checksum, which is sent
  low byte first
- The MBAP length field counts the unit identifier plus the PDU, so a frame is
  `header size + length - 1` bytes
- A serializer computes its own checksum; it never trusts a stored field
- A deserializer verifies the checksum and rejects a frame that contradicts it
- Never treat one `recv()` as one frame — read the declared length, then read
  exactly that many bytes, looping until they arrive
- A client matches every response to its request by transaction identifier and
  discards anything else
- A server echoes the request's transaction identifier, protocol identifier and
  unit identifier unchanged
- A write response echoes the request unchanged; that echo is how a client
  confirms the write
- Assert wire format against published specification vectors, never against
  this library's own output

### 2.4 Simulator rules

- No exception from one client may end the server thread; every path that
  drops a connection retires it from the read list and all bookkeeping together
- Track per-connection state by the connection object — `getsockname()` on an
  accepted socket names the server, and a peer address is not unique either
- Treat a socket teardown call as able to fail; a peer that has gone away is
  the ordinary case on that path, not a fault
- Bound every wait on another thread and report why it gave up; an unbounded
  wait turns a startup failure into a hang with the reason on stderr, where no
  caller can reach it
- A resource limit refuses the request that exceeds it and keeps serving;
  stopping on the limit hands any peer the ability to stop the server
- Secure defaults are load-bearing: verified peer certificate, hostname
  checking on, no custom cipher string, finite socket timeout. Never relax one
  as a test convenience — pass an explicit argument instead

## 3. Quality

Testing, coverage, review order, documentation standards and quality gates
follow the referenced templates. Project-specific additions only:

- A fix for a reported defect ships with a test that fails against the unfixed
  code. Run it both ways and say so in the commit message
- Where behaviour depends on the operating system, inject the fault with a
  double rather than waiting for the platform to supply it — CI is Linux and
  development is Windows
- Never assert on interpreter internals; assert on what the object does
- A test that round-trips this library through itself proves nothing about the
  wire. Pair it with a fixed vector from the specification
- Coverage floor is 80%, enforced in CI. Check: `pytest --cov=pyomb
  --cov-fail-under=80`
- Never silence a lint finding by adding a file to, or widening an entry in,
  the `per-file-ignores` freeze in `pyproject.toml` — it records what was
  already broken, not what may be. Fix the finding; see ADR-003
- The same holds for the mypy freeze in `[[tool.mypy.overrides]]`: never add a
  module and never widen its `disable_error_code` list. Freeze a finding, never
  the analysis that produces it — turning off a strict sub-flag stops the
  checker looking and discards findings the module already has; see ADR-005
- Suppress a bandit finding at the line with `# nosec <ID>` naming the one
  check, and put the reason above it. Never add to the config-level `skips`,
  which stops the check firing tree-wide; see ADR-007

## 4. Identity

Not applicable — a protocol library with no user-facing design or brand voice.

## 5. Review process

Follow `templates/base/core/review.md` priority order, applying
`templates/base/core/quality.md` and `templates/stack/python-lib.md` as the
standard. Verify the MUSTs from `docs.md`, `readme.md` and `git.md` after a new
module, a migration, or before a release.

## 6. Session protocol

Follow `templates/base/workflow/scope.md` for the scope guard and the
end-of-session audit.

### 6.1 Start of session

Read every file in the Mandatory startup block. Check the branch, check
`git status` and ship any unshipped previous wrap first, prune stale branches,
and check the latest CI run on `main` completed successfully. Confirm the scope
with the owner and review the open issues related to it before writing code.

### 6.2 During the session

Flag scope growth explicitly rather than absorbing it. Finish and commit the
current work before starting anything new. Revert tooling-produced changes
outside the agreed scope and file them separately.

### 6.3 End of session

Read `templates/base/workflow/scope.md` (End of session audit) and execute each
item sequentially; do not summarize or skip.
