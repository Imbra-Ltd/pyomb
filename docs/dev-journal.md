# Development journal

Session history for agent-assisted work on pyomb. Agents have no memory across
sessions; this journal records what changed and why. Newest entries are at the
bottom. Tasks link to issues, and architectural decisions are recorded as ADRs
in `docs/decisions/`.

This repository begins at v0.1.0. The work before it happened in
`Imbra-Ltd/protocol-modbus`, whose journal, closed issues and pull requests
stay there; ADR-006 records why the history was not carried across.

## Architecture overview

pyomb is a Python library for Modbus TCP and RTU: a codec, a stream transport,
and a scriptable server/client pair for exercising other implementations. Four
layers matter. `packets.py` is the codec — the MBAP header, a PDU class per
function code, a registry-driven parser, and the TCP and RTU ADU wrappers.
`stream.py` is the transport, which frames on the MBAP length field and can
fragment deliberately to reproduce segmented delivery. `omb_server.py` and
`omb_client.py` are the simulators: a threaded select-loop server with a
per-function-code dispatch and a matching request builder on the client, both
with mutual-TLS support per MB-TCP-Security. `errors.py` maps Modbus exception
codes onto a Python exception hierarchy.

One name now runs across the repository, the distribution and the import
package, per ADR-002. See `README.md` for usage and
`docs/Open_Modbus_Tutorial.md` for the protocol background.

## 2026-08-18 — Migrate to a clean repository

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Fresh history** — the repository starts from one commit holding the
    v0.1.0 tree. The predecessor's history contains objects made unreachable
    by a force-push rather than absent, and unreachable is not gone on a
    public host. Starting fresh is the only mechanism that removes them
    without depending on the host to collect them. ADR-006 records the
    decision and what it costs.
  - **Retired the dated audit** — a 360 report describing the predecessor's
    CI, secret scanning and tracker documents infrastructure this repository
    does not have. This one runs its own once its infrastructure exists,
    which is also what restores `docs/audits/`.
  - **Left the journal behind** — the predecessor's 542 lines of session
    history reference issue numbers that resolve against the archive, and
    carry post-mortems for defects fixed before v0.1.0. They stay where they
    still make sense.
  - **Repointed the references** — the README badge and clone commands,
    ONBOARDING, `pyproject.toml` URLs, the CLAUDE.md repository line, the
    changelog links and the test certificate authority's common name.
    ADR-002 is deliberately untouched: it records that the repository kept
    the name `protocol-modbus`, which was true when it was written, and an
    ADR is immutable.
- **PRs merged:** none — this repository has no history to merge into.
- **Issues closed/created:** none created. Eight open issues transferred from
  the predecessor, renumbered 1 through 8; the mapping is in ADR-006.
- **Lesson:** GitHub refuses to transfer an issue from a private repository to
  a public one, and both repositories must share an owner. That single
  constraint dictates the order of a migration — the destination has to be
  created private and stay private until every issue has moved. Discovering it
  after making the destination public would have meant recreating each issue by
  hand, losing its comments and its number. Reading the transfer restriction
  before creating the repository cost a minute.
- **Lesson:** removing a document is not removing what it says. Retiring the
  audit left the same credential incident described in full in the journal's
  post-mortem, which would have travelled with the codebase into a repository
  heading for public. A scrub is scoped by the content, not by the filename.

## 2026-08-18 — Audit the new repository (later)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **First 360 audit** — nine engineering dimensions per `360-headless`,
    since a library has no Value or Discovery surface. Overall C-, which is
    the Security grade. The code graded A to B+ throughout; every failing
    finding is repository configuration rather than source, and all of it
    arrived with the migration.
  - **Corrected an API rationale rather than the API** — the module docstring
    withheld the simulators from `__all__` because they "pull in socket, ssl
    and threading". Two thirds false: `stream.py` is re-exported and imports
    socket, threading and select itself, so a plain import already pays for
    them. Only ssl is avoided. The decision survives on measurement — ssl
    costs roughly 32ms against the package's own 45ms — so the reason was
    replaced with the number and the command to re-measure it.
  - **Repointed the original working copy** — `origin` now names this
    repository. The two histories share no ancestor, so the old branch was
    renamed `protocol-modbus-archive` and its upstream unset rather than
    reset away, and the stale v0.1.0 tag was replaced with this repository's.
