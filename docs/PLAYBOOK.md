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

The three checks below run at three different moments, and each reports on the
state at the instant it executes. Run one early and it reports a tree that no
longer exists, in wording indistinguishable from a run against finished work.
The order here is the order to execute them in.

**After committing, before opening.** Check whether the branch touches an
off-limits path. A hit is an escalation trigger rather than a failure: it says
the change needs the proposal `CLAUDE.md` 2.5 describes before it merges, and
that the summary names the path at the top. The check reads the declared list
from `CLAUDE.md` rather than restating it, so adding a path is one edit.

Its subject is committed history, so a branch whose work is staged and
uncommitted reports exactly what a compliant branch reports. That is the
reading to get right: the natural moment to run a pre-pull-request check is
while writing the change, and that run is guaranteed to report nothing.

```bash
py - <<'EOF'
import pathlib, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = "origin/main"

# The declared list has one home. Reading it is what stops this command and
# the section drifting apart, in the direction where nothing would notice.
SECTION = re.compile(r"^### 2\.5 ")
NEXT = re.compile(r"^#{2,3} ")
ENTRY = re.compile(r"^- `([^`]+)` is off-limits")

lines = pathlib.Path("CLAUDE.md").read_text(encoding="utf-8").splitlines()
inside, declared = False, []

for line in lines:
    if SECTION.match(line):
        inside = True
        continue
    if inside and NEXT.match(line):
        break
    found = ENTRY.match(line) if inside else None
    if found:
        declared.append(found.group(1))

print("off-limits paths declared: %d" % len(declared))
if not declared:
    print("none read from CLAUDE.md; the section moved or its wording drifted")

out = subprocess.run(["git", "diff", "--name-only", BASE + "...HEAD"],
                     capture_output=True, text=True, encoding="utf-8").stdout
changed = [path for path in out.splitlines() if path]

print("files changed: %d" % len(changed))
if not changed:
    print("no files compared; the change is not committed, the base is wrong, "
          "or the branch is empty")

for path in changed:
    for prefix in declared:
        if path.startswith(prefix) or ("/" + prefix) in path:
            print("  off-limits: %s (matches %s)" % (path, prefix))
EOF
```

Pass condition: the command reports how many paths it read and how many files
it compared, then prints nothing. Zero on either count is a failure rather
than a clean branch. Three causes produce it, and the first is the one reached
by running the check at the wrong moment:

- the change is not committed yet, so there is nothing in the subject
- the declaration cannot be parsed, because 2.5 moved or its wording drifted
- the base is wrong, or the branch holds no commits of its own

It belongs here rather than in section 3. Everything in that section is a tool
or a test wired into CI, and this one must never gate: a hit is the normal
outcome of a legitimate workflow edit, so a gate would be muted within a week.

Still after committing, classify what the change did to the suite. Adding a
test or tightening an assertion can only narrow what passes, and needs no
explanation. Deleting, loosening or rewriting one changes what correct means,
and a green run cannot report that it has:

```bash
git diff --name-status origin/main...HEAD -- 'tests/*' | wc -l
git diff --name-status origin/main...HEAD -- 'tests/*' | grep -vE '^A'
```

Pass condition: the first line counts the test-file changes inspected; the
second lists every one that is not a pure addition. Every path the second
prints is a claim the pull request body owes — what was weakened and why. A
zero from the first is a real answer here, unlike the check above it: it means
the change touched no tests at all. The same uncommitted-work caveat applies,
because the subject is the same committed range.

The listing names files, not assertions, so a formatting pass over a test
module prints as loudly as a deleted case. Narrow it before writing the
explanation:

```bash
git diff -U0 origin/main...HEAD -- 'tests/*' | grep -E '^[-+].*(assert|self\.fail)'
```

Pass condition: every line it prints is accounted for in the body. This is the
evidence the first check asks for rather than a second gate — a mechanical
rewrite shows the same assertion on both sides, and a weakened one does not.

**After opening, before merging.** Create the pull request, then list every
closing keyword its body actually contains and check each against what the
change resolves:

```bash
gh pr create --fill
gh pr view <N> --json body --jq .body | grep -inE '(close[sd]?|fix(e[sd])?|resolve[sd]?) +#[0-9]+'
gh run list --commit $(git rev-parse HEAD)   # every row must be green
```

The order is forced: `gh pr view <N>` needs the pull request to exist, so this
check cannot run before `gh pr create` however the prose reads.

Every line the grep prints closes that issue on merge. A sentence written to
*exclude* an issue prints here too, and closes it just the same — a negated
keyword is still a keyword, and that phrasing has already cost this repository
one wrongly closed issue. Write "part of #N" or the bare number instead.

An empty result means the body carries no closing keyword at all, which is
correct for a change that resolves nothing and a defect for one that does.

**After merging**, confirm what actually closed. A negated keyword closes
silently, so the merge output never reports it:

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

A squash merge reaches the same answer by a longer route, and it is the
route this repository takes. The lower branch's commits are replaced on
`main` by one equivalent commit that the upper branch is not descended
from, so the merge base stays the pre-stack `main`, and any file both
sides rewrote conflicts whole — including a file neither change is about.

The resolution is still the branch's own version, but assert that rather
than reasoning to it. Before resolving, compare the two conflict stages,
where stage 2 is the branch and stage 3 is `main`:

```bash
git show :2:<path> > /tmp/ours && git show :3:<path> > /tmp/theirs
diff /tmp/theirs /tmp/ours
```

Added lines only means the branch side is a superset, so taking it
discards nothing. A removed or changed line is the case to stop and read
before committing.

### 1.6 Issue labels (gh)

Every issue carries exactly one type label and one priority label. GitHub has
no mutually-exclusive label group, so nothing refuses an issue that is missing
one or carries two — the rule holds only because something runs the check:

```bash
py - <<'EOF'
import json, re, subprocess

# Ask for more than the repository is expected to hold, so a listing that
# comes back at the limit is a truncation rather than a coincidence.
LIMIT = 500
TYPES = re.compile(r"^(bug|epic|task|spike|incident)$")
PRIORITIES = re.compile(r"^P[0-3]$")

# Decode as UTF-8 rather than the locale encoding. `gh` emits UTF-8; on
# a console whose code page is not, text=True alone mangles every
# non-ASCII label name, and on a code page that does not map every byte
# it raises UnicodeDecodeError instead.
raw = subprocess.run(["gh", "issue", "list", "--state", "open",
                      "--limit", str(LIMIT), "--json", "number,labels"],
                     capture_output=True, text=True,
                     encoding="utf-8").stdout
issues = json.loads(raw) if raw.strip() else []

print("issues inspected: %d" % len(issues))
if not issues:
    print("no issues found; the query or the repository context is wrong")
if len(issues) == LIMIT:
    print("listing came back at the limit of %d; the set is truncated" % LIMIT)

for issue in issues:
    names = [label["name"] for label in issue["labels"]]
    types = [n for n in names if TYPES.match(n)]
    priorities = [n for n in names if PRIORITIES.match(n)]
    if len(types) != 1 or len(priorities) != 1:
        print("issue %d: %d type label(s), %d priority label(s)"
              % (issue["number"], len(types), len(priorities)))
EOF
```

Pass condition: the command reports how many issues it inspected and prints
nothing after that. Each reported entry names the issue and its actual type
and priority counts, so `0 type label(s)` is an unlabelled issue and
`2 type label(s)` a double-labelled one. Run it when triaging and before a
release.

A count of zero is a failure rather than an empty tracker. Three things
produce an empty listing and only one of them is compliance: every issue
correctly labelled, an authentication failure, or the command running against
the wrong repository. A count equal to the limit is a failure too, because the
listing was truncated and the check then reported on part of the set while
looking identical to a full pass.

This is the form `templates/platform/github.md` ships, adopted rather than
locally extended. The `jq` form it replaces was correct for what it printed
and reported nothing about its own coverage, and keeping a variant means every
upstream fix to the check has to be re-derived here instead of arriving with
the pin. It also drops a line continuation, which is the one break mode that
fails neither loudly nor closed.

There is no priority below `P3` and no holding-lane milestone. Work that is
unscheduled but still live carries an empty milestone field — never a label
and never a lane.

Work deferred on a trigger outside this repository is closed rather than
carried open, per ADR-016. The closing comment carries the trigger, what would
detect it, the instruction to reopen rather than refile, and anything that
loses its watcher by the closure. No triage label is applied: `wontdo` states
the opposite of what is true for work that is expected back.

Naming the detector is what stops the backlog re-running the check by hand.
Where nothing detects the trigger, the comment says so — an unwatched trigger
is a decision to take deliberately, and a comment that omits the question
reads the same as one that answered it.

### 1.7 Writing an issue or pull request body

An issue is read by someone deciding whether to pick the work up, and a pull
request by someone deciding whether to approve it. Neither has the code in
their head, and an issue can sit for months before anyone opens it. Write for
that reader rather than for the person who has just finished the
investigation.

Five habits carry most of it.

**State the symptom before the mechanism.** What a user would see comes
first, why it happens comes second. A body that opens with the internals asks
the reader to hold them before knowing what they explain.

**Expand a term the first time it appears, or avoid it.** Names taken from
the code — `__dict__`, `*args`, "PDU" — are exact and mean nothing to a
reader who has not opened the file. Say what the thing is, then name it.

**Show the example rather than describing it.** Real values a reader can
compare beat a sentence about what would happen, and the interesting bytes
are worth pointing at.

**One idea per sentence.** A sentence carrying three clauses is usually three
sentences. A reader who has to go back and re-read has found a defect in the
sentence, not in themselves.

**Separate how bad it is now from how bad it becomes.** A latent defect and a
live one need different words, and a body that blurs them either alarms the
reader or undersells the work.

Three tells that a paragraph needs rewriting: a double negative, an abstract
noun standing where a value would do ("the divergence", "the ordinal"), and a
sentence that parses only for someone who already knows the answer.

A worked example, from the body of #228. Before:

```text
Two packets that serialize to identical bytes are NOT reachable as unequal
without an assignment -- the generic and concrete PDUs use different formats
and so produce different bytes for the same values.
```

After:

```text
You have to change a value after creating the packet to run into this.
Nothing in the library does that yet, so no current behaviour is wrong.
```

The same fact, readable once.

Nothing gates this. It is judgement, and a check counting sentence length
would pass prose nobody can follow while failing a long sentence that reads
cleanly — so it is a review item, and reading the body back as though the
investigation had not happened is the whole test.

The required structure does not change. `templates/base/workflow/issues.md`
sets which sections each issue type carries; this section governs the prose
inside them.

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
python -m ruff check src tests scripts examples
python -m ruff format src tests scripts examples
```

Configuration is in `pyproject.toml`. The `per-file-ignores` table freezes the
violations that existed when ruff replaced flake8: a new file is checked
against the whole rule set, an existing one cannot get worse, and shrinking the
table is the migration. To take a rule family on, delete the entries naming it,
fix what ruff then reports, and commit both together — the gate holds the gain.

Never add a file to that table to make the gate pass. Regenerate it only after
a cleanup, and empty the block before you do: with the entries in place ruff
suppresses exactly the findings the table has to be rebuilt from, so
`ruff check src tests scripts examples --output-format=json` reports nothing
and the table would come back empty.

ruff is pinned to a minor range in `pyproject.toml`, because a release that
adds rules to an already-selected family, or that changes what the formatter
emits, would fail a gate on untouched code. Bump it deliberately, not on the
next CI run, and expect a bump to need a re-format commit.

CI runs the formatter as `ruff format --check`, which reports and never
rewrites, so a red run names the file rather than editing it. Run the plain
command above before pushing and the check has nothing to say. Formatting is
therefore not reviewable material — the formatter has already settled it, and
a pull request cannot carry the argument. ADR-004 records the adoption.

A finding has three homes and only one of them is the freeze table. A rule
that is wrong at one site is suppressed there; a file that was already broken
on adoption day is in the table; anything else is fixed. ADR-025 draws the
line and ADR-003 owns the table.

```bash
grep -rn '# noqa' src tests scripts examples
```

Pass condition: every line it prints names a rule, as `# noqa: B017`, with the
reason in a comment directly above. A bare `# noqa` is the failure — it
absorbs every rule that later applies to that line, where a named one keeps
failing on the next finding. An empty result is a pass here and not a broken
path: the repository carried none at all until `v0.3.0`.

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

The job downloads the gitleaks binary from a release asset before it can scan
anything, and that download retries. A connection reset there once failed the
job with `curl: (35) Recv failure` and took the required gate with it, having
scanned nothing. `tests/test_workflow_downloads_retry.py` pins the retry and
the fail-fast flags on every download a workflow makes, so the next one added
cannot omit them. A red run here still wants the log read before it is called
transient: a download that failed and a scan that found a secret look the same
in the checks list and mean opposite things.

### 3.8 Static analysis (bandit)

```bash
python -m bandit -c pyproject.toml -r src scripts tests examples
```

The `-c` is not optional. Bandit reads nothing from `pyproject.toml` unless
pointed at it, so dropping the flag produces a different, noisier run than CI's
— the exclusions and the test-only assert skip both disappear.

The tree is clean at every severity, so there is no freeze table and no
severity floor: any finding fails. Suppress a false positive at the line with
`# nosec <ID>` naming the specific check, and put the reason in a comment above
it. Never add a check to the config-level `skips` — that stops bandit looking
everywhere rather than here, which is the distinction ADR-005 draws and
[ADR-012](decisions/012-adopt-codeql-as-the-platform-sast.md) applies to this
gate. ADR-007 wrote these rules and ADR-012 supersedes it, carrying them
forward unchanged, so the live record is the later one.

CodeQL is the other half of this gate, in `.github/workflows/codeql.yml` and
recorded in [ADR-012](decisions/012-adopt-codeql-as-the-platform-sast.md). The
two are not redundant: bandit fails the build on any finding, so it blocks a
merge, where CodeQL writes alerts that nothing announces. Read them rather than
waiting to be told:

```bash
gh api repos/Imbra-Ltd/pyomb/code-scanning/alerts --jq length
gh api "repos/Imbra-Ltd/pyomb/code-scanning/analyses?ref=refs/heads/main" \
  --jq '.[0] | {category, results_count, ref}'
```

The `ref` is not decoration. A pull-request analysis reports what the change
introduces, so it reads zero on a tree that carries findings — which is how
ADR-012 came to record a baseline it had not measured, and why
[ADR-013](decisions/013-correct-the-codeql-baseline.md) supersedes it. Measure
the tree on `refs/heads/main`.

A green CodeQL run means the analysis ran, not that it found nothing. ADR-007
declined this half while the repository was private and named the trigger that
reopened it.

### 3.9 CI

```bash
gh run list --commit $(git rev-parse HEAD)
gh run view <id> --log-failed
```

Both halves of that selector are load-bearing. `--limit 1` reports whichever
workflow finished last and hides the other, and an abbreviated hash makes
`--commit` match nothing, print an empty list and exit zero — a malformed
query that reads exactly like a commit whose runs have not started.

Run it after pushing. An unpushed commit has no runs, so it produces the same
empty list from a third cause, and none of the three is distinguishable from
the others in the output.

A local run is evidence about one platform. CI runs Linux under Python 3.10 and
3.13; development is typically Windows. Read the run before calling a change
good — three pushes were reported clean against a red pipeline on 2026-08-16.

Two checks gate a merge to `main`, one per workflow: `gate` and `codeql`. Each
is a fan-in job that needs every other job in its own workflow and fails unless
each reports exactly `success`, so a skipped or a cancelled job fails it rather
than slipping through. A fan-in can only need jobs beside it, which is why
there are two rather than one: `codeql.yml` is separate so the
`security-events: write` scope it needs stays off the CI jobs.

`codeql` is narrower than its name suggests. It proves the analysis ran, not
that the code is clean — CodeQL uploads findings as alerts and still
succeeds. Blocking a merge on an alert is a separate platform control and is
not turned on; ADR-013 draws the distinction, and 3.8 says how to read the
alerts.

The third workflow, `release.yml`, runs only on a `v*` tag and gates nothing —
it never runs on a pull request, so a green pull request says nothing about it.
See 5.

Branch protection binds administrators, so a red pull request cannot be merged
by anyone. A pull request is required at zero approvals — a single-seat
organisation cannot supply an approval, so any higher count would deadlock
every merge.

Naming one context per workflow rather than one per job is what keeps the list
from going stale. Under the previous arrangement each job was named
individually, and `security` was simply never added — it ran green and gated
nothing for as long as it existed. A job added now binds the moment it joins
its workflow's fan-in `needs` list, and only a new workflow needs the required
list touched at all.

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

Both ways proves nothing where the fix has no observable effect on this tree. A
preventive change -- a guard for a condition nothing currently triggers, a rule
tightened where no file violates it -- prints the same output on either side of
itself, so the run is evidence for neither. Such a fix ships a check against a
synthetic subject reproducing the condition. Without one it is
indistinguishable from a no-op, including to whoever later reads it as
unnecessary and deletes it.

Where the tree can be put into the failing state instead, demonstrate the
defect on the branch that fixes it: run the check with the fix's own edit still
uncommitted, then again once it is committed. Those two numbers are the defect
and its repair over real inputs, and they cost one extra invocation.

### 3.11 Build (build, twine)

```bash
python -m build
python -m twine check dist/*
```

Both need the `dev` extra. `dist/` is gitignored, and it is not emptied
between runs — so `twine check` and the listing below read whatever is there,
which is the previous build until `python -m build` has run against the
current tree. Clear it first when the answer matters.

The wheel must contain `pyomb/` and its `dist-info` and nothing else — the
`src/` layout is what keeps `tests/` and `scripts/` out of it, so check the
listing after changing the build configuration:

```bash
python -c "import zipfile; print(*zipfile.ZipFile('dist/pyomb-<version>-py3-none-any.whl').namelist(), sep='\n')"
```

CI runs all three on every change, in the `build` job, so a build that breaks
or a wheel that starts carrying `tests/` fails the pull request rather than
the release. The build that produces the artifacts a consumer downloads is a
different one, in `release.yml` on a tag; see 5.

### 3.12 Line endings (pytest)

```bash
pytest tests/test_line_endings.py
```

Every text file is stored LF in the index. `.gitattributes` normalises on the
way in, so whatever `core.autocrlf` does in a working tree never reaches a
commit; `.editorconfig` is the editor-side half, for editors that read it.
Development is Windows and CI is Linux, which is the split the pair exists for.

A failure names each offending path. A file the index stores with a carriage
return got in before the normalisation covered it: `git add --renormalize .`
rewrites the index, and the diff it produces is the fix. Both `crlf` and
`mixed` count, so a file carrying one CRLF line among LF ones fails too — a
plain count of `crlf` does not report that one.

The second rule reaches what counting carriage returns cannot. A file git
classifies as binary reports `-text` in place of a line-ending value, and
`text=auto` skips normalising it, so its carriage returns enter the index
unconverted while a count stays at zero. One NUL byte anywhere is enough to
trigger that classification, which is how this journal came to be stored with
1127 CRLF endings while the check reported a clean tree. The specifications
are declared binary in `.gitattributes` and the test reads that declaration
rather than naming them, so a new binary file is one line there. Anything else
reporting `-text` is a text file with a byte in it that does not belong, and
`tests/test_source_is_ascii.py` names the character and its line.

`git ls-files --eol` is the raw view the test reads, one record per tracked
path.

### 3.13 Character set (pytest)

```bash
pytest tests/test_source_is_ascii.py
```

The sibling of the rule above: line endings govern how a file ends its lines,
this governs which characters may appear in them. Markdown carries any
character a reader can see; every other tracked file is printable ASCII without
exception. ADR-029 records where the boundary sits and what moving it gave up.

A failure names each offending character as `path:line:column U+XXXX`. Outside
Markdown the substitute for an em dash is `--`, and a homoglyph — a Cyrillic
letter that renders identically to its Latin twin — is replaced by the Latin
letter it imitates. Inside Markdown the only failure is a control character,
which renders as nothing and is almost always a byte written where the text of
its escape was meant. A NUL is the one that reaches past its own line: git then
classifies the file as binary, skips line-ending normalisation, and the gate
above reads a clean tree over a file full of CRLF.

### 3.14 Decision-record readability (pytest)

```bash
pytest tests/test_decisions_are_readable.py
```

Every sentence in `docs/decisions/` is held to 40 words and every prose
paragraph to 80. Fenced blocks, tables, headings and block quotes are read
past; a quotation of a pinned template is the rule a record is measured
against, not this project's prose. ADR-017 records where the limits came from.

A failure names each offender as `path:line`, its length, and its opening
words. The fix is almost always the same: a sentence over the limit is carrying
a list, so render it as a list and the words survive intact. A paragraph over
the limit usually holds two subjects, so give the second its own paragraph.

### 3.15 Markdown line width (pytest)

```bash
pytest tests/test_markdown_line_width.py
```

Every tracked Markdown line is held to the width `.editorconfig` declares under
its Markdown section, counted in characters so an em dash costs one and not
three. That declaration is the only place the number is written down, and the
check reads it rather than carrying a copy. Table rows, fenced blocks and lines
carrying a URL are exempt, each because it cannot be wrapped; a relative link
is not. `docs/specs/Open_Modbus_Tutorial.md` is outside the rule, having
arrived with the v0.1.0 import at its own width. ADR-018 records the scope and
the exemptions, and names the path it sat at before ADR-028 grouped the
specifications.

A failure names each offender as `path:line (width)`. Wrap at or before the
declared column. A heading that will not fit wants a shorter title, not a
longer line. Removing the declaration fails the check outright rather than
falling back to a default, because a width nothing states is the defect itself.

### 3.16 Decision-record schema (pytest)

```bash
pytest tests/test_decision_frontmatter.py
```

Every record opens with the YAML front matter the upstream governance record
defines. The check reads it back: `id` matches the filename, `status` and
`category` come from closed sets, `date` is `YYYY-MM-DD`, both link fields are
present, and a supersession names the same pair from both sides. ADR-019
records the schema and this project's category set.

A new category is a decision that takes its own record. Widening the set in
`CATEGORIES` to make a record pass inverts that, which is the same move the
lint and type freezes forbid.

### 3.17 Sdist include anchors (pytest)

```bash
pytest tests/test_sdist_includes_are_anchored.py
```

Every pattern in the sdist `include` list carries a leading slash. Hatchling
reads a pattern the way git reads a `.gitignore` line, so one without a
separator matches at any depth: an unanchored `tests`, `README.md` or `LICENSE`
selects the templates submodule's file of that name as well as this project's.
A build from a working checkout carries 57 such files out of 125 — the
submodule's licence, its readme and the whole of its test suite.

The released archives are clean, because `release.yml` checks out without
submodules and the patterns find nothing to select. That is the checkout
configuration covering for the include list, not a safeguard: populating the
submodule in that job would ship the leak on the next tag.

The check reads `pyproject.toml` rather than building one, because an
unanchored pattern is the whole of the defect and a build costs tens of
seconds. It skips on Python 3.10, which has no standard-library TOML parser,
and the 3.13 leg of the matrix carries it.

What it cannot see is a pattern that is anchored and still wrong. After
changing the include list, confirm against a real archive:

```bash
python -m build --sdist
tar -tzf dist/pyomb-*.tar.gz | grep -c solid-ai-templates
```

The count must be `0`.

### 3.18 Public API exports (pytest)

```bash
pytest tests/test_package_exports.py
```

Every name in `__all__` resolves against the package. The list is a literal
rather than a reference, so a name can sit in it with nothing bound behind it;
`from pyomb import ThatName` then fails for a name the package advertises, and
no other gate reports it. CLAUDE.md 2.2 states the export rule and this is what
holds it.

The module also pins the deferral the simulators rest on. `OmbClientSim` and
`OmbServerSim` are bound through the package's `__getattr__` rather than
imported at the top, because importing them costs every caller the ssl import
for a transport most callers never open — roughly 13ms against the package's
own 35ms. A plain `import pyomb` must therefore load neither simulator nor ssl.

That half runs a fresh interpreter and reads `sys.modules` in it. In-process
the suite has already imported both submodules for other reasons, so asking
there would always answer yes.

Re-measure before treating the numbers above as current:

```bash
python -X importtime -c "import pyomb; import pyomb.omb_client; import pyomb.omb_server"
```

Read the cumulative column on the `pyomb` line and on the two that follow it.

### 3.19 Entry-point output encoding (pytest)

```bash
pytest tests/test_entry_points_set_the_encoding.py
```

A program that writes text states its encoding rather than inheriting the
console's, and does so inside its `__main__` guard. The check reads both
directions: every module with a guard that prints or builds a `Logger` calls
`sys.stdout.reconfigure`, and nothing under `src/pyomb/` calls it anywhere but
inside a guard.

The second half is the one that matters. `sys.stdout` belongs to the process,
so a library module reconfiguring it at import reaches into an application that
only wanted to send a Modbus frame. `src/pyomb/logger.py` is the case that
looks like an exception: it builds a handler on `sys.stdout` and sets no
encoding on it, for the reason its own docstring gives for not touching the
root logger.

A new script that prints fails this until it carries the call. A script that
prints nothing is not asked for one.

### 3.20 Examples (CI job)

```bash
python -m venv /tmp/consumer
/tmp/consumer/bin/python -m pip install .
for f in examples/*.py; do /tmp/consumer/bin/python "$f" || break; done
```

The `examples` job in `ci.yml` runs every file in `examples/` against an
install of the project with no extras, on Python 3.10. Reproduce it in a throw
away virtual environment rather than the development one: the point of the job
is that an example needs nothing a consumer would not have, and running it
inside `.venv` proves the opposite of what is wanted, since every gate tool is
already there.

The job globs the directory rather than listing files, so a new example is
covered by existing. It also counts what it ran and fails on zero — an empty
directory, a renamed suffix or a mistyped path would otherwise look exactly
like every example passing.

The two socket examples start the server simulator on port 0 rather than 502.
A port below 1024 needs privileges on Linux, so an example fixed at the
registered Modbus port could not run here at all. `examples/README.md` states
that beside the commands, and the project README keeps 502 because that is what
a real device listens on.

An example is documentation that runs, so a failure here is usually the
documentation going stale rather than a defect in the library. Read what the
example claims before changing what it does.

### 3.21 Decision-record citations (pytest)

```bash
pytest tests/test_decision_citations.py
```

A record numbered 020 or above names no other record in its prose. A
supersession goes in the front matter, where a check can validate it, and a
context-only pointer goes in a closing `## Related` section. A prose reference
rots silently: the record it names gets superseded and the sentence pointing at
it reads exactly as it did before.

Records below 020 merged before the rule existed and keep their citations.
Fourteen of the nineteen carry one, and eight of those carry it inside a
Decision section, where moving it would change what was decided rather than
reformat it. ADR-020 records the boundary and why rewriting them was refused.

The check skips fenced blocks, so a record may quote the rule or the command
that measures compliance without failing itself. It also skips everything from
the `## Related` heading onward. What that section may not carry is
decision-bearing text, which no check can judge — moving or superseding
anything it names must not change what the Decision section means, and only
review can tell.

A failure names the record, the line and the reference. Raising the boundary to
silence one is the one edit that constant must never take: it would exempt a
record written under the rule.

### 3.22 Gate coverage (pytest)

```bash
pytest tests/test_document_gates_are_not_blind.py
```

Every check in this section that reads a tracked-file listing — the line
endings, the character set, the Markdown width, the three over the decision
records and the one over the release audits below — first asserts that the
listing reached a floor its corpus is known to hold. A test asserting no
violations were found passes identically when nothing was examined, so without
that a broken enumeration reports a clean tree in the same words as a clean
one.

This is the control that keeps them honest. It discovers each gate by how it
reads its corpus, replaces that read with an empty result, and fails any gate
that still passes. A gate added later is covered without being registered
anywhere, and the same discovery is what fails a new gate written without a
coverage test.

Two reds are worth telling apart. A coverage test failing names the
enumeration, and the usual cause is a document written but not staged: the
listing reads git's index rather than the working tree, so `git add` is the
fix. A rule failing names the document and the line.

ADR-022 records the floors, where each number came from, and why the unstaged
gap is stated rather than closed.

### 3.23 Release audit currency (pytest)

```bash
pytest tests/test_release_audit_is_current.py
```

The gate applies to a minor or major release. A patch release owes no audit,
and the gate is silent for one.

The newest report in `docs/audits/` must not be older than the release before
the one the package reports. An audit run before that release shipped says
nothing about the changes since, so it is refused. An audit dated the same day
is accepted.

Every release owed an audit until v0.4.4. That produced two consecutive
declines — v0.4.2 wrote a skip record and v0.4.3 reused it — leaving three
releases resting on the 2026-08-29 report. A patch changes no interface, so
the review has nothing new to review, and an obligation discharged by writing
a document is not an obligation. ADR-033 carries the narrowing and what it
gives up.

A version the gate cannot read is a finding rather than a pass. Not knowing
whether an audit is owed is not the same as none being owed, so a typo in the
version literal fails here instead of buying a silent exemption.

Same-day was refused until v0.4.3. Dates carry no time, so an audit written
before a release and one written after it read alike, and refusing both was
the safe reading — until it turned out to block two releases on one calendar
day outright, with no record datable late enough to clear the gate. ADR-032
carries that reversal and what it gives up.

The gate reads the changelog's dated entries rather than `git tag`. CI checks
out shallow and fetches no tags, so a tag-based rule would find nothing and
report a clean tree from it. ADR-027 carries that choice and what was rejected.

Nothing detects a release branch. The comparison tightens only when a new dated
entry appears, which is 5 step 4, so the gate is silent between releases and
fails on the branch cutting a minor or a major one.

While the package reports a patch version the live assertion passes without
comparing anything, which no green run distinguishes from a real pass. The
fixture tests are what keep the rule honest in that state, so they name a minor
version and pin the patch case explicitly.

Two ways to clear it. Run the audit per 4.4, or write
`docs/audits/YYYY-MM-DD-360-skipped.md` naming the release and the reason.
Declining the step is a judgement call an operator is allowed to make; what the
gate refuses is passing over it in silence, which is what four releases did.

## 4. Maintenance

### 4.1 Bump the templates submodule

Pin a released tag, never a branch tip, and resolve which tag from the
listing rather than from the issue that asked for the bump. A tag named in an
issue body is a claim with a short life: it has been wrong on arrival twice,
once where the body said `v2.55.0` and `v2.56.0` already existed, once where
it said `v2.58.0` and `v2.59.0` did. Both bodies were sound against the range
they were written for, and neither could have known.

```bash
git -C docs/solid-ai-templates fetch --tags
git -C docs/solid-ai-templates tag --sort=-v:refname | head -3
git -C docs/solid-ai-templates checkout <tag>
git add docs/solid-ai-templates && git commit -m "chore(templates): bump to <tag>"
```

Read rules at the pinned revision:
`git -C docs/solid-ai-templates show HEAD:templates/<file>`. Reading from
`origin/main` describes a future state of this repository, not its current one.

A bump can change the resolved chain, so reconcile the `CLAUDE.md` startup
block against the new pin in the same commit. Upstream adds and removes
template files, and the block is a hand-maintained copy of what
`templates/manifest.yaml` resolves to; a bump that adds one leaves the block
short, and a bump backwards leaves it naming a file the pin does not carry.

Both directions are checked by the suite, so reconciling needs no separate
step and cannot be forgotten:

```bash
pytest tests/test_startup_block_resolves.py
```

It resolves the manifest's core set and dependency edges over the two axes this
repository sits on, `stack-python-lib` and `platform-github`, adds the two
session-protocol templates no stack declares, and fails naming each file that
differs and which side it sits on. A file the chain resolves and the block
omits is governed scope silently lost; a file the block names and the chain
does not resolve is scope never adopted. A failure is the block to correct
rather than the test, unless this repository has changed stack or code host.
ADR-008 carries why the two additions are there, ADR-015 why the check exists.

The guard checks chain membership, not rule content. A bump can leave the block
correct while a rule this project deliberately diverges from moves underneath
it, and nothing reports that. Re-read every record carrying a divergence
against the text the new pin ships -- ADR-029 on the character set, ADR-017 on
the format-migration boundary, ADR-019 on the prose rule it declines, ADR-020
on the citation scope. The divergence may still hold, or upstream may have
adopted it, in which case the record now describes an inherited rule rather
than a departure from one.

Three of the four are in that second state as of `v2.60.0`, and the reading
that established it is not owed again. Upstream took the format-migration
boundary at `v2.47.0` and the citation scope at `v2.54.0`, each from this
project's own filing, so ADR-017 and ADR-020 now describe inherited rules.
ADR-019's decline of the citation rule was narrowed by ADR-020 before either
landed, and none of it is live. The character-set record is the one still
standing apart, and it stands the other way: `quality.md` narrowed its ASCII
rule to identifiers at `v2.46.0`, so this project's rule is the stricter of the
two rather than a departure from it. ADR-029 replaced ADR-014 on 2026-08-29 and
closed half the gap by lifting the printable restriction off Markdown, leaving
the source half stricter than the templates and the divergence live. A pin that
re-widens that rule puts it back in the first state, which is why it stays on
the list.

ADR-023 joined them at `v2.60.0` and reached the second state from a third
direction. It was never a divergence: it recorded a path added to the
off-limits set beyond the default the rule offers, which the rule invites a
project to do. `git.md` then took that addition into the default set itself,
with the reasoning the record gave -- a pointer executes nothing, so no gate
reads it, and one line replaces every rule the project binds. So the record now
describes an inherited rule, and the entry in `CLAUDE.md` 2.5 that looked like
a local extension is the template's own default. Read it the same way as the
other two: adopted upstream, nothing to maintain here.

All five are recorded against `quality.md`, `docs.md` and `git.md`, and the
first two carry four of them, so the cheap way to carry that position forward
is to ask whether either moved at all before re-reading any record. Neither did
between `v2.54.0` and `v2.56.0`; `quality.md` moved and `docs.md` did not
between `v2.56.0` and `v2.57.0`, and again between `v2.57.0` and `v2.59.0`;
neither moved between `v2.59.0` and `v2.60.0`, which is the case that costs
nothing; `quality.md` moved and `docs.md` did not between `v2.60.0` and
`v2.61.0`. Ask the question rather than assume the answer, because a range that
leaves both files alone is the common one:

```bash
git -C docs/solid-ai-templates ls-tree --name-only <new-tag> templates/base/core/quality.md templates/base/core/docs.md
git -C docs/solid-ai-templates diff --stat <old-tag> <new-tag> -- templates/base/core/quality.md templates/base/core/docs.md
```

The first command MUST name both files, and reading its output is the whole
point of running it. A mistyped or upstream-renamed path is dropped from the
listing rather than reported, and it is dropped from the second command too --
which then prints nothing and exits zero, the same nothing a range that touched
neither file prints. One name back instead of two means the second command
answered a question about one file while reading as though it had covered both.

With both names confirmed, empty output from the second means no record in the
list can have been touched and the paragraph above still holds. Any output
names the file to read, and from there the record that bounds it.

A named file is not a moved rule, and the second command cannot tell them
apart. `v2.59.0` reported `quality.md` moving 132 lines, every one an addition
and none a deletion: five new sections on revisit triggers, sweeping a
workaround comment, destructive operations, a detector's cost and a spike's
corpus. The character-set record bounds a rule in that same file, under Code
style, and none of the 132 lines reach it -- all three hunks land ahead of that
section, and the diff matches nothing for the vocabulary the record is written
in. So the record is unrefuted and stays where the paragraph above puts it.
Read the diff to the record's own subject before treating a named file as a
finding; the range that moves a file without moving the rule is as common as
the range that moves neither.

`v2.61.0` is the same shape at a smaller size, and it is worth recording
because the file moved rather than because the rule did. `quality.md` moved 54
lines in two hunks: one widens the ticket-citation ban to reach commented
configuration, the other appends a mechanical comment-layout check. Both land
below the character-set rules, which the range leaves untouched -- identifiers
stay ASCII-only, and comments, docstrings and string content keep carrying no
restriction at all. The character-set record is unrefuted a second time and
still stands the stricter way round.

A clause can also be correct upstream and wrong here. The templates repository
writes rules for itself as well as for its consumers, so a rule about how it
governs its own records can ship inside a template and read as binding on this
project, where the same words mean something else. Fixing that at the source
beats recording a local divergence, which then needs maintaining forever. The
precedence clause `v2.49.0` shipped was this case, and was scoped upstream
rather than declined here.

### 4.2 Record a decision

Copy `docs/decisions/TEMPLATE.md` to `docs/decisions/NNN-slug.md`. Fill the
YAML front matter — `id` matching the filename, `status`, `date`, a `category`
from the closed set, and both link fields even when empty — then the
`Upstream:` line naming a candidate template file or `none`, then the
sections. Keep every sentence to 40 words and every paragraph to 80; 3.14 and
3.16 are the gates.

Superseding an earlier record updates both sides in the same change: the new
record lists it in `supersedes`, and the old one gets `status: Superseded` and
the new id in `superseded_by`. 3.16 fails if either side is missing.

A record that defers something carries its revisit trigger on a line opening
`**Revisit trigger:**`, or `**Revisit trigger for (N):**` where the record
numbers its decisions. The form is what makes the search work — nothing polls
a trigger, so the only thing connecting an actor to a record that names their
action is a grep for it:

```bash
grep -rn 'Revisit trigger' docs/decisions/
```

The line names the condition and what would detect it: a scheduled check, a
gate that fails, or the surface a reader would notice it on. Where nothing
would, say that detection is a person looking. A trigger that fired and one
that has not read identically from the text, so the sentence that says who is
watching is the only thing separating them.

A merged record is immutable in what it claims, not in how it reads. Editing
one for readability alone is a format migration: make the change, confirm with
`git diff --word-diff` that only connectives and capitalisation moved, and say
readability-only in the commit. Anything that changes a claim needs a new
record instead.

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

Run before a minor or major release or a visibility change, and at milestone
boundaries. A patch release owes no audit. 3.23 gates the release case: the
newest report must not be older than the release before the one being cut. One
report can therefore cover two releases cut on the same day, which is
deliberate and is the whole of what ADR-032 changed.

Every release owed one until v0.4.4, and ADR-033 records why that stopped: two
consecutive declines left three releases resting on a single report, which is
the shape the gate exists to refuse. Scoping the obligation to releases that
add surface is what makes running it the cheaper option than declining it.

Declining the audit for a release that owes one is allowed and takes a document
— `docs/audits/YYYY-MM-DD-360-skipped.md`, naming the release and the reason.
It clears the same gate and lands in the release pull request, where a reviewer
reads it. Four releases were cut with no audit and no record of the decision,
which is what the gate and this paragraph exist to stop repeating.

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

Releases are tagged and published on GitHub. The distribution is not on a
package index, and whether it ever is has not been decided. #70 held that
question and was closed unanswered per ADR-016; reopen it rather than filing a
replacement.

To cut a release:

1. Check `git branch --no-merged main` and `git fsck --unreachable` for work
   that would be lost
2. For a minor or major release, run a 360 audit per 4.4; do not ship with
   critical findings open. A patch release skips this step and owes no record.
   3.23 gates it — it was ungated until v0.4.0, and four releases skipped it
3. Branch `chore/release-vX.Y.Z`, set `__version__` in `src/pyomb/__init__.py`
   — hatchling reads it, so that literal is the only place a version lives
4. Cut the `Unreleased` block of `CHANGELOG.md` into a dated `[X.Y.Z]` entry,
   add its compare link beside the others at the foot of the file, and move
   the `Unreleased` link to compare from the version just cut.
   `tests/test_changelog_release_entry.py` fails until all three are done.
   Doing it on this branch is what puts the entry inside the tagged sdist —
   done afterwards it corrects `main` and leaves the published archive
   describing the release before this one, which no later edit reaches
5. Point the README quick start install command at the wheel the new tag will
   carry. `tests/test_readme_install_command.py` fails until it matches. Doing
   it on this branch is what keeps the README inside the tagged sdist naming
   its own release rather than the one before it
6. Open the pull request, merge it, and wait for CI to pass on `main`
7. Tag with `git tag -a`, never a lightweight tag, or `git describe` reports a
   stale version to consumers
8. Push the tag

Merge the release pull request before any other pull request that is ready,
and tag before merging the rest. The `CHANGELOG.md` entry written in step 4
describes the tree as of the release commit, so anything merged between that
commit and the tag ships inside the release with no entry naming it. The
ordering is not enforced by anything — both pull requests are green and
mergeable in either order, and the wrong order produces a correct build whose
changelog is quietly incomplete.

Pushing the tag is the last manual step. `.github/workflows/release.yml` fires
on any `v*` tag and does the rest: it refuses a tag that does not name the
version the package reports, builds the wheel and the sdist, creates the
release record if the tag has none, attaches the distribution, then generates
the SBOM and attaches that. ADR-011 carries why the SBOM is generated from an
environment holding only the wheel, and why the distribution is uploaded before
the SBOM exists.

`release.yml` first executed on `v0.2.0`. Where it changes, rehearse the
changed steps by hand before the tag rather than after. A tag is the trigger
and cannot be taken back, so the pipeline gets no cheap first failure, and the
whole path runs locally: `python -m build`, `python -m twine check dist/*`,
then the SBOM generated against an environment holding only the wheel. Build
that environment without a package installer, as the workflow does with
`uv venv`; an ordinary virtual environment carries pip, which the generator
then lists as a component and the workflow's assertion rejects.

Do not create the release by hand first. The workflow creates it when absent,
so a hand-made one only risks racing it; if you have already made one, the
workflow uploads into it rather than failing.

`v0.1.0` predates the workflow and carries no assets. It is left that way
deliberately — assets built now from a later tree would not be what that tag
was. See ADR-011.

Before any publish to a package index: claim the name per ADR-002, and publish
from CI only, never from a local machine. #70 carries the acceptance criteria
for that work, including Trusted Publishing over a long-lived token; it is
closed rather than open, so nothing surfaces it until someone reopens it.
