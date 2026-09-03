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
- `templates/base/core/cli.md`
- `templates/base/core/examples.md`
- `templates/base/language/python.md`
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

Read the templates in full, and adopt a rule from them only when you can name
the defect it would have caught in this repository. Otherwise decline it in
one line and move on -- no record, no ticket. A rule stating itself as a MUST
is not evidence that it reduces risk here; see ADR-034, which carries the
measurement that produced this. Rules already adopted stay adopted.

This file describes the target, which the code does not yet meet. Every rule
binds new and modified code; do not rewrite untouched code to match it outside
a tracked migration issue. The open issues are the authority on what is
outstanding — read them rather than inferring the gap.

## 1. Project

### 1.1 Identity

- Model: hybrid
- Owner: Imbra Ltd — Branimir Georgiev
- Repo: `github.com/Imbra-Ltd/pyomb` (public)
- Stack: Python 3.10+, `pyproject.toml`, ruff, mypy, pytest
- Distribution: wheel and sdist attached to the GitHub release, distributed
  and imported as `pyomb`; nothing goes to a package index — see ADR-011
- Specifications: Modbus Application Protocol v1.1b3, Modbus Messaging
  Implementation Guide v1.0b, MB-TCP-Security v21, and the Modicon Modbus
  Protocol Reference Guide PI-MBUS-300 Rev J — all in `docs/specs/`

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
uv sync --locked --extra dev     # install the locked toolchain into .venv
uv lock --upgrade                # refresh the lock; review the diff
pre-commit install               # run the gates before every commit
pytest                           # run tests
mypy                             # type check; settings in pyproject.toml
bandit -c pyproject.toml -r src scripts tests examples   # static analysis
ruff check src tests scripts examples     # lint
ruff format src tests scripts examples    # format
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
- Read every workflow run for a push before describing the change as good — a
  local run is evidence about one platform only, and `--limit 1` reports
  whichever workflow finished last while hiding the other. Check:
  `gh run list --commit $(git rev-parse HEAD)`
- Never commit `.venv/`, `__pycache__/`, `*.egg-info/`, `dist/`,
  `.mypy_cache/`, or `assets/certificates/`
- Always commit `uv.lock`, and run `uv lock` in the same change as any
  dependency edit — CI installs with `--locked` and fails on a stale lock;
  never reach for `--frozen` to get past it. See ADR-010
- Read what `git add -A` staged before committing; a submodule pointer left
  at another branch's revision rides along into an unrelated commit
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
  nothing. That `__all__` is a literal, so a name in it can have nothing bound
  behind it; `tests/test_package_exports.py` asserts every one resolves
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
  checking on, no custom cipher string, finite socket timeout, and a declared
  minimum TLS version. Never relax one as a test convenience — pass an
  explicit argument instead. The floor takes no such argument: it is set
  after the caller's options, which are OR-ed and can only add a restriction

### 2.5 Off-limits paths

- `.github/workflows/` is off-limits — the release workflow fires on a tag
  that cannot be taken back, and no suite runs it
- `docs/solid-ai-templates` is off-limits — the pointer is one line and
  changes every rule this project binds
- Propose a change inside either before making it; the proposal carries a
  rollback strategy and the coverage that would catch a regression
- The approval is for that plan, not for the area — the next change needs its
  own proposal
- A diff touching either names it at the top of its summary; the reviewer's
  attention is the control, and it is spent only if the summary spends it
- Run the check in PLAYBOOK 1.3 before opening a pull request; it reads the
  two paths above, so the list has one home. See ADR-023

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
  which stops the check firing tree-wide; see ADR-012
- Suppress a ruff finding the same way, with `# noqa: <RULE>` naming the one
  rule and the reason above it, and only where the rule is wrong at that site.
  A file that was already broken belongs in the freeze and a real defect gets
  fixed; never a bare `# noqa`, which absorbs every rule that later applies to
  the line. See ADR-025
- Every pattern in the sdist `include` list carries a leading slash. An
  unanchored pattern matches at any depth, so it also selects the templates
  submodule's file of that name and republishes it. Enforced by
  `tests/test_sdist_includes_are_anchored.py`
- Markdown carries any character a reader can see; every other tracked file is
  printable ASCII, where `--` substitutes for a dash. A control character is a
  defect in both — it renders as nothing, and one NUL makes git call the file
  binary and blinds the line-ending gate. Enforced by
  `tests/test_source_is_ascii.py`; see ADR-029
- A decision record holds every sentence to 40 words and every paragraph to 80.
  A sentence that runs long is almost always carrying a list — render it as
  one. Enforced by `tests/test_decisions_are_readable.py`; see ADR-017
- A readability edit to a merged decision record that changes no claim is a
  format migration, not a new decision; say so in the commit and show it with a
  word-level diff. An edit that changes a claim needs a new record; see ADR-017
- Markdown wraps at the width `.editorconfig` declares under its Markdown
  section, which is the only place that number is written down. Table rows,
  fenced blocks and lines carrying a URL are exempt because none of them can be
  wrapped. Enforced by `tests/test_markdown_line_width.py`, which reads the
  declaration rather than restating it; see ADR-018
- An issue or pull request body is written for a reader who has not seen the
  code: symptom before mechanism, every borrowed term expanded on first use,
  and a real example rather than a description of one. Nothing gates it,
  because a sentence-length check passes prose nobody can follow; see
  PLAYBOOK 1.7
- A decision record opens with YAML front matter — `id`, `status`, `date`,
  `category`, `supersedes`, `superseded_by` — which is the source of truth for
  status and supersession. Copy `docs/decisions/TEMPLATE.md`; a new category
  takes its own record. Enforced by `tests/test_decision_frontmatter.py`; see
  ADR-019
- Superseding a record updates both sides in the same change: `supersedes` on
  the new one, `status` and `superseded_by` on the old. That metadata edit is
  the one change a merged record accepts beyond readability; see ADR-019
- A decision record numbered 020 or above names no other record in its prose:
  a supersession goes in the front matter and a context-only pointer goes in a
  closing `## Related` section. Records below that number keep the prose
  citations they merged with and are not to be rewritten. Enforced by
  `tests/test_decision_citations.py`, which skips fenced blocks; see ADR-020
- A check asserting that a set of violations is empty asserts, in a test of its
  own, that its enumeration reached a floor the corpus is known to hold. Those
  listings read git's index, so a document written but not staged is invisible
  to every one of them and `git add` is the fix. Enforced by
  `tests/test_document_gates_are_not_blind.py`, which discovers each gate and
  fails one that passes on an empty corpus; see ADR-022
- The same fact defeats the control that would test such a gate, so plant a
  negative control in the artifact the check reads rather than on disk: an
  unstaged edit leaves an index-reading gate green and reads as proof it is
  blind, which is the comfortable conclusion and the wrong one
- Adding a test or tightening an assertion needs no explanation. Deleting,
  loosening or rewriting one changes what correct means, so it states why in
  the pull request and never merges on a green suite alone — the suite cannot
  report that it was weakened. PLAYBOOK 1.3 carries the classifier and the
  assertion-level diff that evidences the claim

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
and check every workflow run on the `main` tip completed successfully. Confirm
the scope with the owner and review the open issues related to it before
writing code.

### 6.2 During the session

Flag scope growth explicitly rather than absorbing it. Finish and commit the
current work before starting anything new. Revert tooling-produced changes
outside the agreed scope and file them separately.

### 6.3 End of session

Read `templates/base/workflow/scope.md` (End of session audit) and execute each
item sequentially; do not summarize or skip.