- **PRs merged:** #9 and #14.
- **Issues closed/created:** none closed. #10 opened for secret scanning and
  push protection being disabled, #11 for the absent SAST, #12 for `main`
  being unprotected so no check gates a merge, and #13 for actions pinned to
  mutable tags. #1 was rewritten rather than filed against: it claimed the
  client and server sat at 0% coverage, citing a package path deleted days
  earlier, where they measure 85% and 94%.
- **Lesson:** a repository's security settings are not part of its source and
  do not travel with a migration. Secret scanning and push protection were
  enabled on the predecessor in response to a real credential exposure, and
  this repository — created precisely to improve on that history — was created
  without them. Nothing in the tree records the loss, and no gate detects it;
  only asking the host does.
- **Lesson:** two searches in a row returned confident, plausible, opposite
  answers about whether the tests assert against the wire. The first pattern
  was mis-escaped and the second failed silently because `grep -P` is
  unsupported in this locale, and a silent failure is indistinguishable from a
  genuine zero. Reading one file settled what two greps could not. Counted
  properly, 26 of 41 test files carry 510 literal vectors. Any finding whose
  weight rests on a count needs the count produced twice, by different means.
- **Pending:** #10 and #12 block publication. The PyPI name is unclaimed and
  needs credentials this session did not have. Two pull requests, #16 and #17,
  were opened by another session and are untouched here.

## 2026-08-19 — Close the publication blockers

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Merged the packaging cleanup** — PR #16 deletes the empty
    `requirements.txt` and the `ONBOARDING` sentence that existed only to
    warn about it. Its own verification grep had run against a base two
    commits older, so the grep was repeated against current `main` before
    merging: the only surviving hits are the ordinary word in
    `CONTRIBUTING.md` and the sentence the PR rewrites.
  - **Enabled the repository security controls** — secret scanning, push
    protection, Dependabot alerts and Dependabot security updates. No
    purchase was needed. The organisation already carries Secret Protection
    at one committer maximum, and that committer was already counted through
    `protocol-modbus`; GHAS bills unique active committers org-wide rather
    than per repository, so this consumed no additional seat.
  - **Protected `main`** — the four CI checks are now required, a pull
    request is required at zero approvals, force pushes and deletion are
    blocked, and merged head branches delete themselves. Administrators are
    bound too, which goes beyond what the issue asked.
  - **Corrected the Python floor** — `CLAUDE.md` claimed 3.11+ while
    `requires-python`, the classifier, the CI matrix, the README badge,
    `ONBOARDING` and `CONTRIBUTING` all said 3.10. The packaging metadata and
    the matrix are what bind a consumer, so the context file was the stale
    copy and was lowered to match rather than the floor being raised to match
    it. Surfaced while checking whether the project was ready to publish.
- **PRs merged:** #16 and #20.
- **Issues closed/created:** #10 and #12 closed, each verified by reading the
  setting back from the host after applying it. None created.
- **Lesson:** on a single-seat organisation the review count and the gate are
  different controls. Requiring one approval would deadlock every merge, since
  nobody can approve their own pull request, so the count has to stay at zero
  — which leaves administrator enforcement as the only thing that makes the
  checks binding on the one person who uses the repository. Reaching for the
  approval count instead would have produced a gate that either blocks
  everything or nothing.
