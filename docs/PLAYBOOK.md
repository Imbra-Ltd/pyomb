# Playbook

Operational reference for common tasks. Setup lives in
`docs/ONBOARDING.md`; the conventions these steps enforce live in `CLAUDE.md`.

## 1. Git workflow

### 1.1 Branch

Work on a branch; never commit to `main`. Naming: `feat/<scope>`,
`fix/<scope>`, `docs/<scope>`, `chore/<scope>`.

```bash
git switch -c fix/rtu-checksum
```

### 1.2 Commit

`<type>(<scope>): <summary>` in the imperative, subject under 80 characters.
Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `style`, `test`.

### 1.3 Pull request

One concern per PR. Repeat the closing keyword before every issue number —
`Closes #22, closes #23` closes both, `Closes #22, #23` closes only the first.
Never put a closing keyword next to an issue the change does not resolve; the
match is on the bare substring and fires even when negated.

```bash
gh pr create --fill
gh run list --limit 1        # CI must be green before merge
```

Before opening it, list every closing keyword the body actually contains and
check each against what the change resolves:

```bash
gh pr view <N> --json body --jq .body | grep -inE '(close[sd]?|fix(e[sd])?|resolve[sd]?) +#[0-9]+'
```

Every line it prints closes that issue on merge. A sentence written to
*exclude* an issue prints here too, and closes it just the same — a negated
keyword is still a keyword, and that phrasing has already cost this repository
one wrongly closed issue. Write "part of #N" or the bare number instead.

After merging, confirm what actually closed. A negated keyword closes silently,
so the merge output never reports it:

```bash
gh issue list --state closed --limit 100 --json number,title,closedAt \
  --jq 'sort_by(.closedAt) | reverse | .[:6] | .[] | "\(.number)  \(.closedAt)  \(.title)"'
```

Sort by `closedAt` and do not shorten the `--limit`. A plain
`gh issue list --state closed --limit 10` orders by issue number, so an old
issue closed a minute ago does not appear anywhere in it — which is precisely
the case this check exists to catch, since the issue wrongly closed by a
negated keyword is usually an old one the change merely mentioned.

### 1.4 Force-push

Do not. A deny rule in the maintainer's environment blocks every form
including `--force-with-lease`. When a branch is behind `main`, merge `main`
into it or use `gh pr update-branch <N>`.

### 1.5 Merge a stack

This repository deletes the head branch automatically on merge. Confirm it
before relying on the procedure below, because that one setting decides whether
a stacked pull request survives:

```bash
gh repo view --json deleteBranchOnMerge
```

How the branch is deleted matters more than whether it is. Deletion carried out
as part of the merge retargets a dependent pull request onto the merged one's
own base and leaves it open. Deletion as a separate step does not: the host
closes the dependent pull request, and it cannot be reopened, because reopening
needs its base ref to exist.

Merge bottom-up, and for each pair:

1. Merge the lower pull request. Do not pass a delete-branch flag while
   anything still targets its branch — `gh pr merge <N> --squash`, no more.
2. Let the automatic deletion retarget the upper one.

The flag is the trap, not the setting. `gh pr merge --delete-branch` deletes as
a separate step even though it reads as part of the merge, and so does deleting
the branch by hand afterwards. Either one closes the upper pull request for
good.

To recover from that: recreate the deleted ref from the base branch, reopen the
pull request, retarget it, delete the ref again, then update the branch.

The same shape catches automated dependency pull requests. Merging a change to
the bot's own config invalidates every pull request it has open, closing them
and deleting their branches — merge the pending bumps first when the intent is
to take them and change the policy.

After the lower one merges, the upper one's diff will double-count it: the
merge base is still the old `main`. Merge `main` into the upper branch and push
— never rebase, since the branch is already pushed and force-push is denied.
When the lower one was rebase-merged, the content is identical on both sides,
so the resolution is the branch's own version throughout, and
`git diff --stat HEAD` after resolving MUST be empty. Anything else means the
merge brought in something the branch did not already have, which is worth
reading before committing.