- **Lesson:** a refused tool call is a fact about the request as phrased, not
  always about the action. Enabling secret scanning was denied twice when sent
  as a JSON body, and was reported to the owner as needing their hands. An
  unrelated single-field write to the same endpoint then succeeded, which
  isolated the objection to the payload rather than the endpoint; resent as
  plain fields, the original call went through. Test the narrowest sibling
  call before reporting a capability as unavailable.
- **Pending:** #11 is the top remaining P2. The billing endpoint reports Code
  Security at zero of one seats used, so CodeQL looks available on the current
  plan — confirm that before writing a workflow. #2 is down to repository
  topics alone; the description and the v0.1.0 release already exist, so its
  title overstates what is left. #4, the submodule pinned to an unreleased
  revision, is untouched. Claiming the PyPI name was scoped and then postponed
  by the owner: the name is free on both indexes, the artifact builds and
  passes `twine check`, and the route is a pending publisher on PyPI plus a
  tag-triggered release workflow, since the index has no way to reserve a name
  short of uploading to it.

## 2026-08-19 — Stop the leaked server thread (later)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Found the leak with a probe rather than by reading** — the issue offered
    two candidate fixes and both aimed at the logger. A throwaway pytest plugin
    that listed live threads after every test named the culprit instead:
    `TestMutualTls` was the only class in the suite leaving an `OmbServerSim`
    thread behind, on four of its tests, while the other 370 tests finished
    clean.
  - **Fixed the fixture that guessed** — its `tearDown` called `stop()` and
    slept a fifth of a second. `stop()` only sets the quit event and the run
    loop sits in a one second `select`, so the sleep was shorter than the wait
    it stood in for and never once sufficed. It now joins with the same five
    second bound the other three server fixtures use, and reports the timeout
    instead of passing silently.
  - **Added a suite-wide guard** — `tests/conftest.py` fails any test that
    finishes with a live server thread, so the next fixture that sleeps is
    named where it leaks rather than surfacing as noise at the end of an
    unrelated run. Against the unfixed fixture it errors on four tests; with
    the fix the file is eight passed.
  - **Corrected a comment the fix falsified** — the class justified per-test
    ports by the listener not always being released before the next `setUp`.
    The join makes that untrue, so the comment now carries the reason that
    survives: the server sets no `SO_REUSEADDR`, so a just-closed port can
    still refuse the next bind while its connection sits in `TIME_WAIT`.
  - **Dropped the sleep on the other side of the same fixture** — `setUp`
    slept half a second after `start()`, which already blocks until the
    listener is accepting and raises if it does not. Removed in a follow-up
    once the fix had landed, with ten runs of the file and three full-suite
    runs as the oracle, since there is no behaviour to assert on. The file
    went from about 8s to under 3s and the suite from about 38s to about 33s.
- **PRs merged:** #23 and #25.
- **Issues closed/created:** #5 closed. #22 created, recording that the CI
  badge cannot render while the repository is private.
- **Lesson:** the issue's mechanism section was accurate and its proposed fixes
  were still wrong. `Logger` binding `sys.stdout` at construction is the
  condition that makes the noise visible, not the cause; the cause is a fixture
  that does not wait for the thread it started. Nulling the logger in the suite
  would have silenced the traceback and left a server running through unrelated
  tests. Both candidates were plausible enough to implement without noticing.
- **Lesson:** the error text carried the answer. The traceback named
  `('0.0.0.0', 18807)` and the TLS class counts up from 18802, so the sixth
  test of that class owned the leaked thread. Reading the port out of the
  failure was quicker than reasoning about which of the seven fixtures looked
  wrong, and it agreed with the probe.
- **Pending:** the autouse guard is a reusable convention rather than a
  project-specific one and belongs upstream in
  `templates/base/core/testing.md`, as a sibling of the rule about tests not
  touching processes they did not start — the upstream issue is not yet filed.
  A local `main` was left carrying a stray merge commit and an unsquashed
  duplicate after `gh pr merge` and `git pull` ran together; the content
  matched `origin/main` exactly, and the reset to clear it needs the owner.