### 1.6 Issue labels (gh)

Every issue carries exactly one type label and one priority label. GitHub has
no mutually-exclusive label group, so nothing refuses an issue that is missing
one or carries two — the rule holds only because something runs the check:

```bash
gh issue list --state open --limit 200 --json number,labels \
  --jq '[.[] | {n: .number,
                t: ([.labels[].name
                     | select(test("^(bug|epic|task|spike|incident)$"))] | length),
                p: ([.labels[].name | select(test("^P[0-3]$"))] | length)}
        | select(.t != 1 or .p != 1)]'
```

Output MUST be `[]`. Each reported entry names the issue and its actual type
and priority counts, so a `t: 0` is an unlabelled issue and a `t: 2` is a
double-labelled one. Run it when triaging and before a release.

There is no priority below `P3` and no holding-lane milestone. Work that is
not scheduled carries an empty milestone field, which this repository uses for
everything — deferral is the absence of a milestone, never a label.

## 2. Domain operations

### 2.1 Add a function code

1. Add the request and response PDU classes to `src/pyomb/packets.py`, following
   the existing pairs — `PDU_FORMAT`, `PDU_ID`, `serialize`, `deserialize`.
   The last two carry a fixed signature: `serialize(self)` and the classmethod
   `deserialize(cls, stream)`, per ADR-009. Reach the packing helper with
   `self.pack(fmt)` rather than accepting a format from the caller — a
   function code's layout is fixed by the specification.
   `tests/test_packet_signature_contract.py` fails on a class that diverges.
2. Register both at the bottom of the module, where every other class is
   registered.
3. Add a builder to `RequestFactory` in `src/pyomb/omb_client.py` and a
   branch to `sendRequest`.
4. Add a responder to `ResponseFactory` in `src/pyomb/omb_server.py` and a
   branch to `on_data`.
5. Add the code to the tables in `tests/test_server_dispatch.py` and
   `tests/test_client_requests.py`; both iterate a table, so one row each.
6. Assert the wire bytes against a vector from the specification in `docs/`,
   never against this library's own output.

### 2.2 Regenerate the TLS chain

```bash
python scripts/gen_test_certs.py
```

Certificates last 365 days. When the mutual-TLS tests start failing on expiry
rather than on behaviour, rerun this.

## 3. Quality

Run all of these before pushing.

### 3.1 Tests (pytest)

```bash
python -m pytest -q
```

### 3.2 Tests from VS Code

`.vscode/settings.json` enables pytest discovery against `tests/`. Open the
Testing panel (the flask icon in the activity bar) and press Run Tests, or use
Ctrl+Shift+P and "Test: Run All Tests".

If the panel shows no tests or reports import errors, the cause is almost
always the interpreter. `pyomb` resolves through the editable install, so VS
Code must be pointed at the `.venv` that `uv sync` created in the repository
root: Ctrl+Shift+P, "Python: Select Interpreter". A selection made before the
toolchain moved to uv points at the old site-packages install and will keep
resolving an increasingly stale `pyomb`. Confirm with "Python: Show Output"
and check the path matches `python -c "import sys; print(sys.executable)"`.

The mutual-TLS tests skip until the chain exists — see 2.2. The integration
tests bind real ports and sleep through timeouts, so a full run takes about 25
seconds and the run appears to stall part way; that is the inactivity sweep, not
a hang. Teardown prints `ValueError: I/O operation on closed file` from the
server's logger, which is noise, not a failure.

### 3.3 Coverage (pytest-cov)

```bash
python -m pytest -q --cov=pyomb --cov-report=term-missing --cov-fail-under=80
```

CI enforces the floor, and it is the 80% `CLAUDE.md` asks for. The measured
figure sits above it; read it from the run rather than from here, since a
number written down in a document goes stale without anyone editing it.

### 3.4 Lint and format (ruff)

```bash
python -m ruff check src tests scripts
python -m ruff format src tests scripts
```