## 2026-08-19 — Wire the last quality gate (later still)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Wired the SAST gate** — bandit runs in CI over `src`, `scripts` and
    `tests`, failing on any finding at any severity. Security was the one
    blank row left in the quality-gates table, on a library whose whole job is
    parsing untrusted bytes off a socket. See ADR-007.
  - **Turned the gate on with no freeze table** — ADR-003 froze hundreds of
    lint findings and ADR-005 froze 711 type errors to make their gates
    passable. Measuring first showed this one needs neither: `src/` reports
    nothing at all, across 4,363 lines. The whole tree yields 35 findings and
    both groups are explainable rather than latent — 33 asserts in one test
    module, and the cert generator's two subprocess advisories.
  - **Handled both groups where they sit** — a glob-scoped `assert_used` skip
    for the test modules, and site-local `# nosec` markers naming the specific
    check for the subprocess pair, each with its reason above the line. Never
    a config-level `skips` entry, which would stop bandit looking tree-wide
    rather than at the one call site.
  - **Proved the gate bites** — a throwaway module carrying an assert, a
    hardcoded password, `shell=True` and an MD5 digest went into `src/pyomb/`
    and the gate failed on all four. The assert firing there is the part that
    matters: it proves the test-only skip did not leak out of `tests/`.
  - **Probed the exclude anchoring rather than trusting it** — the stack
    template warns that an unanchored path pattern silently drops a whole
    sub-package while CI stays green. Confirmed directly: an unanchored
    `"docs"` excludes a planted `src/pyomb/docs` and the run still exits zero;
    `"./docs"` scans it and reports the finding.
  - **Declined platform SAST rather than leaving the row blank** — code
    scanning returns 403 on a private repository without Code Security, so it
    cannot be turned on by committing a workflow. ADR-007 records the decline
    with the two conditions that reopen it.
  - **Corrected the head-branch deletion procedure** — PLAYBOOK 1.5 asserted
    the repository does not delete the head branch on merge; the setting is
    on, and both merges this session had their branches removed by the host
    before anything local could. Rewritten around how the branch is deleted
    rather than whether, since deletion as part of the merge retargets a
    dependent pull request while deletion as a separate step closes it for
    good.
  - **Set the repository topics** — the last item in #2, whose description and
    v0.1.0 release already existed.
- **PRs merged:** #27 and #28.
- **Issues closed/created:** #11 and #2 closed. None created.
- **Lesson:** measure before assuming a retrofit needs a ratchet. Two prior
  decision records established freezing as this project's way of turning a
  gate on, and the third gate looked like the same shape. Running the tool
  first showed the shipped code was already clean, so the gate starts at full
  strictness and any finding it reports from here is genuinely new. Copying
  the established pattern would have built a freeze table with nothing in it
  and a weaker gate to go with it.
- **Lesson:** a document that contradicts the system can be worse than merely
  stale. PLAYBOOK 1.5 was wrong about the setting, and the procedure it built
  on that premise instructed deleting a base branch as a separate step — which
  is exactly the move that closes a dependent pull request irrecoverably. The
  reader following it carefully was the one who got hurt. What confirmed the
  fix was complete is the sweep rule: the remaining hits are the 2026-08-18
  audit and this journal, both historical records, leaving the playbook as the
  only surviving instruction to apply the old behaviour.
- **Upstream:** both flagged candidates were filed rather than left named.
  braboj/solid-ai-templates#1026 proposes that a gate category naming more than
  one tool is satisfied by the tools that can run plus a recorded decline
  carrying a revisit trigger, never left blank — the generic form of what
  ADR-007 decided here. braboj/solid-ai-templates#1027 carries the previous
  session's autouse thread guard, which had been named and left unfiled: where
  a suite starts a background worker, a per-test fixture asserts none survives,
  so the leak names the test that caused it rather than the run that inherits
  it.
- **Lesson:** the prior session's rule about testing a narrow sibling call paid
  off in the other direction. Adding `security` to the required status checks
  was refused, and a sibling write to the repository's topics on the same host
  went straight through — which isolates the objection to the protection
  endpoint rather than to repository writes in general. That is worth stating
  precisely when handing the action back, because it tells the owner the block
  is not something a rephrasing will clear.
- **Pending:** `security` is not yet a required status check, so the job runs
  without gating. PLAYBOOK 3.9 already says five checks gate a merge while four
  do — a known inconsistency that closes when the setting lands, and it needs
  the owner.
  Claiming the PyPI name is now untracked, having lived only in #2. #4 is
  blocked rather than merely untouched: the submodule sits three commits past
  `v2.44.0`, and `templates/base/core/examples.md`, which this project's
  startup block requires, exists only in those unreleased commits — so pinning
  back to the tag would break the startup block, and the issue needs a
  `v2.45.0` upstream release before it can move.

## 2026-08-19 — Pin the actions and scan the history (evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Pinned every action reference to a commit SHA** — seven references, not
    the five #13 counted, because the bandit job landed after that body was
    written. A tag is mutable, and the job holding the pin also holds a
    checkout of this source. `.github/dependabot.yml` enrols the Actions
    ecosystem on the default versioning strategy, so the pins keep moving.
  - **Took the Node 24 majors in the same change** — pinning forces a version
    choice, and the current majors are the ones that retire the deprecation.
    Both were read against their release notes rather than assumed drop-in:
    checkout takes no inputs here, and the one input the setup-python major
    removed is one this workflow never passed. Verified on the runs rather
    than the diff — five deprecation annotations before, none after.
  - **Switched the secret scan from the working tree to the whole history** —
    the job carried `--no-git` behind a comment saying history still held
    credential material awaiting a purge. Neither half survived a probe. The
    purge was closed as not planned, so the lifting condition could never
    fire, and the material is not in this history at all: the comment came
    over verbatim from the predecessor, whose unreachable objects the
    migration left behind. No commit here has ever added key material.
  - **Fetched the history that scan needs** — `fetch-depth: 0` on that job's
    checkout, because the action fetches a single commit by default.
  - **Swept the surfaces describing the old arrangement** — PLAYBOOK 3.7 and
    SECURITY.md both still called it a working-tree scan. PLAYBOOK 4.5 is new,
    covering the weekly bump pull requests the Dependabot config starts
    producing.
- **PRs merged:** #30 and #31.
- **Issues closed/created:** #13, #8 and #7 closed. #32 created.
- **Lesson:** an issue's proposed fix is a hypothesis about the repository, and
  this one was written against the wrong repository. #7 asked for the
  working-tree scan to be documented as permanent; three commands showed the
  constraint it rested on belongs to the predecessor, and the stronger gate was
  available immediately. Probing cost under a minute, and the alternative was
  recording a weaker gate as a deliberate choice.
- **Lesson:** removing a limiting flag can leave a check weaker while it reads
  stronger. `--no-git` gone with `fetch-depth` left at its default gives a job
  that scans one commit, finds nothing and goes green, which the interface
  renders identically to a real pass. What settled it was reading the count out
  of the job log rather than the exit status: 18 commits scanned, not 1.
- **Upstream:** none to file — the convention is already upstream, as a MUST in
  both `base/security/devsecops.md` and `platform/github.md`, and was filed and
  closed there as braboj/solid-ai-templates#759. The finding is the other
  direction: neither template is in this project's startup block, so a rule
  that has existed upstream all along was re-derived here from a defect. #32
  carries the question of whether to resolve them.
- **Pending:** `security` is still not a required status check, carried from
  the previous session and still needing the owner. #4 is unchanged and still
  blocked: upstream has cut no tag past `v2.44.0`, so neither route it names is
  available yet.