Configuration is in `pyproject.toml`. The `per-file-ignores` table freezes the
violations that existed when ruff replaced flake8: a new file is checked
against the whole rule set, an existing one cannot get worse, and shrinking the
table is the migration. To take a rule family on, delete the entries naming it,
fix what ruff then reports, and commit both together — the gate holds the gain.

Never add a file to that table to make the gate pass. Regenerate it only after
a cleanup, and empty the block before you do: with the entries in place ruff
suppresses exactly the findings the table has to be rebuilt from, so
`ruff check src tests scripts --output-format=json` reports nothing and the
table would come back empty.

ruff is pinned to a minor range in `pyproject.toml`, because a release that
adds rules to an already-selected family, or that changes what the formatter
emits, would fail a gate on untouched code. Bump it deliberately, not on the
next CI run, and expect a bump to need a re-format commit.

CI runs the formatter as `ruff format --check`, which reports and never
rewrites, so a red run names the file rather than editing it. Run the plain
command above before pushing and the check has nothing to say. Formatting is
therefore not reviewable material — the formatter has already settled it, and
a pull request cannot carry the argument. ADR-004 records the adoption.

### 3.5 Type checking (mypy)

```bash
python -m mypy
```

No arguments: the scope, the strict setting and the per-module freeze all live
in `pyproject.toml`, so a local run and the gate cannot resolve to different
checks. `mypy src/ --strict`, the command `CLAUDE.md` documents, reports the
same thing — the overrides apply on top of it.

`strict` is on globally, so a module added from here is held to all of it from
its first commit. The six modules that predate the gate are frozen by error
code in `[[tool.mypy.overrides]]`, each listing exactly what it emits today.
The two rules are the ones the lint freeze carries: never add a module to make
the gate pass, and never widen an entry. ADR-005 records why. Narrowing is the
migration, and it has run once: ADR-009 settled the packet operation signatures
and dropped `override` from `pyomb.packets`, which split that entry away from
`pyomb.stream`. The findings still frozen that are real defects rather than
missing annotations are tracked in #45 and #46.

mypy is pinned to a minor range for the reason ruff is: the freeze records one
version's error codes, and a release reporting a new one would fail the gate
on untouched modules.

### 3.6 Pre-commit hooks (pre-commit)

```bash
pre-commit install
pre-commit run --all-files
```

The first command is a one-off after `uv sync --locked --extra dev`; from then
on the hooks run on staged files at every commit. The second runs them across
the whole tree, which is the audit rather than the commit path.

The hooks are ruff check, ruff format, gitleaks, file hygiene and mypy — every
one of which CI also runs, because a hook is skippable with `--no-verify`. The
ruff and gitleaks revisions are pinned to the releases CI resolves; a hook that
formats differently from the gate is worse than no hook, because the two then
disagree about a file nobody edited.

### 3.7 Secret scanning (gitleaks)

Runs in CI over the whole history, which is why that job checks out every
commit rather than the single one the action fetches by default. This
repository was imported at v0.1.0 and has never carried key material, so the
full range is in scope. Push protection is enabled on the repository and blocks
a secret at the client before it reaches CI.

### 3.8 Static analysis (bandit)

```bash
python -m bandit -c pyproject.toml -r src scripts tests
```

The `-c` is not optional. Bandit reads nothing from `pyproject.toml` unless
pointed at it, so dropping the flag produces a different, noisier run than CI's
— the exclusions and the test-only assert skip both disappear.

The tree is clean at every severity, so there is no freeze table and no
severity floor: any finding fails. Suppress a false positive at the line with
`# nosec <ID>` naming the specific check, and put the reason in a comment above
it. Never add a check to the config-level `skips` — that stops bandit looking
everywhere rather than here, which is the distinction ADR-005 draws and
[ADR-007](decisions/007-bandit-as-the-whole-sast-gate.md) applies to this gate.

GitHub code scanning is not the other half of this gate. It cannot run on a
private repository without Code Security, and ADR-007 records the decline and
what would reopen it.

### 3.9 CI

```bash
gh run list --limit 1
gh run view <id> --log-failed
```

A local run is evidence about one platform. CI runs Linux under Python 3.10 and
3.13; development is typically Windows. Read the run before calling a change
good — three pushes were reported clean against a red pipeline on 2026-08-16.

One check gates a merge to `main`: `gate`. It is a fan-in job that needs every
other job in `ci.yml` and fails unless each reports exactly `success`, so a
skipped or a cancelled job fails it rather than slipping through. The other
workflow, `release.yml`, runs only on a `v*` tag and gates nothing — it never
runs on a pull request, so a green pull request says nothing about it. See 5.

Branch protection binds administrators, so a red pull request cannot be merged
by anyone. A pull request is required at zero approvals — a single-seat
organisation cannot supply an approval, so any higher count would deadlock
every merge.

Naming one context rather than one per job is what keeps the list from going
stale. Under the previous arrangement each job was named individually, and
`security` was simply never added — it ran green and gated nothing for as long
as it existed. A job added now binds the moment it joins the `gate` job's
`needs` list.

Read the live list rather than trusting this paragraph — a required-checks list
drifts from prose the moment the arrangement changes:

```bash
gh api repos/Imbra-Ltd/pyomb/branches/main/protection \
  --jq .required_status_checks.contexts
```

### 3.10 Verifying a fix

A fix ships with a test that fails against the unfixed code. Run it both ways:
stash or revert the source change, confirm the new test fails, restore, confirm
it passes. Say so in the commit message.

### 3.11 Build (build, twine)

```bash
python -m build
python -m twine check dist/*
```

Both need the `dev` extra. `dist/` is gitignored. The wheel must contain
`pyomb/` and its `dist-info` and nothing else — the `src/` layout is what keeps
`tests/` and `scripts/` out of it, so check the listing after changing the
build configuration:

```bash
python -c "import zipfile; print(*zipfile.ZipFile('dist/pyomb-<version>-py3-none-any.whl').namelist(), sep='\n')"
```

CI runs all three on every change, in the `build` job, so a build that breaks
or a wheel that starts carrying `tests/` fails the pull request rather than
the release. The build that produces the artifacts a consumer downloads is a
different one, in `release.yml` on a tag; see 5.

### 3.12 Line endings (.gitattributes, .editorconfig)

```bash
git ls-files --eol | grep -c "i/crlf"
```

Zero is the pass condition. `.gitattributes` normalises every text file to LF
in the index, so whatever `core.autocrlf` does in a working tree never reaches
a commit; `.editorconfig` is the editor-side half, for editors that read it.
Development is Windows and CI is Linux, which is the split the pair exists for.

A non-zero count means a CRLF file was committed before the normalisation
covered it. `git add --renormalize .` rewrites the index, and the diff it
produces is the fix.

## 4. Maintenance

### 4.1 Bump the templates submodule

Pin a released tag, never a branch tip.

```bash
git -C docs/solid-ai-templates fetch --tags
git -C docs/solid-ai-templates checkout <tag>
git add docs/solid-ai-templates && git commit -m "chore(templates): bump to <tag>"
```

Read rules at the pinned revision:
`git -C docs/solid-ai-templates show HEAD:templates/<file>`. Reading from
`origin/main` describes a future state of this repository, not its current one.

### 4.2 Record a decision

Add `docs/decisions/NNN-slug.md` with Status, Date, Context, Decision,
Alternatives considered, Consequences, and an `Upstream:` line naming a
candidate template file or `none`.

### 4.3 Write a journal entry

Append to `docs/dev-journal.md`, oldest-first. Heading
`## YYYY-MM-DD — three to six word theme`, with `(morning)`/`(afternoon)` when
a day has more than one session. A P0/P1 fix or an incident requires a
post-mortem: Symptom, Root cause, Why missed, Fix, Prevention. One without a
prevention action is incomplete.

### 4.4 Run a 360-degree audit

Nine engineering dimensions, not the four stakeholder perspectives: a library
has no Value or Discovery surface, so `360-headless` applies. Review one
dimension at a time with its lens restated, and give each finding the command
or file that demonstrates it. A finding that cannot be demonstrated is dropped
or marked UNVERIFIED, never listed beside a demonstrated one.

Write the report to `docs/audits/YYYY-MM-DD-360.md` with a scores table, the
issues created, a "Current bottleneck" section, and a findings table per
dimension. The overall grade is the lowest dimension. File findings as issues
rather than fixing them in the same pass — an audit is a discovery pass.

Run before a release or a visibility change, and at milestone boundaries.

### 4.5 Action version updates (Dependabot)

Every `uses:` in the workflow is pinned to a commit SHA with the release in a
trailing comment. Dependabot reads that comment, so a bump arrives as a pull
request rewriting the SHA and the comment together.

`.github/dependabot.yml` enrols the Actions ecosystem alone, weekly, on the
default versioning strategy — the one that lifts a pin to the newest release.
That default is the point of the arrangement rather than an oversight: a pin
nothing moves is a pin that goes stale, and pinning is only worth doing if
something keeps it current.

Read the release notes for input changes before merging a major bump; the
gate proves the rest. The pip ecosystem is deliberately not enrolled, because
this project bounds its dependencies rather than pinning them.

### 4.6 Refresh the toolchain lock (uv)

```bash
uv lock --upgrade
uv sync --locked --extra dev
```

`uv.lock` pins every version the gates run against, across the whole
`requires-python` range rather than for one interpreter, so the single file
serves 3.10 CI, 3.13 CI and a Windows machine. ADR-010 carries why.

The first command re-resolves to the newest versions the ranges in
`pyproject.toml` allow and rewrites the lock. The second proves the result
installs. Review the diff before committing: a toolchain bump is a change to
what every gate measures, and the diff is where that is visible.

Two rules follow from `--locked`, which is what CI installs with:

- Editing a dependency in `pyproject.toml` without running `uv lock` fails
  every CI job at the install step, naming the fix. That is the gate working,
  not a broken pipeline.
- Never pass `--frozen` to work around it. `--frozen` skips the check the
  freeze exists to perform, which turns the lock back into decoration.

Dependabot is enrolled on the pip ecosystem and opens the refresh weekly, so
the commands above are the manual path rather than the routine one. Treat a
lock nobody has touched in months as a finding: it pins an ageing toolchain
with no signal that it has aged.

## 5. Release and deploy

v0.1.0 is tagged and released on GitHub. The distribution is not on PyPI.

To cut a release:

1. Check `git branch --no-merged main` and `git fsck --unreachable` for work
   that would be lost
2. Run a 360 audit per 4.4; do not ship with critical findings open
3. Branch `chore/release-vX.Y.Z`, set `__version__` in `src/pyomb/__init__.py`
   — hatchling reads it, so that literal is the only place a version lives
4. Open the pull request, merge it, and wait for CI to pass on `main`
5. Tag with `git tag -a`, never a lightweight tag, or `git describe` reports a
   stale version to consumers
6. Push the tag

Pushing the tag is the last manual step. `.github/workflows/release.yml` fires
on any `v*` tag and does the rest: it refuses a tag that does not name the
version the package reports, builds the wheel and the sdist, creates the
release record if the tag has none, attaches the distribution, then generates
the SBOM and attaches that. ADR-011 carries why the SBOM is generated from an
environment holding only the wheel, and why the distribution is uploaded before
the SBOM exists.

Do not create the release by hand first. The workflow creates it when absent,
so a hand-made one only risks racing it; if you have already made one, the
workflow uploads into it rather than failing.

`v0.1.0` predates the workflow and carries no assets. It is left that way
deliberately — assets built now from a later tree would not be what that tag
was. See ADR-011.

Before the first PyPI publish: claim the name per ADR-002, and publish from CI
only, never from a local machine. No open issue tracks that work.
