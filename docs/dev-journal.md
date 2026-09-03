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
`docs/specs/Open_Modbus_Tutorial.md` for the protocol background.

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
- **Upstream:** two conventions, and they went opposite ways. The
  full-history-scan rule was already upstream as a MUST in both
  `base/security/devsecops.md` and `platform/github.md`, filed and closed there
  as braboj/solid-ai-templates#759 — so nothing to contribute, and the finding
  runs the other direction: neither template is in this project's startup
  block, so a rule that existed upstream all along was re-derived here from a
  defect. #32 carries whether to resolve them. The second convention is new and
  filed as braboj/solid-ai-templates#1028: a gate whose input scope is a
  configuration parameter has to be verified by the coverage it reports rather
  than its exit status, because a scope collapsed to near-nothing still exits
  zero. The existing rules cover a gate that was skipped and a verdict that was
  misread, not one that ran green over an almost empty input.
- **Pending:** `security` is still not a required status check, carried from
  the previous session and still needing the owner. #4 is unchanged and still
  blocked: upstream has cut no tag past `v2.44.0`, so neither route it names is
  available yet.

## 2026-08-19 — Resolve the platform template layer (late evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Resolved the platform axis of the template manifest** — the mandatory
    startup block listed the chain for `stack-python-lib` and no platform
    template at all. ADR-001 walked the stack axis and stopped, and nothing
    flagged it because no stack in `templates/manifest.yaml` declares a
    platform dependency: the platform is chosen by where the repository is
    hosted, on an axis the stack graph never touches. A single-axis walk
    terminates cleanly and looks finished. ADR-008 adds
    `templates/platform/github.md` and `templates/base/workflow/issues.md`,
    which the manifest names as its dependency, and declines
    `base/security/devsecops.md` on the evidence that no library stack in any
    language depends on it.
  - **Fanned the CI gates in to one required check** — the workflow fanned out
    and never fanned in, so branch protection named four contexts individually
    and `security` was not among them. Bandit has run green and blocked nothing
    since ADR-007 wired it. The new `gate` job needs every other job and
    requires each result to be exactly `success`, so a skipped or cancelled job
    fails rather than passes, and a job added later binds by joining the needs
    list instead of by someone remembering to edit a repository setting.
  - **Guarded the gitleaks download** — the step ran `curl` without `-f`, which
    reports success on a 404 and writes the response body into the archive; the
    run then failed two lines down at `tar` naming a corrupt archive rather
    than a missing release.
  - **Corrected two issues whose premises had expired** — #3 asked for a
    `CONTRIBUTING.md` rewrite that had already shipped, and #22 deferred to an
    issue that was closed and had never covered the condition it was deferring
    on. Both were 2026-08-13 audit findings raised against the predecessor
    repository and carried across the migration unchecked, the same way #1 was.
    What #3 actually left was two git rules the file never carried, and those
    shipped instead of the rewrite.
- **PRs merged:** #37, #39, #40 and #42.
- **Issues closed/created:** #32, #38 and #3 closed. #36 and #38 created. #3
  and #22 had their bodies corrected before anything else happened to them —
  both rested on premises that had expired, and closing #3 on the original
  text would have recorded a rewrite that never took place.
- **Lesson:** an omission produced by a resolution procedure is invisible in its
  own output. Reading the startup block against the templates would never have
  found the missing platform layer, because the block is internally consistent
  and every file it lists is correct — what surfaced it was reading the
  manifest that generates the block instead of the block itself. Where a
  derived artifact can be wrong by omission, the check has to run against the
  deriving rule, not the artifact.
- **Lesson:** two of the three items planned for this session rested on false
  premises, and both cost about a minute to falsify. A stale ticket is
  expensive in a specific way — #3 would have produced a full rewrite of a file
  that needed two sentences, and the rewrite would have looked like real work
  the whole time. Issues that survive a repository migration are the ones to
  re-verify first; three of the seven open here were raised against a tree that
  no longer exists.
- **Lesson:** a measurement in the wrong unit reads exactly like a finding.
  Checking the added prose for the 80-column rule, `awk length` reported 81 on
  a compliant line and `wc -m` agreed, because the line carries an em-dash and
  neither tool was counting characters — one counts bytes, and the other counts
  bytes too in a non-UTF-8 locale. The line is 79 characters. Two tools
  agreeing is not corroboration when they share the same blind spot.
- **Upstream:** four filings, all filed rather than named.
  braboj/solid-ai-templates#1029 covers the startup-block rule, which says to
  list every template the project depends on and thereby reads as one graph
  walk — it would omit the platform layer identically for
  `platform-gitlab` and `platform-linear`.
  braboj/solid-ai-templates#1030 is a factual correction rather than a
  convention: `platform/github.md` states CodeQL is free on public and private
  repositories, and ADR-007 already measured the 403 that refutes it for a
  private one. Until it is corrected, ADR-007 outranks the template on that
  point under the precedence order in `CLAUDE.md`.
  braboj/solid-ai-templates#1031 came out of the end-of-session audit: the
  templates state the skipped-is-not-passed rule and give the fan-in that
  encodes it, but never say the encoding has to be verified on the skipped
  path. A failed upstream job trips a correct fan-in and a naive one alike,
  so only a skipped upstream tells them apart, and that is the run nobody
  reaches for.
  braboj/solid-ai-templates#1032 is the cohort rule this session paid for
  twice: a migration invalidates every open issue at once, because each is a
  claim about a tree that no longer exists while the issue itself survives.
  The existing rules verify one claim at a time and never name the trigger
  that spoils a batch.
- **Settings:** branch protection was repointed at `gate` as the sole required
  context, by the owner through the repository settings page. That is the half
  the workflow could not carry — until it landed the new job reported and bound
  exactly as much as bandit did, which is nothing. `security` now blocks a
  merge for the first time since ADR-007 wired it. Every other protection value
  survived the edit unchanged: administrators still bound, zero required
  approvals, no force-push, no branch deletion. `CONTRIBUTING.md` section 6 and
  PLAYBOOK 3.9 followed in #42 rather than ahead of it, because the two
  surfaces flip in opposite directions and a sentence describing a state that
  does not hold yet is the same defect facing the other way.
- **Pending:** #4 only, unchanged and still blocked — upstream has cut no tag
  past `v2.44.0`, so neither route it names is available. Worth carrying
  forward instead: #1 and #6 come from the same 2026-08-13 audit cohort as #3
  and #22, both of which turned out to be describing a repository that no
  longer exists. Re-verify their premises before scoping either.

## 2026-08-19 — Settle the packet signature contract (night)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Settled one signature per packet operation** — `ModbusPacketAbc`
    declared `serialize` with `**kwargs` and `deserialize` as an instance
    method taking `**kwargs`, `ModbusPdu` redeclared both with a format
    parameter, and each of the 34 implementations dropped whatever it did not
    use. Every step narrowed what the one above promised, so a caller holding
    the abstract type could not call either operation without knowing the
    concrete class it really had. The contract is now `serialize(self)` and
    the classmethod `deserialize(cls, stream)`, declared once. ADR-009 carries
    the decision.
  - **Split the format escape hatch out under its own name** — caller-supplied
    packing is something the generic PDU genuinely offers and no concrete PDU
    may, because a concrete PDU's layout is fixed by the specification and
    honouring a caller's format there emits a frame a real device rejects. It
    moved to `ModbusPdu.pack(fmt)` and `ModbusPdu.unpack(stream, fmt)`, so a
    subclass declining to offer it breaks nothing. `fmt` is required there
    rather than falling back to the class default on a falsy value, which is
    what `base/core/config.md` asks for.
  - **Shrank the mypy freeze** — `pyomb.packets` no longer suppresses
    `override`, and the entry it shared with `pyomb.stream` split in two so
    the one module still needing the code keeps it alone. Findings behind the
    freeze fell from 711 to 593.
  - **Re-verified two carried-forward premises before scoping either** — #1
    and #6 came from the same 2026-08-13 audit cohort as #3 and #22, both of
    which described a repository that no longer exists. Both held exactly:
    mypy reports 711 findings with 123 `override`, and coverage stands at 84%
    with `packets.py` at 79%.
  - **Repaired a PLAYBOOK reference to an issue that does not exist** — 3.5
    cited `#51` as tracking the two real defects behind the mypy freeze. The
    highest issue number in this repository is 46. The number survived the
    migration in ADR-006 while the issue it named did not, so a reader tracing
    it landed on nothing. It now names #45 and #46, and the paragraph records
    that the freeze has been narrowed once.
- **PRs merged:** #47 and #48.
- **Issues closed/created:** #6 closed. #45 and #46 created, carrying the two
  findings left out of this scope — the same narrowing in the sender
  hierarchy, and the client's optional socket attribute, which cannot be
  annotated without exposing 14 accesses under a code the freeze does not
  carry.
- **Lesson:** counting findings sizes a backlog; reading one finding's notes
  sizes the fix. The gate reports 123 `[override]`, which reads as 123 things
  to settle. mypy's `note:` lines print the two signatures side by side, and
  one of them showed the whole cluster is two defects — a variadic in the base
  that constrains nobody, and a parameter one class offers that its own
  subtypes must not. That collapsed 123 findings into about sixty lines in two
  base classes.
- **Lesson:** a suppression entry listing two modules cannot express a partial
  migration. `pyomb.packets` and `pyomb.stream` shared one `override` entry,
  so every code in it looked equally earned by both. Splitting the entry was
  the only way to record that one module was done, and the split is the
  artifact that stops the next reader assuming the packets module still needs
  the code.
- **Lesson:** the breaking change was invisible from the source tree. Nothing
  under `src/` passed a format, the README never showed one, and a grep over
  `docs/` found nothing — the only callers were five lines in the test suite.
  It would have read as a dead capability safe to delete rather than one worth
  renaming. The suite was the sole evidence the escape hatch was used at all,
  which is an argument for reading it as a consumer rather than as coverage.
- **Lesson:** the ruff freeze bit a new file for the first time, as designed.
  `tests/**` is exempt from the `D` family only, and the per-file table cannot
  cover a file that did not exist, so the new test module failed on `UP032`
  for using `.format()` in the style every legacy module around it uses. The
  fix was to write the new file to the whole rule set. A freeze that holds
  legacy code where it is, and gates new code fully, looks exactly like this
  from the inside.
- **Upstream:** one filing. braboj/solid-ai-templates#1033 against
  `templates/base/core/quality.md`. The templates name the Liskov principle
  once, in `testing.md`, from the testing angle, and carry no rule that would
  stop a variadic being declared on an abstract operation — nor one for the
  legitimate case where a class part-way down a hierarchy offers a capability
  its own subtypes must not, which is resolved by giving the capability its
  own name rather than widening the shared contract.
- **Pending:** #4, unchanged and still blocked. Upstream has cut no tag past
  `v2.44.0` and the submodule sits three commits beyond it, so neither route
  the issue names is available; re-checked this session rather than assumed.
  Also pending, and needing a decision rather than work: PLAYBOOK 5 says the
  first PyPI publish is "Tracked as #2", but #2 is closed and was about
  repository metadata and the initial release, and no open issue tracks the
  publish. Either the sentence loses its tracker or the work gets one, and
  filing planned release work is the owner's call, so it is flagged rather
  than fixed. Worth carrying forward: #1 is now measured rather than claimed —
  `packets.py` at 79% is the only module under the floor, and it is the codec.

## 2026-08-19 — Cover the packet error branches (late night)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Pinned the error type every packet operation reports** — `packets.py`
    was the only module under the floor at 79%, and it is the codec, where an
    untested branch means a wrong frame on the wire. Reading the uncovered
    lines rather than counting them settled the scope: of 226 uncovered
    statements, about 210 were one repeated block, the `try`/`except` around
    each `serialize` and `deserialize` that re-raises as `ModbusPacketError`.
    It was written per class forty-odd times and pinned nowhere, so a class
    whose handler was missing or mis-scoped would let a raw `struct.error`
    out through an `except` clause no caller ever wrote. The module now
    stands at 99%.
  - **Two inputs carry all 34 concrete classes** — an empty stream, which
    nothing decodes from and a peer can send, and a one-element tuple holding
    a value past every unsigned format the specification uses. `struct`
    refuses that tuple whether the field it lands on is a scalar or a
    sequence, which is what removes the need for a per-class table of field
    types. The tests collect their subjects from the module rather than
    listing them, so a packet class added later is covered the day it lands.
  - **Covered the logger and the derivation with a history** — `logger.py`
    went from 63% to 100%. The whole of `file_handler` and `log_to_file` was
    untested, including the appending form that replaced a `str.replace`
    derivation. An empty search string makes `str.replace` insert between
    every character, so an entry point without an extension produced names
    such as `.logs.loge.logr.logv.loge.logr.log`.
  - **Shared the class enumeration rather than copying it** — the signature
    contract from the previous session had the only copy. It moved to
    `tests/packet_hierarchy.py` and both contracts read it from there.
  - **Filed the one hole the new contract does not close** — #50. `ModbusPdu`
    computes `len(...)` outside the guard in both `serialize` and
    `deserialize`, so a scalar `data` field or a non-sized stream leaves a raw
    `TypeError`. The contract test passes only because it supplies `data` as
    the sequence the constructor documents. Filed rather than fixed: no
    production code belongs in a coverage change.
- **PRs merged:** #51.
- **Issues closed/created:** #1 closed. #50 created, carrying the `ModbusPdu`
  guard hole. Neither path in it is reachable from the wire — the transport
  hands `deserialize` a `bytes` object and nothing builds a `ModbusPdu` with a
  scalar — which is why it is P3 rather than a defect against the codec.
- **Lesson:** a coverage number sizes the work, and the uncovered lines shape
  it. 226 statements across a 3,700-line codec reads as a module-wide testing
  effort. Bucketing the missing lines by statement text took one command and
  showed 210 of them were three lines repeated: `except Exception as e`, a
  message, a re-raise. That collapsed forty near-identical tests into one
  contract over a collected hierarchy, and the collection is what keeps the
  next packet class covered without anyone remembering to add it.
- **Lesson:** a test written against passing code proves nothing about broken
  code. Both sets were run against a mutated source before being trusted —
  all 76 re-raise sites replaced with a bare `raise` produced 76 failures, and
  reinstating the `str.replace` derivation failed the two derivation tests
  with the `.logs.loge.logr...` shape in the error. Without that step a test
  asserting `assertRaises(ModbusPacketError)` around a call that raises for an
  entirely different reason would have looked identical.
- **Lesson:** the four statements left uncovered in `packets.py` are the
  `raise NotImplementedError` bodies in the abstract base, and `ABCMeta`
  refuses to instantiate the class that would reach them. Chasing 100% there
  means calling the unbound function, which asserts on how the base is wired
  rather than on what any object does. The honest report is 99% with the
  remainder named.
- **Lesson:** the ruff freeze bit again, and the same way as last session. The
  new contract module tripped `SIM117` for nesting `assertRaises` inside
  `subTest`. The per-file table cannot cover a file that did not exist, so a
  new test file is gated on the whole rule set while the modules around it
  keep their frozen codes. Fixing the finding took one line each.
- **Upstream:** none. The collect-the-subjects-rather-than-list-them shape is
  already carried by `testing-drift-guard` and `testing-ast-contract` in
  `templates/base/core/testing.md`, which introspect the live artifact for the
  same reason.
- **Pending:** #4, unchanged and still blocked, re-checked rather than
  assumed: upstream has cut no tag past `v2.44.0` and the submodule sits three
  commits beyond it, so neither route the issue names is available. Still
  needing a decision rather than work: PLAYBOOK 5 says the first PyPI publish
  is "Tracked as #2", but #2 is closed and was about repository metadata, and
  no open issue tracks the publish. Filing planned release work is the
  owner's call. Worth carrying forward: `omb_client.py` at 85% and
  `stream.py` at 85% are now the weakest modules, both above the floor and
  neither tracked by an issue.

## 2026-08-21 — Empty the freeze of real findings

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Moved the PDU length measurement inside the guard that converts** —
    `ModbusPdu.serialize` and `deserialize` each built their format string
    from a length taken before `pack()` or `unpack()` was entered, so the
    guard those two carry never saw it. A `data` field that is not a sequence,
    or a stream that cannot be measured, left a raw `TypeError` through an
    operation whose callers catch `ModbusPacketError`. Every other class in
    the hierarchy converts; this was the one that did not.
  - **Settled one signature for `run_once`** — `ModbusSenderAbc` declared a
    `burst` parameter its only implementation does not take. Burst is a
    property of the sender rather than of one run: it sets TCP_NODELAY on the
    socket the sender owns, and `ModbusTcpSender` already carries it as state
    through the constructor or `set_burst_mode`. The parameter came off the
    base, which is where ADR-009 put the same defect in the packet hierarchy.
  - **Fixed the milder form of it found on the way** —
    `ModbusStreamAbc.send` named its parameter `packet` where its own subtype
    named it `message`, so the keyword the supertype promised was one the
    subtype refused. mypy does not flag a rename under this project's
    settings. The base took the subtype's name: every call site passes
    serialized bytes positionally, so `message` is the accurate one.
  - **Gave the client's socket the optional type its teardown implies** —
    `disconnect()` clears the attribute, but it was inferred from its first
    assignment as `socket.socket`. Eight of the exposed accesses route through
    one private accessor that raises `ModbusNetworkError` naming the remedy;
    the other two are the teardown itself, which now returns quietly on a
    client holding no socket.
  - **Emptied the mypy freeze of real findings** — `override` left with the
    sender fix and `assignment` with the client fix. Remeasured by stripping
    every `disable_error_code` and counting rather than by adjusting the
    number in place: 594 findings, two codes, both of them annotations the
    tree does not yet carry. Nothing frozen is a defect any more.
- **PRs merged:** #53, #54 and #55.
- **Issues closed/created:** #50, #45 and #46 closed. None created.
- **Lesson:** an issue's own estimate of its size is a claim like any other.
  #46 said annotating the attribute would turn 14 accesses into findings and
  warned the sizing was part of the work. Applying the annotation and running
  the checker reported ten: mypy narrows the other four itself from an
  assignment earlier in the same method. The measurement took one probe and
  moved the scope by nearly a third before any of it was written.
- **Lesson:** a contract test that ignores a field to accommodate a known
  defect is the freeze anti-pattern wearing a different hat. The stream
  signature test compares parameter names, and one pair disagreed. Excluding
  names would have passed today and stopped the test looking forever, which is
  what ADR-005 says about turning off a strict sub-flag. Fixing the rename was
  smaller than weakening the gate, and the gate now asserts the whole
  signature.
- **Lesson:** the helper that reads a signature has to know what kind of
  method declared it. The packet version dropped the first parameter
  unconditionally, which is right for an instance method and a classmethod and
  wrong for a staticmethod — and `ModbusFragmenter` declares both its abstract
  operations that way, so the shared helper would have read its `message`
  parameter as the implicit one and reported a mismatch that is not there.
- **Lesson:** re-reading a deferred issue's trigger is worth the one command
  it costs. #36 defers an SBOM until the first release and states the
  repository has cut none. It has: `v0.1.0` published 2026-08-18, annotated,
  a day *before* the issue was filed saying otherwise. The trigger had already
  fired, so the issue was not deferred-pending-an-event but open work reading
  as deferred. Corrected on the issue rather than acted on, since the three
  questions in its body bind the release workflow and are the owner's.
- **Upstream:** none. Both defects settled this session are instances of rules
  the templates already carry, and the Liskov gap that produced them was filed
  upstream last session as braboj/solid-ai-templates#1033.
- **Pending:** four issues, none of them code. #4 is unchanged and still
  blocked, re-checked rather than assumed: upstream has cut no tag past
  `v2.44.0` and the submodule sits three commits beyond it. #22 is blocked on
  the repository being private, re-checked and still true. #15 and #36 are
  both "what to decide" bodies whose questions are the owner's — and #36's
  trigger has now fired, so it is waiting on a decision rather than on an
  event. Also still waiting: PLAYBOOK 5 says the first PyPI publish is
  "Tracked as #2", but #2 is closed and no open issue tracks the publish.
  Worth carrying forward: `v0.1.0` carries no release assets at all, so
  whatever is decided for the SBOM covers the wheel and sdist too.

## 2026-08-21 — Lock the toolchain and ship release assets (later)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Locked the development toolchain with uv** — five packages floated
    completely, so CI and a contributor's machine resolved them
    independently and a green run could not say afterwards what it ran
    against. The template names `requirements-dev.lock`, which implies
    `pip freeze` output, and that is the one thing that cannot work here:
    frozen output has its markers already resolved, so it is true for one
    interpreter and platform and misrepresents the others, and this project
    spans three. `uv lock` resolves across the whole `requires-python` range
    instead. ADR-010.
  - **Made the lock load-bearing rather than decorative** — every job installs
    with `uv sync --locked`, which refuses a lock that no longer matches
    `pyproject.toml`, and every gate step runs under `uv run --no-sync` so the
    install is the only place a dependency can be resolved. Dependabot is
    enrolled on pip, because a lock nothing refreshes pins an ageing toolchain
    silently.
  - **Gave tagged releases their assets** — the repository had no release
    workflow at all; CI built a wheel on every change and discarded it with the
    run. `release.yml` fires on a `v*` tag, refuses one that does not name the
    version the package reports, builds, creates the release record when the
    tag has none, attaches the wheel and sdist, then generates the SBOM and
    attaches that. ADR-011.
  - **Generated the SBOM from a consumer environment** — every generator's
    convenient mode reads the environment at hand, which in CI is the build
    environment. Measured, that lists 81 components including pytest, ruff and
    mypy; an environment holding only the built wheel lists one. Both documents
    are schema-valid, so the step asserts the component set rather than
    trusting the exit code.
  - **Repaired the dead tracker in PLAYBOOK 5** — the section ended "Tracked
    as #2", and #2 is closed and was about repository metadata. The pointer is
    gone and the substance kept. Filing a replacement is still the owner's.
- **PRs merged:** #57 and #58.
- **Issues closed/created:** #15 and #36 closed. None created.
- **Lesson:** re-reading a deferred issue's trigger cost one command and
  changed what the session did. #36 said the repository had cut no release, so
  the SBOM was deferred until one existed. `v0.1.0` had published a day before
  the issue was filed. The rule was being violated rather than not yet
  applicable — and the same check found the larger gap the issue never
  mentions, that the release carries no wheel or sdist either.
- **Lesson:** the template turned out far more prescriptive than the issue
  quoting it, and reading the source changed the design. `devsecops.md` marks
  the SBOM job `continue-on-error` and forbids it creating the release record.
  Neither fits a workflow that *is* the release pipeline rather than a side-car
  scan, so both are documented divergences — but the rule's actual intent,
  that a scan must never leave a release empty, is carried by ordering wheel and
  sdist upload before the SBOM is generated. Reading the rule got the intent;
  reading the issue would have got two rules to obey or ignore.
- **Lesson:** a number read off a manifest is not a measurement. ADR-011 first
  said the build-environment SBOM carried 93 components, taken from the lock's
  package count. Running the generator reported 81 — a lock resolves across
  platforms and Python versions and records entries no single environment
  installs. Corrected before the ADR shipped, and corrected on the upstream
  issue that had already quoted it.
- **Lesson:** an SBOM generator pointed at the wrong environment exits zero.
  The document is schema-valid, the step is green, and the answer names the
  toolchain as part of the product. That is the `quality-gates-pair-check`
  shape exactly: the constraint is about content, so the check has to be about
  content, and asserting the component set is the whole of it.
- **Upstream:** two filings. braboj/solid-ai-templates#1034 against
  `templates/stack/python-lib.md` — the lock file rule is one line naming
  `requirements-dev.lock` and survives neither a CI matrix nor a lock nothing
  installs from. braboj/solid-ai-templates#1035 against
  `templates/base/security/devsecops.md` — the SBOM rule says where to attach
  the document and never what it must describe, and the convenient command
  produces the wrong one.
- **Pending:** two issues, both genuinely blocked rather than waiting on work.
  #4 is unchanged, re-checked rather than assumed: upstream has cut no tag past
  `v2.44.0` and the submodule sits three commits beyond it. #22 is blocked on
  the repository being private, re-checked and still true. Carrying forward:
  `release.yml` has never executed — it does not run on pull requests, so CI
  passing on #58 says nothing about it. The chain was run by hand end to end,
  including the negative case where a tag names the wrong version, but the
  first real proof is the next tag. Also carried: whether the first PyPI
  publish gets a tracking issue, which PLAYBOOK 5 no longer pretends is
  tracked.

## 2026-08-21 — What the wrap-up audit found (wrap)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Repaired an edit that was made and then lost** — the uv migration
    updated README, ONBOARDING and PLAYBOOK but left `CLAUDE.md` telling a
    contributor to run `pip install -e ".[dev]"`. The edit had been written
    and reverted in the same script: it called `write_text` twice from one
    string read before either write, so the second write clobbered the first,
    and both asserts passed because both targets existed in the original.
  - **Put this session's changes in the CHANGELOG** — the `[Unreleased]`
    section was last touched by the previous session, so the release assets,
    the two breaking signature changes, the client's new error type and the
    move to a locked toolchain were all absent from the one document a consumer
    reads for them.
  - **Made the ONBOARDING verify step name its environment** — section 3
    checked the setup with a bare `python -m pytest`, which after the uv move
    resolves against whatever interpreter is active. Where a global pytest
    exists it runs, passes, and verifies an environment the contributor is not
    about to develop in.
  - **Named the workflow the fan-in gate covers** — PLAYBOOK 3.9 said `gate`
    needs every other job "in the workflow", which was unambiguous while there
    was one. It now names `ci.yml` and says `release.yml` gates nothing.
- **PRs merged:** #60 and #62.
- **Issues closed/created:** #61 created — the server tests bind ports from a
  fixed base, and 20200 is unbindable on this machine.
- **Lesson:** four documentation defects, none of which any gate could catch.
  Each file was internally consistent; the contradictions only existed between
  files, and nothing compares an install command in `CLAUDE.md` against the one
  in `README.md`. The audit is the check, which is an argument for executing it
  rather than summarising it.
- **Lesson:** `write_text` twice from one pre-read string silently discards the
  first edit, and an assertion on the target string does not catch it — both
  targets exist in the original content, so both asserts pass. Read once, apply
  every replacement, write once.
- **Lesson:** `git add -A` swept an editor setting into a documentation commit.
  An `88`-column ruler had appeared in `.vscode/settings.json` from outside the
  session, and the commit carried it. Reverted on a second commit rather than
  amended, because the branch was pushed and force-push is forbidden here, and
  the squash collapses the pair. The scope guard calls this the silent kind of
  creep, and it is: nothing about the diff looked wrong.
- **Lesson:** asserting a mechanism from an error code is not diagnosing it.
  #61 was filed saying two tests fail because `TIME_WAIT` holds their fixed
  port and that waiting two minutes clears it. Neither was true — a bare
  `socket.bind` on 20200 fails while 20201 and 20202 succeed, `netstat` shows
  nothing bound, and it does not clear. The finding survived; the explanation
  had to be corrected on the issue after it was already public.
- **Upstream:** two filings, both from conventions this session produced rather
  than from its ADRs. braboj/solid-ai-templates#1036 against
  `templates/base/workflow/issues.md` — a deferred issue's trigger is a claim
  about the world and needs re-verifying, not just stating; #36's had fired the
  day before the issue was written. braboj/solid-ai-templates#1037 against
  `templates/base/workflow/quality-gates.md` — narrowing what a check compares
  is not the same as ratcheting which cases fail, and only the second keeps the
  gate.
- **Pending:** three issues, none of them blocked on a decision. #4 and #22 are
  unchanged and genuinely blocked, both re-verified this session. #61 is new
  and open. Carried forward unchanged from the previous entry: `release.yml`
  has still never executed, and whether the first PyPI publish gets a tracking
  issue is still the owner's call. New and worth carrying: the README quick
  start tells a reader to build from source, which stays correct only until
  a tag ships assets — the next release is when to offer the wheel instead.

## 2026-08-21 — Give the server port 0, pin back to a tag (evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Gave `OmbServerSim` a working port 0** — `run()` bound whatever port it
    was handed and never read the result back, so a server asked for port 0
    bound a real port and went on reporting 0. The listener was up and
    unreachable, and that is what had forced every server test module to name
    a fixed port. It now captures `getsockname()[1]` after `listen()` and
    before setting the started event, so every caller the event releases sees
    the real port.
  - **Moved all four server test modules to port 0** — three allocated with
    `type(self).port_counter`, which is the pattern the audit comment in
    `test_server_connections.py` already recorded as broken, because the
    subclass attribute write makes each subclass restart from the inherited
    value. The comment had been read as advice about one module; it described
    a defect live in three. The two startup tests now take a port from the
    operating system and hold it rather than assuming a named one is free.
  - **Pinned the templates submodule back to `v2.44.0`** — it sat three
    commits past the newest tag, so the repository enforced rules upstream had
    not cut, and `CLAUDE.md` listed a file that existed at no released
    revision. Pinning back cost nothing: the commits refactored the examples
    rules out of `readme.md` and `python-lib.md` into a new `examples.md`
    rather than writing new ones, and this project has no `examples/`
    directory, which is the condition `base-examples` applies under.
  - **Corrected two issues that were wrong on the record** — #22 said the CI
    badge cannot render while the repository is private, and #61 said the
    suite fails on consecutive runs. Neither held.
- **PRs merged:** #64 and #65.
- **Issues closed/created:** #61 and #4 closed. #66 created — nothing
  publishes the package and `release.yml` has never executed.
- **Lesson:** the owner disproved a filed finding by looking at the page. #22
  reasoned from a `curl` 404 to "broken for every viewer, the owner included",
  but GitHub does not serve its own Actions badge through camo: the rendered
  README carries a direct `src` while the two shields.io badges beside it are
  proxied, so the browser sends a session cookie and any viewer who can read
  the README can read the badge. The probe measured the anonymous case and the
  conclusion was written about all cases. The endpoint authenticates by cookie
  rather than by token, so even an authenticated API client reproduces the
  404, which is what made the wrong reading so easy to confirm twice.
- **Lesson:** #61 has now been misdiagnosed three times — `TIME_WAIT`, then
  "20200 is unbindable on this machine", then the symptom itself, which does
  not reproduce across six runs. What was actually broken was one line in
  `src/`, and no amount of staring at the counter would have found it. The
  finding survived all three wrong explanations, which is the argument for
  filing the observation and probing the mechanism separately rather than
  letting a plausible cause travel with the report.
- **Lesson:** a planned fix is a hypothesis about a file. The README quick
  start was carried into this session as work to do, on a journal note saying
  it should offer the wheel once a tag ships assets. Opening it showed the
  trigger has not fired — `v0.1.0` has zero assets — and that the documented
  output is byte-correct against a real run. Changing it would have replaced a
  working instruction with a broken one. It became an acceptance criterion on
  #66 instead of an edit.
- **Lesson:** three sessions of journal breadcrumbs are a ticket nobody filed.
  "`release.yml` has still never executed" and "whether the first PyPI publish
  gets a tracking issue is the owner's call" had been carried forward twice
  without an owner, while #22's unblocking condition pointed at nothing. One
  issue, #66, now holds all three.
- **Upstream:** two filings, neither from the conventions this session leaned
  on. `testing-in-process-server` and pinning a submodule to a released tag
  both already exist upstream and were the authority for the changes rather
  than candidates produced by them; the filings come from how the session went
  wrong instead. braboj/solid-ai-templates#1038 against
  `templates/base/workflow/ai-workflow.md` — a comment recording a rejected
  mechanism is a defect report that was only half-filed, so grep the mechanism
  rather than reading the comment as advice about its own module.
  braboj/solid-ai-templates#1039 against `templates/base/core/review.md` — a
  probe running as the wrong principal answers a different question, and
  checking it with the wrong credential type reproduces the wrong answer,
  which is what let #22 survive a re-verification.
- **Pending:** #22 and #66 open, both now correctly scoped and neither blocked
  on a decision this session could take. `ADR-007`'s Related section still
  describes #22 as a consequence of repository visibility; left unedited by
  the owner's call, because a merged ADR is immutable, and #22's correction
  note records the divergence from the tracker side.

## 2026-08-21 — Go public and prove the release path (night)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Made the repository public** — pre-flighted rather than flipped:
    gitleaks over every tracked file, and a sweep of all 47 commits for a
    `.env`, key, certificate or credential path ever added. Both clean. The
    flip settled #22 on its own. The anonymous fetch that 404'd in that
    issue's correction note now returns `200 image/svg+xml`, which is the
    case that mattered, because `pyproject.toml` makes the README the long
    description an anonymous viewer reads.
  - **Cut `v0.2.0` and watched `release.yml` execute for the first time** —
    the workflow landed after `v0.1.0` and no tag had fired it since, so this
    tag was its first run. Every step was rehearsed locally first, because a
    tag is not something you take back: the package reports the version,
    `build` produces both artifacts, `twine check` passes on each, and an
    environment holding only the wheel yields an SBOM listing exactly
    `pyomb`. The run then went green in 19 seconds, and the release carries
    the wheel, the sdist and a CycloneDX 1.6 SBOM with no serial number.
  - **Pointed the quick start at the wheel** — clone-and-build was correct
    only while no release carried assets. The new command was run in a clean
    virtual environment, then the example that follows it, which printed the
    same twelve bytes the README documents.
  - **Guarded the version the README names** — it now lives in
    `__init__.py` and in the wheel URL, and every checker the project runs
    reads that URL as prose. `tests/test_readme_install_command.py` pins the
    second to the first, capturing the tag path and the filename separately
    so a half-finished edit fails rather than passing on the half that was
    done. Run both ways.
  - **Recorded the release steps that were done by hand** — PLAYBOOK 5
    gains the CHANGELOG cut and the README bump, and its "no open issue
    tracks that work" line now names #70.
- **PRs merged:** #72 and #73.
- **Issues closed/created:** #22 and #66 closed. #70 and #71 created.
- **Lesson:** a revisit trigger has no watcher. ADR-007 declined platform
  SAST and named its trigger exactly — "the repository going public, which
  makes code scanning free" — and the flip fired it silently. The record
  still read `Accepted` and still described a scanner the host refuses to
  run. It was caught only by re-probing the endpoint the ADR cited and
  getting `not-configured` where it had recorded a 403. A decision record is
  a file nobody re-reads without a reason, so the obligation belongs to
  whoever fires the trigger, not to the record.
- **Lesson:** a visibility flip is not one change. It resolved an open bug
  without touching the code that bug named, fired a decision record's revisit
  trigger, and moved a paid feature into reach. The blast radius was in the
  decision log and the tracker, not in the tree — which is exactly where a
  diff review does not look.
- **Lesson:** rehearsing an unproven workflow is cheap and teaches something.
  The SBOM step asserts its component list is exactly `pyomb`, which holds
  only because `uv venv` creates an environment without pip. Built the
  ordinary way, the generator lists pip too and the assertion fails. That was
  worth learning in a scratch directory rather than in a red run against a
  tag already pushed.
- **Lesson:** the tag went up before the README could know about it. The
  `v0.2.0` sdist carries the old clone-and-build quick start, because the
  bump cannot name a wheel that does not exist yet. PLAYBOOK 5 now puts the
  bump on the release branch, so the next tagged sdist names its own release
  and the URL 404s only for the minutes between merge and tag.
- **Upstream:** two filings, both from how this session went rather than from
  a convention it produced. braboj/solid-ai-templates#1040 against
  `templates/base/core/git.md` — the pre-release checks all read the
  repository's state and none asks whether the pipeline the tag fires has
  ever executed, and a tag gets no cheap first failure.
  braboj/solid-ai-templates#1041 against `templates/base/core/quality.md` —
  the YAGNI rule asks for a concrete revisit trigger but never says who
  watches it, and a trigger with no owner is a reminder set to fire into an
  empty room.
- **Pending:** three issues, all open by the owner's call this session rather
  than blocked on discovery. #70 defers the package-index question to a
  separate discussion and carries the trigger. #71 holds the ADR-007 revisit,
  filed rather than built to keep the session on one theme; the superseding
  ADR is its deliverable, and until it lands `ADR-007` reads as `Accepted`
  while describing a constraint that has lifted. #68 is unchanged and
  re-checked rather than assumed: upstream has still cut no tag past
  `v2.44.0`, and `templates/base/core/examples.md` is not in it. No ADR was
  written this session — the distribution call schedules PyPI rather than
  moving off it, which `base-issues-defer` puts in an unmilestoned issue, and
  the visibility flip's decision consequence is #71's to record.

## 2026-08-21 — Adopt CodeQL, and correct its baseline an hour later (late)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Adopted the platform SAST that ADR-007 declined** — the trigger it
    named had fired when the repository went public, so the objection the ADR
    rejected the alternative on was gone. `.github/workflows/codeql.yml`
    analyses `python` and `actions`, in its own workflow because it is the one
    thing here needing `security-events: write`.
  - **Gave the isolated workflow its own fan-in** — `platform/github.md`
    wants the write scope isolated and also wants one required context, and
    the two collide: a fan-in can only need jobs in its own workflow. A
    `codeql` job over the language matrix satisfies both, at one required
    context per workflow instead of one per language.
  - **Superseded ADR-007 and carried its bandit rules forward** — a reader
    who stops at the live record has to find them, so ADR-012 restates the
    three rather than leaving them in a superseded file. All 21 citations of
    ADR-007 were audited; the two that instruct rather than narrate moved, and
    the rest stayed because they are history.
  - **Corrected the baseline in ADR-013, one hour after ADR-012 merged** —
    the suite comparison in ADR-012 was measured on pull-request refs, where
    CodeQL reports against the diff. Both rows read zero because the branch
    added nothing, not because the tree was clean.
  - **Filed what the real baseline found** — #76, the TLS client setting no
    minimum protocol version, and #77, two bind-to-all-interfaces alerts.
    Both reproduced against the source before filing rather than forwarded
    from the scanner.
  - **Restored the line continuations in the SBOM command** — one
    162-character line with runs of thirteen spaces where the backslashes had
    been. Behaviour-neutral, and proved so by extracting the command from both
    revisions and diffing the argv.
- **PRs merged:** #75, #78 and #79.
- **Issues closed/created:** #71 closed. #76, #77 and #80 created.
- **Lesson:** a scanner's pull-request run is not a baseline. Zero on
  `refs/pull/N/merge` means the change introduces nothing; the same commit on
  `refs/heads/main` reported three. Nothing about the wrong number looked
  wrong — two suites, two plausible rule counts, a consistent zero, and a
  conclusion that followed from it. The project's verification rules prompt for
  a measurement in the wrong unit and for a silently partial extraction, and a
  diff-scoped run resembles neither.
- **Lesson:** CodeQL paid for itself in under an hour on a tree bandit calls
  clean at full strictness. Bandit has no check for a missing TLS floor and
  none for a bind to all interfaces expressed as `""`, so its zero was
  evidence about its rule set rather than about the code. ADR-007 read that
  zero as the tree being clean, which is why both scanners are worth the
  second workflow.
- **Lesson:** the argv check caught an edit that a diff review would have
  passed. The first attempt at the continuation fix wrote a literal
  backslash-n into the workflow. It renders identically to a real continuation
  and would have handed the SBOM generator three arguments named `n`. Reading
  it back with `cat -A` and comparing the tokenised command is what found it,
  on the one workflow that cannot be dry-run on a pull request.
- **Lesson:** the first measurement of the ASCII footprint said 96,965
  non-ASCII characters in one source file. `grep -o '[^\x00-\x7f]'` does not
  interpret that range and matched almost everything. The real number is 338
  across 23 files, and the implausible one should have been the tell before the
  method was.
- **Upstream:** two filings. braboj/solid-ai-templates#1042 against
  `templates/platform/github.md` — isolating an elevated-scope scan into
  its own workflow costs the single-required-context property unless that
  workflow carries its own fan-in, and the template asks for both rules without
  noting they collide. braboj/solid-ai-templates#1043 against
  `templates/base/core/review.md` — the verification section covers a
  measurement in the wrong unit and a silently partial extraction, and a
  measurement at the wrong scope is a third axis that looks like neither.
- **Pending:** five issues, none blocked. #76 is the only one with a severity
  worth acting on soon: the TLS floor is currently correct by accident of
  OpenSSL 3.0.15 rather than by anything the library states, so it is a
  hardening fix rather than a live exposure, and it needs a test that fails
  against current code. #77 and #80 are both decisions rather than work. #70
  and #68 are unchanged from earlier today. The `codeql` context is not in
  branch protection, so CodeQL reports and gates nothing until the owner adds
  it; ADR-012 carries the command and why it is theirs to run.

## 2026-08-21 — What the wrap-up audit found (wrap)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Made `codeql` a required context** — the owner ran the branch
    protection change, so two checks now gate a merge, one per workflow.
    `strict`, `enforce_admins`, the zero-approval review requirement and both
    force-push and deletion blocks were read back and are unchanged.
  - **Corrected PLAYBOOK 3.9** — it still said one check gates a merge and
    that `codeql` was in no required list, both written hours before either
    became false.
  - **Corrected the CI-reading rule in CLAUDE.md** — it told the agent to
    check `gh run list --limit 1`, which was right while the repository had
    one workflow. With two it reports whichever finished last and hides the
    other, so an agent could read a green CodeQL run and call a red build
    good. It now selects by commit.
  - **Fixed a collapsed line continuation in PLAYBOOK 3.8** — the same
    defect repaired in `release.yml` two pull requests earlier, reintroduced
    by the same editing mistake in the same session.
  - **Updated the README structure map** — `.github/` described CI and
    release workflows and there are now three.
- **PRs merged:** #82.
- **Issues closed/created:** none. Five remain open, all deliberately.
- **Lesson:** adding a workflow invalidated a rule in three documents, none of
  which the change touched. PLAYBOOK 3.9 described the gate arrangement,
  CLAUDE.md carried a check command that assumed one workflow, and the README
  mapped the directory. A reviewer of the workflow diff had no reason to open
  any of them, and no gate reads prose. The sweep only happened because the
  audit runs after the work rather than inside it.
- **Lesson:** a positional selector hides an assumption about cardinality.
  `--limit 1` was a correct check for as long as the count was one, and it did
  not fail when the count changed — it kept exiting zero and started
  answering about an arbitrary member. Selecting by commit says what is
  actually meant and survives the next workflow.
- **Lesson:** the same editing mistake landed twice in one session. A
  backslash-newline written through a nested heredoc came out as a literal
  `\n` in `release.yml`, was caught by an argv comparison, and then
  came out as collapsed spaces in PLAYBOOK 3.8 an hour later. Reading the
  bytes back with `cat -A` is what caught both; reading the rendered diff
  caught neither, because both render as what they were supposed to be.
- **Upstream:** one filing. braboj/solid-ai-templates#1044 against
  `templates/base/workflow/quality-gates.md` — `quality-gates-pair-check`
  requires a rule to name its runnable check and says nothing about how that
  check selects its subject, so the obvious positional selector goes silently
  wrong the moment a second instance exists. Distinct from #1043, filed
  earlier today: there the tool measures the wrong population, here it
  measures correctly and the command asks about the wrong member.
- **Pending:** five issues, none blocked on anything this session could
  resolve. #76 is the only one carrying real weight — the TLS client's
  protocol floor is currently correct by accident of OpenSSL 3.0.15 rather
  than by anything the library states, so it is hardening rather than live
  exposure, and it needs a test that fails against the unfixed code. #70 and
  #77 and #80 are decisions rather than work, and #68 waits on an upstream tag
  that does not exist. Verified against the tracker rather than recalled: all
  five are open, correctly labelled, and none sits in a milestone the project
  has moved past, since the project uses none.

## 2026-08-21 — Declare the TLS floor, settle the ASCII rule (last)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Declared the minimum TLS version on both contexts** — `OmbClientSim` and
    `OmbServerSim` built their `SSLContext` without `minimum_version`, so the
    floor was a property of whichever OpenSSL a consumer links rather than of
    this library. The value comes from the specification the repository
    already ships rather than from taste: MB-TCP-Security v21 R-32 requires
    TLS 1.2 or better and R-34 forbids negotiating down to 1.1, 1.0 or SSL
    3.0. Read out of the PDF with `pdftotext` rather than recalled.
  - **Widened that fix to the server** — CodeQL reported the client alone, and
    `omb_server.py` carried the identical `options |= ssl_options` with no
    floor. `TestSecureDefaults` asserts the two symmetrically, so a
    client-only fix would have left the same latent defect in the sibling and
    a visibly lopsided test class. Agreed with the owner before the change
    rather than absorbed into it.
  - **Triaged both bind alerts without moving the default** — a server
    simulator exists to accept connections from a device under test, and that
    device is normally on another host, so a loopback-only default would
    refuse the traffic the simulator is for. Both alerts are dismissed with a
    reason, and both reasons are also at the bind site, because a dismissal
    that lives only in the Security tab is lost with the tab.
  - **Settled the ASCII rule as ADR-014** — prose keeps the em dash, code and
    configuration stay ASCII, and Markdown may use nothing else either. The
    last clause is the load-bearing one: the four defects #80 found were
    hiding behind 353 deliberate em dashes, so a blanket prose exemption would
    have made them permanent.
  - **Gave that rule the check it never had** — `tests/test_source_is_ascii.py`
    reads the tree as git tracks it and names each offender as
    `path:line:column U+XXXX`. `RUF002` came off the `errors.py` entry in the
    ruff freeze once its two characters were gone, and ruff reported nothing
    new in its place.
  - **Corrected PLAYBOOK 3.12's line-ending check** — the NUL did more
    than hide itself. Git classifies a file containing one as binary, so
    `text=auto` skipped normalising this journal and its 1127 CRLF endings
    went into the index unconverted, in a repository whose rule is LF there.
    The check reported clean throughout, because a binary-classified file
    reports `i/-text` and never matches the `i/crlf` the command greps for.
  - **Repaired two control bytes in this journal** — it carried a literal NUL
    and a literal DEL inside a code span, on the line describing the very
    grep that mishandles that range.
- **PRs merged:** none. #83, #84 and #85 are open, green on both workflows and
  mergeable; merging was unavailable to the agent this session, so landing
  them is the owner's.
- **Issues closed/created:** none closed, none created. #76, #77 and #80 each
  carry a closing keyword in exactly one pull request and close on merge —
  checked with the PLAYBOOK 1.3 query rather than by reading, which also
  confirmed no body carries a stray or negated keyword. #68 was re-checked
  against upstream and its trigger still has not fired: `v2.44.0` is the
  newest tag and does not contain `examples.md`. #70 was excluded by the owner.
- **Lesson:** a test asserting the hardened value would have passed against
  the unfixed code. This OpenSSL already defaults to TLS 1.2, so the floor
  reads 771 either way, and the defect was never the value — it was that the
  value came from the platform. The assertion had to be about provenance, so
  the test injects a permissive platform and asserts the library overrides it.
  When the thing being fixed is where a value comes from rather than what it
  is, an assertion on the value is not a test of the fix.
- **Lesson:** the double could not be installed the obvious way. Replacing
  `ssl.SSLContext` on the module recurses forever, because the standard
  library's own `minimum_version` setter resolves that same name on the
  module and lands back in the double. Redirecting only the name the module
  under test reads leaves the real class where the standard library expects
  it. The first attempt failed with a `RecursionError` that looked like a
  passing test, in that the run was red either way — worth reading why a test
  fails and not only that it does.
- **Lesson:** a gate never seen to fail is not evidence of anything. Every
  character class was injected one at a time to watch the ASCII check reject
  it, and that is the only reason two holes surfaced. The check tested
  `ord(c) > 127`, which treats ASCII as a ceiling when it is a range, so a NUL
  and a DEL sat in this file undetected — a control character renders as
  nothing, which hides it better than any homoglyph, and the only outward sign
  was git and grep quietly reclassifying the file as binary. Separately,
  `splitlines()` breaks on the vertical tab, the form feed and the Unicode
  line separators, so each was consumed as a line boundary and never appeared
  within a line for the check to see. Splitting on the newline alone fixed it.
- **Lesson:** a defect can disable the check that would have caught it. One
  NUL byte made git treat this journal as binary, which suppressed the LF
  normalisation and simultaneously made the line-ending check blind to the
  result, since it greps for `i/crlf` and a binary file reports `i/-text`.
  The check passed for as long as the file was broken and would have started
  failing the moment it was fixed, had the endings not been repaired in the
  same change. Same shape as the positional selector recorded earlier today:
  the command ran correctly and answered about a population that excluded
  its subject.
- **Lesson:** a comment about behaviour that differs by platform is a claim to
  probe, not to reason out. The bind-site comment nearly shipped saying a
  loopback-only blocker would leave the server free to bind, stated generally.
  Linux refuses that later wildcard bind and Windows allows it, so with CI on
  Linux and development on Windows the test would pass for the wrong reason on
  one and the right reason on the other.
- **Lesson:** an issue's own notes age like anything else. #77 gave the
  dismissal reasons as `used_in_tests` and `wont_fix`; the API rejects both
  and wants the spaced `used in tests` and `won't fix`, and caps the comment
  at 280 characters. Two rejected calls, not a wrong dismissal, but the
  ticket was written from memory of the API rather than against it.
- **Upstream:** three filings, all against templates whose rules this
  session found unenforced or unenforceable.
  braboj/solid-ai-templates#1045 against `templates/base/core/quality.md`:
  the ASCII rule names no check, which `quality-gates-pair-check` requires
  of any mechanically checkable constraint, and 170 of the 186 template
  documents carry 17,350 non-ASCII characters themselves, including 751
  box-drawing characters in the very section that forbids them in ADR
  diagrams. #1046 against `templates/base/workflow/quality-gates.md`: a
  paired check must not filter on a property the violation it detects can
  change, which is the line-ending case above, and is a different axis from
  #1044, where the member is selected wrongly from a fixed population
  rather than the population itself being redefined. #1047 against
  `templates/base/core/testing.md`: when a fix's subject is where a value
  comes from rather than what it is, asserting the value does not test it,
  because the environment may already supply the right answer.
- **Pending:** three pull requests to land, and the three issues that close
  with them. Nothing is blocked on a decision. #68 remains genuinely blocked
  on an upstream tag, re-verified this session rather than assumed, and #70 is
  the owner's call by their own instruction. ADR-014 records a deliberate
  divergence from the pinned templates, so the next submodule bump that moves
  the ASCII rule must be read against that record rather than as a gap to
  close.

## 2026-08-22 — Land the stack, widen the de-stack recipe (wrap)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Landed the four open pull requests** — #83, #84 and #85 onto `main` in
    that order, then #86. The previous session left all four green and
    mergeable and recorded landing them as the owner's, merging having been
    unavailable to the agent then.
  - **Read the protection settings rather than assuming the batch cascade** —
    the git template describes every remaining pull request going stale after
    the first merge, at one update and one CI cycle each. That holds only
    where protection requires branches be up to date, and `main` here reads
    `strict: false`, so nothing needed updating between merges. This session
    had predicted the cascade out loud before checking, which is the wrong
    order.
  - **Let the platform retarget the dependent pull request** — #85 merged with
    no delete-branch flag, and the automatic head-branch deletion retargeted
    #86 onto `main` and left it open, as PLAYBOOK 1.5 says it does.
  - **De-stacked #86 by merging `main` in** — it conflicted the moment it
    retargeted. Its merge base is the `main` tip from before the stack, where
    the journal still carries the NUL byte #85 removed, so both sides had
    rewritten the whole file over a base git cannot three-way merge. Resolved
    to the branch's own version, taken after measuring that version as
    `main`'s journal plus 119 added lines with nothing removed and nothing
    changed.
  - **Widened PLAYBOOK 1.5 to the squash case** — its closing paragraph gave
    the de-stack verification for a rebase-merged lower pull request, and this
    repository squash-merges, which is the case that actually ran. The
    addition states why the merge base stays behind under a squash and names
    the conflict-stage comparison as the check.
  - **Finished retiring the `--limit 1` CI selector** — CLAUDE.md moved off
    it a day ago, on the finding that with two workflows it reports whichever
    finished last and hides the other. The PLAYBOOK kept instructing it in
    two places, one of them the pull-request recipe a reader is most likely
    to copy from, so the retired selector outlived its retirement on the
    surface where it does the most damage. 3.9 now also says why the full
    hash matters.
- **PRs merged:** #83, #84, #85 and #86.
- **Issues closed/created:** #76, #77 and #80 closed on merge, each read back
  from the tracker rather than assumed. None created here. #70 and #68 are
  untouched, and #68's trigger was re-checked rather than recalled: `v2.44.0`
  is still the newest tag and still carries no `examples.md`.
- **Lesson:** a conflict resolution is a claim about what it discards. Taking
  one side of a whole-file conflict is easy to justify by narrative — the
  branch is newer, it already contains the other side — and a narrative is not
  evidence. Comparing the two conflict stages makes it a measurement: 119
  lines added, none removed, none changed, so the side taken is provably a
  superset. The squash landing exactly 119 insertions confirmed it afterwards.
- **Lesson:** an abbreviated commit hash makes `gh run list --commit` answer
  about nothing. It matches no run, prints an empty list and exits zero, so a
  poll waiting for the run to appear spent its whole budget and reported
  silence, which reads exactly like a workflow that never fired. CLAUDE.md
  already prescribes the full form through `git rev-parse HEAD`, written after
  the neighbouring `--limit 1` defect a day earlier; this session deviated
  from a rule the project had already paid to learn.
- **Lesson:** the working directory persists between commands. A `cd` into the
  submodule made a later read of PLAYBOOK 1.5 return nothing, and the obvious
  reading was that the section did not exist and the wrap should write it. It
  exists, and it is thorough enough that writing it again would have been the
  session's worst output. One `pwd` separates a documentation gap from a false
  negative, and the rule saying so was already read this session.
- **Lesson:** `--no-verify` went onto the merge-conflict commit out of habit,
  which is the exact bypass the three-layer gate model names. The hooks and
  the full suite ran immediately afterwards and passed, so the commit ended
  verified in the wrong order rather than unverified — but ordering is the
  whole point of a pre-commit gate, and a habit is not a reason.
- **Lesson:** retiring a flag from the rule that names it does not retire it
  from the documents that instruct it. The `--limit 1` correction landed in
  CLAUDE.md a day ago and the PLAYBOOK kept two copies. The sweep is one grep
  at the moment of retirement and it was not run; what surfaced it here was
  opening the PLAYBOOK for an unrelated reason and reading the command that
  happened to sit there.
- **Upstream:** two filings, both against rules this session found silent
  rather than wrong. braboj/solid-ai-templates#1048 against
  `templates/base/core/git.md`: de-stacking gives two routes and no way to
  verify the resolution, and under squash merge the merge base predates the
  base's own content, so a whole-file conflict can arise over content neither
  change touched. #1049 against `templates/platform/github.md`: the template
  says nothing about selecting a run by commit, and the abbreviated hash
  returns an empty list and exits zero. Related to #1044 and distinct from it
  — there a selector picked the wrong member of a real population, here the
  key matches nothing and the empty result reads as a clean answer.
- **Pending:** nothing this session could resolve. #70 is the owner's decision
  by their own instruction, and #68 waits on an upstream tag that does not yet
  exist. Both were verified open and correctly labelled against the tracker.

## 2026-08-24 — Ship v0.2.1, empty the backlog (wrap)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Released v0.2.1** — #90 squash-merged, then an annotated tag pushed on
    the resulting commit. The release is entirely tag-driven: the workflow
    asserted the tag names the version the package reports, built, created the
    release record itself and attached the wheel, the sdist and the CycloneDX
    SBOM. `gh release create` was deliberately not run, PLAYBOOK 5 saying it
    only risks racing the workflow for the same record.
  - **Landed #89** — the startup-block guard, which closed #88 on merge. Its
    branch was updated onto the post-release `main` before merging, so its
    checks ran against the tree it would actually join.
  - **Closed #70 and #68 as deferred** — both by owner instruction, each with a
    comment recording that the closure decides nothing. ADR-016 records the
    divergence and bounds it, since `base-issues-defer` puts deferred work in
    an open, unmilestoned issue and both tickets were written to exactly that
    shape.
  - **Swept the citations the closures broke** — PLAYBOOK 5 claimed "#70
    carries whether it ever is" and "#70 tracks that work", and 1.6 said
    deferral is the absence of a milestone, which ADR-016 contradicts.
    ADR-015 describes #68 as open four times and was left alone, being merged
    and immutable; ADR-016's Related section takes the reader who follows it.
  - **Corrected the repository visibility in CLAUDE.md** — the identity block
    had said private since it was written, and `gh repo view` reports `PUBLIC`.
    That is the fact an agent reasons from when judging what is safe to commit,
    in the one file loaded before anything else.
- **PRs merged:** #90, #89, #91, #92, #93 and #94.
- **Issues closed/created:** #88 closed on merge, read back from the tracker
  rather than assumed. #70 and #68 closed as `NOT_PLANNED` by instruction. None
  created here. The backlog is now empty, which it has not been before.
- **Lesson:** the batch-merge cascade did not fire, and this session predicted
  it would before checking — the same mistake the previous entry records, with
  the same cause noted there, that protection reads `strict: false`. Reading a
  lesson is not the same as it binding. The check is one field and it belongs
  before the claim.
- **Lesson:** a gate's scope is narrower than the rule it enforces. The claim
  that a branch-tip submodule pin would now fail the #89 guard was wrong: that
  guard compares the block against the chain the pin resolves and never asks
  whether the pin is a tag, so a bump plus the matching block line passes it.
  What forbids the bump is the rule in CLAUDE.md and nothing else. Attributing
  a rule to a test that does not carry it makes the rule look cheaper to
  satisfy than it is, and it took reading the test to notice.
- **Lesson:** closing an issue silently transfers whatever it was holding.
  #68 was the only thing tracking ADR-008's stale counts, and it held the
  argument that a supersession ADR would be churn *because* something tracked
  them; that argument survived the close and its tracker did not. The
  second-order loss is invisible from the close button, which is why ADR-016
  requires the closing comment to name it.
- **Lesson:** the wrap-up checklist is not bookkeeping. Item 6 turned up a
  false statement about repository exposure that had been sitting in CLAUDE.md
  since it was written, and item 9 turned up an unstated release ordering that
  would have shipped an incomplete changelog. Neither was in the session's
  scope and neither would have been found by working the scope.
- **Upstream:** two filings, both against rules that are silent rather than
  wrong. braboj/solid-ai-templates#1052 against
  `templates/base/workflow/issues.md`: a deferral's trigger has no watcher and
  the open issue is not one, so an externally-triggered deferral accumulates
  re-checking cost and, where it is also the sole tracker of a drift elsewhere,
  drops that drift silently when closed. #1053 against
  `templates/base/core/git.md`: the release procedure says nothing about other
  ready pull requests, and merging one between the release commit and the tag
  ships it inside the release unlisted, with no gate reporting it.
- **Pending:** nothing. Every checklist item was verified against the tree, the
  tracker or the remote rather than deferred.

## 2026-08-24 — Gate the prose conventions (afternoon)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Reviewed whether ADR-016 was worth keeping**, at the owner's question,
    and kept it. The record is cited as live policy by PLAYBOOK 1.6 and 5, and
    retracting it would need a superseding record plus two PLAYBOOK rewrites --
    more artifact to remove one than to keep it. The divergence it bounds also
    survives retraction, since two tickets still sit closed against a pinned
    rule that says carry them open. The fair criticism went in the reply: it
    generalises from one instruction applied twice, and decisions 4 to 6
    restate rules that already exist elsewhere.
  - **Gated decision-record readability** as ADR-017: 40 words a sentence, 80 a
    paragraph, enforced by `tests/test_decisions_are_readable.py`. Both numbers
    are calibrated rather than picked. The 71 pinned template files put their
    99th-percentile sentence at 42 words and the project's tightest prose, the
    README and `CLAUDE.md`, tops out at 41, so 40 is where the prose this
    project is measured by already sits. A limit of 35 would have been stricter
    than the templates' own prose.
  - **Edited 13 of the 16 merged records without superseding one.** The gate
    reported 22 offenders, and every one shared a single shape: a list written
    as a sentence. That is what made the edit safe, because rendering the list
    as a list moves no word of the argument. ADR-017 bounds the divergence from
    the format-migration rule at the claim rather than the byte, and 9 of the
    22 sat in the `**Upstream:**` block, which is project front matter rather
    than one of the four sections that rule names.
  - **Gated Markdown width** as ADR-018, at 80 columns. The convention turned
    out to be unwritten rather than unenforced: `.editorconfig` sets a width
    under `[*.py]` only and CONTRIBUTING states 120 with 80 recommended under a
    heading that reads Code style, so neither reaches prose. Of 165 lines past
    80, 160 are in the tutorial imported with the v0.1.0 tree at its own width
    and 2 are README badge links, which left three genuine offenders.
- **PRs merged:** none. #96 is open, green on all ten checks, and carries all
  four commits pending the owner's review.
- **Issues closed/created:** none either way. The work was owner-directed in
  conversation against an empty backlog and carried no tracking issue.
- **Lesson:** a summary line is not a verification. The record introducing the
  readability gate breached it, and the local run was reported green on content
  that CI then failed. The cause was reading `pytest -q` through `tail -3` and
  taking a pass line at face value; the byte-identical content ruled out any
  environment difference. Read the count deliberately, especially when the
  claim being made is that a new gate passes.
- **Lesson:** near-total compliance is what hides a convention. The 80-column
  wrap was kept by every document in the tree and written down nowhere, so
  nothing looked wrong until a 98-column heading rode a fully green pipeline.
  The tell was not the missing rule but the one line that broke it.
- **Lesson:** measuring the threshold inverted the instinct. Intuition reached
  for a tighter sentence limit than the corpus supports, and the distribution
  showed that limit would have gated the project's prose more strictly than the
  templates it inherits -- a gate the project would have fought rather than
  kept.
- **Lesson:** an issue number was written into a record and a pull request
  before the issue was filed, twice, and matched by luck both times. Filing
  first costs nothing and the alternative is a citation that points nowhere.
- **Upstream:** two filings. braboj/solid-ai-templates#1054 against
  `templates/base/core/docs.md`: the format-migration exemption enumerates
  permitted operations, so it is under-inclusive by construction and omits the
  one edit an immutable record most needs. #1055 against the same file: a width
  rule stated for code does not reach the prose around it, since an
  `.editorconfig` entry and a Code style heading both stop at the source tree.
- **Pending:** #96 is unmerged and awaiting review, which is the owner's call
  and the only blocked item. Two findings are recorded here rather than filed,
  because the owner has deliberately kept the backlog empty and filing is their
  decision: `src/pyomb/stream.py` and three test modules cite ADR numbers in
  comments and docstrings, which `CLAUDE.md` forbids and no gate catches; and
  the journal's own prose is gated for width but not readability, running to a
  128-word sentence and list items past 200 words.

## 2026-08-24 — Adopt the ADR front-matter schema (evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Traced why this project and `imbra-explore` write records in two
    formats.** The answer was upstream and not in either repository. The
    templates repository decided the schema in its own ADR-010 on 2026-06-02
    and lists the reconciliation of `templates/base/core/docs.md` among that
    record's own consequences. The follow-up never landed, so the shipped
    template still carries the pre-ADR-010 form. The sibling copied the
    repository's own template and this project read the shipped one.
  - **Migrated all 18 records to the schema** and recorded it as ADR-019. The
    diff is metadata-only: the three bold-label fields become the front-matter
    block, and the single prose line that moves is a ragged wrap left by the
    width fix in the previous session, which re-flows without changing a word.
  - **Declined ADR-010's prose rule**, which forbids naming another record in a
    body. Measured first: all 18 records do it, 75 times. Removing a citation
    removes the sentence's subject, since ADR-013 exists to correct the
    baseline ADR-012 set and cannot say what was wrong without naming it. It
    also contradicts a rule in `CLAUDE.md` that outranks a pinned template by
    that file's own precedence order.
  - **Built the schema gate** as `tests/test_decision_frontmatter.py`, which is
    the smoke check ADR-010 defers to a follow-up. It found a live defect on
    its first run: neither superseded record pointed forward. ADR-007 and
    ADR-012 said so in prose and nothing carried the reverse link.
  - **Bumped `imbra-explore`'s templates pin** from a branch-tip commit 64 past
    v2.17.0 to the v2.44.0 tag, as pull request 263 in that repository. It is
    deliberately not ready to merge: the bump spans 147 commits and 2377 lines
    of rule change, and the reconciliation against that repository's own
    conventions needs a session with its documents read.
- **PRs merged:** #96 and #97 here, in that order and bottom-up. Pull request
  263 in `imbra-explore` is open and waiting on its reconciliation.
- **Issues closed/created:** none here. Upstream, braboj/solid-ai-templates#1056
  against `templates/base/core/docs.md`.
- **Lesson:** when two consumers of one authority disagree, the authority's own
  decision log outranks what it ships. This session checked the shipped
  template, found it prescribed bold labels, and concluded the sibling had
  invented its format and mislabelled it as conformance. That was wrong in both
  halves. The record that settles it sits in the upstream repository's own
  `docs/decisions/`, which is not part of the chain a consumer resolves and so
  is never read by accident.
- **Lesson:** the de-stack went by the book because the book was already
  written. PLAYBOOK 1.5 described this exact squash-merge conflict shape and
  said to compare the two conflict stages rather than reason about which side
  wins. Following it turned six conflicts into six one-line judgements, and two
  of them would have been missed entirely: the merge output was read through
  `tail`, and only `git diff --name-only --diff-filter=U` showed `CLAUDE.md`
  and PLAYBOOK were also unresolved.
- **Lesson:** declining part of an inherited rule needs the measurement rather
  than the instinct. The reasons for keeping prose citations were clear before
  counting them, but 75 across all 18 records is what makes the decline a
  recorded decision instead of a preference.
- **Upstream:** one filing. braboj/solid-ai-templates#1056: a decision recorded
  in a repository's own log does not reach the consumers of what it ships, and
  the follow-up that would carry it across is itself a consequence of that
  decision, so nothing outside the repository fires when it never lands. The
  filing carries a second point, that ADR-010's closed category set names the
  template repository's own domains and describes nothing in a consumer.
- **Pending:** the `imbra-explore` reconciliation, which is that repository's
  work and is listed in its pull request. Nothing here.

## 2026-08-24 — Settle the governance files, fix the sdist (late)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Settled whether `CONTRIBUTING.md` and `SECURITY.md` belong at the root.**
    Both, and they stay where they are. The argument offered for the question
    was an external Python blueprint, and reading it turned the question
    around: that repository carries both files too, in `docs/`, so it argues
    about placement rather than existence. Its copies are unfilled stubs
    carrying `[[REPO_NAME]]` and `[[EMAIL]]`, and a supported-versions table
    pinned to a version it never shipped.
  - **Found the pinned templates silent on the whole question.** A grep of the
    submodule at v2.44.0 returns no mention of `CONTRIBUTING.md`,
    `SECURITY.md` or `CODE_OF_CONDUCT.md`, and none of the synonyms either.
    `templates/base/core/readme.md` section 8 is the single acknowledgement
    that a contribution guide may exist, and it neither names the file nor
    says where it lives. `templates/base/security/security.md` is application
    security rules and is not in this project's chain.
  - **Thinned `CONTRIBUTING.md` from 161 lines to 125.** Sections 3 to 6
    restated what PLAYBOOK 1.1 to 1.4, 3.1, 3.3 to 3.6 and 3.9 already own, in
    less detail and different words. Each now keeps the rule a contributor
    needs before starting and cites the numbered section for the commands.
  - **Fixed a packaging defect the analysis surfaced.** A hatchling include
    pattern with no separator matches at any depth, so `tests`, `README.md` and
    `LICENSE` each selected the templates submodule's copy as well as this
    project's. A build from a working checkout carries 57 such files out of
    125; anchoring all four drops the archive to 68.
  - **Wrote the new gate down where the other gates are.** PLAYBOOK 3.17
    carries the command, what the static check cannot see and the archive
    listing that covers it; `CLAUDE.md` section 3 carries the one-line rule.
- **PRs merged:** #101 then #102, in that order.
- **Issues closed/created:** created and closed #99 and #100 here. Upstream,
  braboj/solid-ai-templates#1057 against `templates/base/core/docs.md`.
- **Lesson:** a template repository carrying a file is not evidence that a real
  project needs one. The blueprint's own `SECURITY.md` and `CONTRIBUTING.md`
  are placeholders, so their presence says only that templates ship stubs. What
  actually settled the question was the two files' content here: a scope
  carve-out for the simulator's deliberately weak TLS settings that nothing
  else in the repository states, and a GitHub affordance no other document has.
- **Lesson:** probing a symptom to its mechanism changed the size of the work.
  The sdist bloat was filed as an observation and would have been actioned as
  one; the tell was that the leaked set was exactly the three patterns lacking
  a separator, which turned a vague packaging cleanup into a one-line fix with
  a test that fails against the unfixed manifest.
- **Lesson:** a local artifact is not the published one, and the wrap caught it
  rather than the work. The defect was written up from `dist/` in the working
  tree and described as having reached PyPI. Neither half held: this project has
  no PyPI presence at all, and `release.yml` checks out without submodules, so
  the released sdists never carried the leak. The correction was three committed
  files and an upstream issue already filed. Downloading the release asset is
  one command and it was never run, because a tarball on disk with the right
  version in its name reads exactly like the thing that shipped.
- **Lesson:** thinning a document means checking who cites the parts being cut.
  `pyproject.toml` describes its ruff line length as the ceiling CONTRIBUTING
  sets, so removing that file's style bullets as duplicate would have left the
  configuration pointing at nothing. Two more paragraphs survived the same
  test: the camelCase legacy note and the rule that a protocol change is
  asserted against serialized bytes.
- **Upstream:** two filings. braboj/solid-ai-templates#1057: the docs template's
  Standard documents table names six documents and says nothing about the
  community health files a code host recognises, so every public consumer
  answers the question alone and the structure audit cannot check for a file no
  template names. It also carries a comment on what such a file may hold, since
  a contribution guide sits beside ONBOARDING and PLAYBOOK and absorbs both
  without a boundary. And #1058: `python-lib.md` tells a project to anchor the
  path-based excludes in its tool configuration and says nothing about the
  include patterns of a build target, which is the same defect seen from the
  other side.
- **Pending:** #1057 is filed and not implemented. It edits a document in the
  templates repository, which has its own conventions and its own backlog, and
  the copy here is a pinned checkout.

## 2026-08-25 — Bump the chain, export the simulators

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Bumped the templates pin to `v2.45.0` and restored `examples.md` to the
    startup block.** Upstream cut the tag roughly a day after #68 was closed as
    not-planned for want of it. The manifest adds `base-examples` to the
    `stack-python-lib` chain, so the resolution went from thirteen files to
    fourteen. ADR-015's guard did the reconciliation rather than a person:
    against the new pin with the block untouched it failed naming the file and
    the side it sat on, and passed once the entry went back where #65 had
    removed it from.
  - **Confirmed `base-examples` is a no-op here, against the tagged text rather
    than the untagged text #68 judged it from.** It governs a project that
    ships an `examples/` directory and states that a project without one
    inherits nothing. The two other block files the tag moved, `readme.md` and
    `python-lib.md`, only delegate their examples rules to the new template, so
    neither adds an obligation.
  - **Left ADR-008 untouched, having checked rather than assumed.** Its Context
    counts ten files on the stack axis, its diagram names examples among them,
    and its Consequences count fourteen in the block. All three read accurate
    again at this pin, which is the self-reversing state #68 described when it
    declined to write a supersession.
  - **Exported `OmbClientSim` and `OmbServerSim` from the package root.** They
    were reachable only through their submodules, while `CLAUDE.md` 2.2
    requires the public API be exported explicitly with `__all__`. They now
    bind through a module `__getattr__`, which puts them in the flat API and
    leaves the ssl import to the first caller that asks for a simulator; a
    `TYPE_CHECKING` block hands the checker the real classes so nothing in the
    public API becomes `Any`.
  - **Gave `CLAUDE.md` 2.2 its first check.** Nothing asserted that a name in
    `__all__` resolves, and the list is a literal rather than a reference, so
    an advertised name can have nothing behind it and no gate reports it.
    `tests/test_package_exports.py` pins that contract, and pins the deferral
    from a fresh interpreter, because in-process the suite has already imported
    both submodules for other reasons and would always answer yes.
- **PRs merged:** #105 then #106, in that order.
- **Issues closed/created:** #68 closed by #105. Created #107 and #108, both
  open and neither shipped.
- **Lesson:** a deferred issue's closing comment predicted its own blind spot
  and was right inside a day. #68 was closed recording that upstream cutting a
  tag "will now produce no signal on this side", and that whoever next read the
  startup block was the detection mechanism. The tag landed about
  twenty-four hours later. What caught it was the session-start check of
  submodule state, not anything built for the purpose, which is the argument
  for leaving a triggered-but-unsignalled issue open rather than closing it
  tidily.
- **Lesson:** re-measuring an audit comment turned an override into a
  re-scope. `__init__.py` refused this export in a comment citing 32ms of ssl
  against the package's own 45ms, a 70% penalty, and ended by telling the
  reader to re-measure before treating the number as current. Six paired runs
  put it at 13ms against 35ms, a 38% penalty -- half the recorded cost and
  still real. Honouring the constraint through a different mechanism was then
  the obvious move, where overriding a 70% figure would not have been.
- **Lesson:** a finding read off one line was wrong, and the same file said so
  ten lines higher. The simulators were reported as missing from the public API
  on the strength of `__all__` alone. The module docstring declares
  `pyomb.omb_client` and `pyomb.omb_server` as equally public submodules, so
  the README's import was the documented form rather than a reach past the
  surface. `review.md` asks that a finding be demonstrated before it is
  reported; reading the whole file it sits in is the cheapest half of that, and
  it was the user who caught the gap.
- **Lesson:** an infra failure read as a diff failure until the log was opened.
  The `secrets` gate failed on #106 and took the fan-in `gate` with it. The log
  carried `curl: (35) Recv failure: Connection reset by peer`, so gitleaks was
  never downloaded and nothing scanned the diff. One announced re-run passed.
  The habit `review.md` warns against is retry-until-green, and the only thing
  separating that from a legitimate re-run is whether the log was read first.
- **Upstream:** two filings, both generic once the domain skin comes off.
  braboj/solid-ai-templates#1076 against `templates/base/core/testing.md`: an
  export list is a hand-written manifest of what a module binds, kept beside
  the bindings and drifting from them silently, which is the shape
  `testing-drift-guard` already names three instances of and does not name this
  one. The linter cannot substitute, because `F401` asks whether an import is
  used and `__all__` membership counts as use; it never asks the reverse.
  And #1077 against `templates/stack/python-lib.md`: "All public API exported
  from `__init__.py`" is right as a default and collides with import cost when
  the surface spans a cheap core and an expensive edge, leaving a project to
  break the rule or tax every caller when a third option exists.
- **Pending:** #107 and #108 are filed and unshipped. Upstream,
  braboj/solid-ai-templates#1057 and #1058 remain open; #1056 closed as
  completed. Separately, `origin/main` upstream now sits ten commits past
  `v2.45.0` carrying content changes to `quality.md` and `docs.md` that narrow
  the ASCII rule and stop naming a line-length number. Both bear on ADR-014 and
  ADR-018 here. Nothing is inherited while the pin holds a tag, and the startup
  block guard checks chain membership rather than rule content, so the next
  bump needs those two records reconciled deliberately.

## 2026-08-26 — Bump to v2.46.0, then empty the backlog

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Bumped the templates pin to `v2.46.0` and reconciled both recorded
    divergences.** The previous entry flagged that the next bump would need
    ADR-014 and ADR-018 read first. It did, and the reading went the opposite
    way to what the diff suggested: both records were filed upstream as #1045
    and #1055, both were taken, and the tag that looked like two fresh
    violations was this project's own filings coming back.
  - **Read ADR-014's divergence as resolved rather than refuted.** The rule now
    restricts identifiers and exempts comments, docstrings, string content and
    documentation, so the em dash in prose is compliant outright. What survives
    is a tightening, kept on the record's own evidence: the four defects its
    first measurement found were traced back to the commit that fixed them, and
    all three locations -- a Cyrillic Te in the tutorial's prose, curly quotes
    and an en dash in an `errors.py` docstring -- are exactly what the narrowed
    rule exempts.
  - **Left ADR-018 intact and moved its number into configuration.**
    `.editorconfig` already declared 80 and the test carried a second copy, so
    the module now reads the declaration and a tree declaring no width fails
    outright rather than falling back to a default. `CLAUDE.md`, CONTRIBUTING
    and PLAYBOOK stopped restating the number.
  - **Gave the gitleaks download a retry.** `--retry-all-errors` rather than
    `--retry`, because curl counts only timeouts and 408, 429 and 5xx as
    transient, and the fault that failed this gate was a connection reset.
    `tests/test_workflow_downloads_retry.py` pins the retry and the fail-fast
    flags on every download any workflow makes.
  - **Set the output encoding at every entry point that prints.** Six sites,
    not the nine the issue claimed: only four of seven scripts write text. The
    two package modules call it inside their `__main__` guard and check the
    attribute first, which is what mypy demanded and what a replaced or absent
    stdout demands anyway. `demo_metaclass.py` gained a guard rather than a
    bare call, which also removed an import side effect it already had.
  - **Shipped `examples/` with a job that runs it.** Four journeys, an index
    pairing each with real output, and a job that installs the project with
    plain pip and no extras on 3.10, globs the directory, counts what it ran
    and fails on zero. The directory joined the ruff and bandit scopes, so it
    is clean against the whole rule set with no freeze entry.
  - **Scoped the new prose-citation rule to records from 020 forward.** ADR-020
    and `tests/test_decision_citations.py`; the fourteen merged records that
    cite another keep their prose.
  - **Recorded the examples port divergence as ADR-021.** The directory shipped
    without a record, which the end-of-session audit caught rather than the
    rule preventing.
- **PRs merged:** #113, then #114 and #115, then #116, then #117. #118 and the
  wrap follow.
- **Issues closed/created:** #107, #108, #110 and #111 closed by the pull
  requests above. #112 closed as not planned, having been filed in error.
  Nothing new opened; the backlog is empty.
- **Post-mortem (#112, filed against work that already existed):**
  - **Symptom:** an issue asserting that nothing opens the built wheel, with
    acceptance criteria that were already met in full.
  - **Root cause:** the claim came from reading the `v2.46.0` diff of
    `python-lib.md`, which adds a wheel-contents check, and inferring the gap.
    The workflow that would have settled it was never opened.
  - **Why missed:** nothing distinguishes a template rule the project already
    satisfies from one it does not, and a diff cannot say. Three other new
    checks were verified against the tree that morning; this one was not,
    because the template's own prose asserts no other gate covers it, which
    read as confirmation.
  - **Fix:** closed with a comment naming the existing step in `ci.yml` and
    PLAYBOOK 3.11.
  - **Prevention:** when a template diff names a missing check, grep the
    workflows and the playbook for it before filing. `base-review` already
    covers this under "From an extraction" -- absence of evidence from a
    partial view is not evidence of absence -- and a template diff is exactly
    such a view.
- **Lesson:** a divergence can close from the other side, and the diff does not
  say so. Reading the divergence record before the diff, which `base-docs`
  asks for, turned a supposed two-record migration into one deleted constant.
- **Lesson:** taking a narrowed rule verbatim would have re-hidden the defects
  the original was raised by. Every homoglyph and smart character ADR-014 found
  sat in a comment, a docstring or prose -- precisely what `v2.46.0` exempts.
  The evidence for keeping the local rule stricter predates the change by five
  days and was still sitting in the record.
- **Lesson:** the coverage guard on a meta-test earned its place twice in one
  session, both times before the thing it guards was written. The workflow
  retry check's first curl pattern anchored at the bare start of a line and
  matched nothing under a `run` block's indentation; the citation check found
  no records because the new one was not yet staged and `git ls-files` reads
  the index. Both would have passed while reading nothing.
- **Lesson:** a rule arriving after a corpus is already immutable needs a
  stated scope, and the count that decides it is not the obvious one. Fourteen
  of nineteen records cite another in prose, which sounds like a migration;
  eight carry the citation inside a Decision section, which is what makes it
  impossible. Measuring the second number turned a fourteen-file rewrite into
  one record and one check.
- **Lesson:** the wrap-up audit found a rule the session had broken. `examples/`
  is a new directory and `base-docs` wants the record written before the files,
  so ADR-021 is late by four hours. Nothing else in the session would have
  surfaced it, which is the argument for executing the checklist rather than
  summarizing it.
- **Upstream:** two filings. braboj/solid-ai-templates#1104 against
  `templates/base/core/docs.md`: a rule constraining the form of documents that
  are immutable once merged has to say whether it binds forward or
  retroactively, since the two readings differ by an unbounded amount of work
  and by whether an existing corpus is compliant or in violation. Recorded on
  the `Upstream:` line of ADR-020 at decision time rather than at the wrap. And
  #1107 against `templates/base/core/testing.md`: a meta-test that enumerates a
  corpus needs a companion assertion that the corpus was not empty, because an
  empty enumeration is indistinguishable from full compliance -- the template
  already names two patterns of this shape and neither carries the guard.
  ADR-021 records `none` with a revisit trigger: one project meeting a
  privileged-port collision once is not evidence the rule generalizes.
- **Pending:** nothing in this repository. Upstream sits at `v2.49.0`, three
  tags past the pin, touching four chain files -- `docs.md`, `git.md`,
  `testing.md` and `quality-gates.md`. The citation rule is unchanged there, so
  ADR-020 is not at risk of same-day supersession, but that bump is its own
  session and wants the same read-the-record-first treatment this one needed.
  braboj/solid-ai-templates#1057, #1058, #1076, #1077, #1104 and #1107 remain
  open upstream. One residual was recorded rather than filed: `release.yml`
  builds its own artifacts on a tag without repeating the wheel-contents
  assertion, which needs a build-configuration change landing between a merged
  commit and its tag to matter, so there is no window.

## 2026-08-26 — Scope the precedence rule, ship v0.3.0 (afternoon)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Fixed the ADR-vs-template precedence conflict at the source rather than
    carrying it here.** `v2.49.0` added a clause to `docs.md` ruling that where
    a merged record and the templates disagree, the templates govern and the
    record stands as history. This project's precedence order puts the records
    above the pinned chain, which is the rung ADR-014, ADR-019 and ADR-020 sit
    on. Taking it verbatim would have expired all three the moment upstream
    restated the rule each departs from, with a pointer bump as the trigger and
    nothing reporting it. All three survived anyway, but only because each is
    also written into `CLAUDE.md`, which outranks the chain either way -- safe
    by being recorded twice rather than by design.
  - **Scoped the clause upstream, in two halves.** It was written for
    braboj/solid-ai-templates#1098, where a record carries a stale claim that
    can be neither edited nor superseded. That reasoning holds in a repository
    that owns the rules its records describe, where a record drafts the spec and
    the spec winning is right. Shipped inside a template it bound every
    consuming project to a ruling written for the inverse relationship, where a
    record is a written refusal rather than a draft. `docs.md` now leaves
    precedence to the consuming project's own context file; templates-govern
    moved to the templates repository's `CLAUDE.md`, beside the immutability
    rule it already carries. Scoping beat deleting because deletion leaves the
    question unanswered and makes the next consumer invent a ruling.
  - **Bumped the pin from `v2.46.0` to `v2.51.0` with no divergence recorded.**
    Five tags, three chain files -- `docs.md`, `git.md` and
    `platform/github.md`. Nothing needed changing here: the precedence order
    `CLAUDE.md` already declares is what the scoped clause now defers to. The
    range also carried rules this project already satisfies, several derived
    from its own filings -- administrator-bound protection at a zero review
    count, minor-pinned linters, a full-history secret scan, an isolated CodeQL
    workflow carrying its own fan-in, and run selection by full commit SHA.
  - **Released `v0.3.0`.** Twenty-four pull requests since `v0.2.1`. The tag is
    annotated at the release commit rather than at whatever `main` pointed to,
    `release.yml` built and attached the wheel, sdist and SBOM, and the README's
    install URL was confirmed live against the published wheel rather than
    assumed. `tests/test_readme_install_command.py` failed the bump until the
    quick start moved with it, which is the whole reason that guard exists.
- **PRs merged:** #120 then #121. Upstream, braboj/solid-ai-templates#1118;
  #1121 closed as a duplicate of #1120.
- **Issues closed/created:** created #122 and #123. Upstream, filed #1117 and
  shipped it the same session; filed #1127, open.
- **Lesson:** a duplicate shipped because external state was checked early and
  not again at the moment of acting. Upstream #1049 was read as open, then a
  fix for it was written, reviewed and pushed while the owner merged his own as
  #1120. `ai-workflow` puts the check immediately before the visible action for
  exactly this reason; a reading several minutes stale is not a reading, and
  the wasted work was the cheap half of the cost.
- **Lesson:** a check returned a plausible number for the wrong reason and was
  nearly believed. The pre-release orphan scan compared unreachable commit
  subjects against `main` by exact string, so squash-merge's appended `(#N)`
  made 118 of them read as lost work. The tell was the size of the result on a
  tree with no unmerged branches. `review.md` asks that a measurement be
  hand-checked against one flagged item before it is reported, and one would
  have settled it instantly.
- **Lesson:** reading the target before filing turned a wrong issue into a
  sharp one. A line-ending gate was about to be filed as an unconsidered gap;
  PLAYBOOK 3.12 already documents both commands, the binary-reclassification
  trap, and the incident where this journal sat with 1127 CRLF endings while
  the check reported clean. The real gap is narrower and worth more: the check
  is manual while its sibling 3.13 runs as pytest on every pull request.
- **Lesson:** a filtered tracker query hid the item that mattered. Listing a
  milestone by title showed four issues and read as complete once two moved;
  the API listing showed a fifth, open, that the title query never returned.
  Milestone state drove a release decision, so the cheaper query was the one
  that could have shipped a half-done milestone.
- **Lesson:** the release shipped without its changelog entry, and the wrap-up
  audit is what caught it. PLAYBOOK 5 step 4 cuts the `Unreleased` block into
  a versioned entry; step 5 points the README at the new wheel. Step 5 is
  gated by `tests/test_readme_install_command.py` and failed the bump on cue.
  Step 4 is gated by nothing, so it was simply not done, and its neighbour
  passing made the procedure feel complete. `v0.3.0` is tagged with a
  changelog that does not name it -- unrecoverable for that archive, since
  re-tagging a published release is worse than the gap. #123 carries the
  missing gate. Two adjacent steps, one enforced, and only the unenforced one
  was missed.
- **Upstream:** two filings beyond the shipped fix.
  braboj/solid-ai-templates#1127 against `templates/base/core/git.md`:
  pre-release step 4 verifies that every issue closed since the previous tag
  carries the milestone being released, while `platform/github.md` holds that a
  routine release never scoped as a milestone gets none and MUST NOT have one
  backfilled. A project using milestones selectively runs the check on a
  routine release and gets every closed issue back, correct and unactionable,
  in the same shape as a real finding. Observed here: eight lines, none
  actionable, release correct to cut. And #1133 against
  `templates/base/workflow/quality-gates.md`, generalised from the changelog
  miss: the existing rules cover a constraint with no check and a check never
  run, but not a procedure mixing gated and ungated steps, where the gated
  ones supply confidence the others have not earned. Enforcement is not
  transitive across adjacent steps, and the step to gate first is the one
  whose omission cannot be corrected afterwards.
- **Pending:** #122 and #123 are filed and unshipped. The templates
  repository's own release procedure wants the `v2.51.0` cut recorded as its
  own unmilestoned journal entry, which has not been written. Upstream,
  braboj/solid-ai-templates#1057, #1058, #1076, #1077, #1104, #1127 and #1133
  remain open; #1107 closed since the previous entry named it, which is signal
  that the older filings are being worked rather than accumulating. Upstream
  also cut `v2.52.0` while this session ran, touching five chain files across
  161 added lines -- `docs.md`, `git.md`, `review.md`, `testing.md` and
  `quality-gates.md`. That is the next bump and wants its own session, read
  against the divergence records the way 4.1 now says.
## 2026-08-26 — Gate the two unenforced rules (evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Gated the line-ending rule the playbook documented and nothing ran.**
    Two rules: no index entry carries a carriage return, and nothing the
    project declares text is stored as binary. The second is what a count
    cannot express -- a blob git classifies as binary stops being normalised,
    so its carriage returns enter the index unconverted while the count reads
    zero, which is how this journal came to hold 1127 of them under a clean
    report. Which files are legitimately binary now comes from git's own
    attribute column rather than a list in the test: the specifications are
    declared binary in `.gitattributes` and report `-text` in both columns,
    while a file detected as binary under a `text=auto` declaration is the
    incident shape exactly. `mixed` joined the carriage-return set, which the
    documented count of `i/crlf` never reported though it commits the same
    bytes. PLAYBOOK 3.12 becomes a pytest section like its siblings.
  - **Gated the changelog entry beside the wheel URL it sits next to.** Five
    rules against the version the package reports: a dated section records
    it, the `Unreleased` link compares from it, every section carries a link
    definition, no definition outlives its section, and none resolves to a
    version other than its label. The last catches a link copied from its
    neighbour and not retargeted, which resolves and is wrong, so a reader
    meets it only by following it. Release step 4 names the test the way step
    5 names its own, and the `Unreleased` block now records both gates --
    step 4 presupposes that block accumulates and it was empty.
  - **Committed the negative controls rather than only running them.** Both
    modules express their rules as pure functions over parsed records, so a
    planted record of each break sits in the suite as a test rather than as a
    claim in a commit message. The end-to-end controls stayed out of the
    tree: a throwaway repository carrying a real CRLF blob, a real mixed blob
    and a real NUL byte for one, and a reproduction of the tree `v0.3.0` was
    tagged in for the other.
- **PRs merged:** #125 then #126.
- **Issues closed/created:** #122 and #123 closed by the pull requests that
  carry them, which emptied the backlog. #127 and #128 created during the
  wrap-up audit. Upstream, filed braboj/solid-ai-templates#1140.
- **Lesson:** a negative control needs proof the break landed. Three
  structural assertions were controlled by patching the module under test,
  and two of the patterns did not match, because the anchor carried an escape
  the pattern miscounted. The run then reported that neither assertion fired,
  which reads exactly like a coverage guard that is decorative. It was caught
  only because three breaks ran back to back and the failing pair was
  identical every time, so the edit had made no difference at all. One break
  on its own would have shown a plausible result with nothing to compare it
  against. An edit that matches nothing exits zero, so a break that never
  landed and a check that never fired produce the same evidence.
- **Lesson:** the acceptance criteria named a behaviour and the cheaper
  implementation was already in hand. "A file reporting `i/-text` that is not
  one of the specification PDFs fails" invites hardcoding four paths, or a
  suffix set that would let a stray byte excuse itself by the file's name.
  git resolves the attributes itself and prints them in the same record, so
  the declaration is readable rather than restatable, and the rule that falls
  out -- declared binary passes, detected binary fails -- is the incident
  shape rather than an approximation of it. Reading the tool's whole output
  before designing against a summary of it is what surfaced the column.
- **Lesson:** a synthetic fixture is shaped by whoever imagined it. The
  changelog gate carries a clean synthetic file and one break per rule, and
  every one passed first time, because the fixture and the readers came out
  of the same head. Reproducing the tree `v0.3.0` was actually tagged in is
  what made the control independent: it failed two rules naming both faults,
  which is the evidence that this gate would have stopped the release that
  prompted it. No file written for the occasion could have said that.
- **Lesson:** the wrap-up audit found the class of claim nothing reads. Every
  document gate in the suite checks what is inside a file -- characters,
  widths, front matter, citations, links, versions -- and none of them reads
  a sentence about the state of the tree. `docs/ONBOARDING.md` still tells a
  new contributor that the repository, the distribution and the import
  package do not yet share a name, which ADR-006 settled when it carried
  `pyomb` to a clean repository. True when written, false since the v0.1.0
  import, and invisible to every check because it is prose about the world
  rather than content in a file. #127 carries it.
- **Upstream:** one filing. braboj/solid-ai-templates#1140 against
  `templates/base/workflow/quality-gates.md`: the negative-control rule
  governs the control and not the step that plants the break. The file
  already legislates the same shape one bullet away, where a check must state
  what it inspected because reaching zero files and finding zero violations
  print the same thing. A second candidate -- expressing a rule as a pure
  function so its negative control can be committed -- was considered and not
  filed, because `testing-characterization-fingerprint` rules the other way
  for its own scaffold and a filing that does not engage that tension is not
  worth the maintainer's time.
- **Pending:** #127 and #128 are filed and unshipped. The pin sits at
  `v2.51.0` while upstream has cut `v2.52.0` and `v2.53.0` -- six chain files
  and 199 added lines -- which #128 now carries rather than a line here, so
  the next session reads it from the tracker. The templates repository's own
  release procedure still wants the `v2.51.0` cut recorded as its own
  unmilestoned journal entry, which remains unwritten. Upstream,
  braboj/solid-ai-templates#1057, #1058, #1076, #1077, #1127, #1133 and #1140
  are open; #1104 closed since the previous entry named it.

## 2026-08-26 — Clear the backlog, bump the pin (late)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Dropped the naming claim ONBOARDING carried past its own settlement.**
    Section 5 told a new contributor that the repository, the distribution and
    the import package do not yet share a name. All three read `pyomb` and
    have since the v0.1.0 import: ADR-002 decided the last two while leaving
    the repository as `protocol-modbus`, and ADR-006 then carried the name to
    a clean repository without touching the sentence describing the gap. The
    paragraph goes rather than being restated, because a settled fact needs no
    sentence and section 5 is a domain overview beside its links. The sweep
    for other survivors found only ADR-002 and ADR-006, which are merged
    records of what was true when written, and the second says so itself.
  - **Bumped the pin to `v2.53.0` and reconciled four divergences.** Two tags,
    six chain files, 199 lines added, every one of them in the startup block.
    The range has a single theme: a check reports what it inspected, and a
    count of zero is a failure rather than a clean result. None of ADR-014,
    ADR-017, ADR-019 or ADR-020 is refuted by it. ADR-014's rule lives in
    `quality.md`, which the range does not contain at all. The other three
    point at `docs.md`, which it does contain -- and all three hunks there
    touch the checks that file ships rather than the immutability or citation
    text the records bound.
  - **Corrected the reconciliation instruction while executing it.** PLAYBOOK
    4.1 named ADR-014, ADR-019 and ADR-020 as the records to re-read on a
    bump and omitted ADR-017, whose own Consequences ask for exactly that
    reading. Fixed in the same change rather than filed, because it is the
    procedure the change was running.
- **PRs merged:** #130 then #132.
- **Issues closed/created:** #127 and #128 closed by the pull requests that
  carry them. #131 created from a negative control run during the bump.
  Upstream, filed braboj/solid-ai-templates#1150.
- **Lesson:** the gates that enforce the divergences are the ones that cannot
  report having run. `testing.md` arrived with a rule that the coverage
  assertion belongs in its own test, so every document gate was controlled by
  patching its enumeration to return nothing and rerunning the module. Three
  of six passed on an empty corpus, and they are the checks implementing
  ADR-014, ADR-017 and ADR-019 -- each divergence record's own enforcement
  mechanism. Nothing about those three is unusual. Each was written to assert
  a property of file content, and whether any file was read was never the
  property. The previous entry closed on a claim that no gate reads; this is
  the same shape one level up, where the assertion is real and the corpus
  behind it is not proven. #131 carries the measurement.
- **Lesson:** a file in the range is not a rule in the range. Three of the
  four records name `docs.md`, so the first reading of the diffstat is that
  three divergences are in play at once. Every hunk in that file adds a count
  and a zero guard to an embedded check, which is a neighbour moving rather
  than the rule. Separating the two is the reconciliation, and it took
  grepping the range for the rule text to say so -- reading the file list
  alone reports the opposite and reads as three gaps to close.
- **Lesson:** an instruction that enumerates its own subjects goes stale in
  the direction nothing watches. PLAYBOOK 4.1 listed three of the four
  records carrying a divergence, and the omitted one is the most recent to
  state the requirement in its Consequences. A list of instances drifts as
  instances are added, and the addition is a different pull request from the
  one that maintains the list, so neither side ever sees both. It surfaced
  only because the list was executed rather than read.
- **Upstream:** one filing. braboj/solid-ai-templates#1150 against
  `templates/platform/github.md`: the label conformance check was rewritten
  from jq into Python and kept the jq form's pass condition three paragraphs
  below the new one, so the file states both `Output MUST be []` and that the
  command reports a count. The rewritten check prints `issues inspected: N`
  and never `[]`, so a reader taking the literal instruction reads a correct
  run as a violation. Found by running the check in the form it ships rather
  than reading it. A second candidate -- that a procedure enumerating the
  records it governs should derive them rather than list them -- was
  considered and not filed, because `base-docs` already rules that a
  hand-maintained restatement of a self-documenting source drifts, and a
  filing that only re-states it in a new setting is not worth the
  maintainer's time.
- **Pending:** #131 is filed and unshipped, and it is the only open issue.
  The templates repository's own release procedure still wants the `v2.51.0`
  cut recorded as its own unmilestoned journal entry, which remains unwritten
  and is now two tags behind. Upstream, braboj/solid-ai-templates#1058,
  #1076, #1077, #1127, #1133, #1140 and #1150 are open; #1057 closed since
  the previous entry named it.

## 2026-08-28 — Un-blind the gates, bump the pin

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Made every document gate fail when it reads nothing.** Six checks assert
    that a list of violations is empty, and three passed on an empty corpus —
    the character set, the readability limits and the frontmatter schema,
    which are the enforcement mechanisms of three recorded divergences. Each
    now carries a coverage test of its own asserting a floor rather than
    non-emptiness, because a listing that returns one entry passes a non-empty
    check while measuring nothing. Coverage reaches past the file list where
    the file list is not the only thing that can come back empty: the
    readability gate floors the sentences it parsed, and the character-set
    gate floors each half of the tree, since its two rules read one each.
    ADR-022 records the floors, how each was sized, and why the unstaged-file
    gap is stated rather than closed.
  - **Shipped the negative control as a test rather than running it once.**
    `tests/test_document_gates_are_not_blind.py` discovers each gate by how it
    reads its corpus and blinds it through the call they all share, so a
    seventh gate is covered without being registered anywhere and a new gate
    written without a coverage assertion fails on the pull request that adds
    it. Verified both ways: it fails against the unfixed tree naming exactly
    the three blind gates, and a deliberately blind gate planted in the suite
    was discovered and failed before being removed.
  - **Bumped the pin to `v2.54.0` and reconciled the divergences.** The first
    range to reach the rules the records bound rather than the checks beside
    them. ADR-020's citation scope was adopted upstream in it, from this
    project's own filing, so that record now describes an inherited rule.
    ADR-017's format-migration boundary was taken at `v2.47.0`, also from this
    project's filing. ADR-019's decline had already been narrowed by ADR-020,
    so none of it is live. ADR-014 is not in the range at all and stands the
    other way round: `quality.md` narrowed its ASCII rule to identifiers at
    `v2.46.0`, so this project's rule is the stricter of the two. PLAYBOOK 4.1
    now records where all four stand, so the next bump starts from the settled
    position rather than re-deriving it.
  - **Named the distribution the release workflow produces.** CLAUDE.md 1.1
    read `Distribution: PyPI as pyomb` while the release workflow attaches a
    wheel and an sdist to the GitHub release and stops there, which is what
    ADR-011 decided and what the README and the changelog already said. The
    context file was the stale side of a three-way disagreement, and the one
    read on every turn.
  - **Named the declared TLS floor among the secure defaults.** CLAUDE.md 2.4
    enumerated four load-bearing defaults and the protocol floor was not among
    them, which is the enumeration the tests had mirrored before the floor was
    lost. See the post-mortem below.
  - **Declined the code of conduct rather than leaving it open.** The rule the
    range added is a SHOULD and the template says plainly that it is a
    governance choice, so the decision was the owner's. Closed with `wontdo`,
    the reasoning recorded, and a revisit trigger named: the first issue,
    discussion or pull request opened from outside the organisation.
- **PRs merged:** #135, #139, #140 and #141.
- **Issues closed/created:** #131 and #134 closed by the pull requests that
  carry them. #136, #137 and #138 created while reconciling the pin, filed
  rather than absorbed into the bump; #136 closed as declined, #138 closed by
  #140, and #137 closed by this entry. Upstream, filed
  braboj/solid-ai-templates#1161.
- **Post-mortem (#76, owed since 2026-08-22 and written here because a journal
  entry's account is fixed):**
  - **Symptom:** the client and the server built their `ssl.SSLContext`
    without declaring a minimum protocol version, so the floor was whatever
    the linked OpenSSL supplied. Nothing was exploitable where it ran, since
    that default was already TLS 1.2. CodeQL's first full-tree analysis of
    `main` rated it high under `py/insecure-protocol`.
  - **Root cause:** the floor was inherited rather than declared, and
    `ssl_options` defaulting to `ssl.OP_ALL` reads as though it covers the
    protocol switches. It does not — `OP_ALL` is a bug-compatibility mask and
    shares no bits with `OP_NO_TLSv1`.
  - **Why missed:** `TestSecureDefaults` already asserted properties of the
    constructed context rather than of a successful handshake — peer
    verification, client certificate required, no cipher string — so the test
    class with the right shape existed. The floor was not among the defaults
    CLAUDE.md 2.4 enumerated, so it was not among the properties pinned
    either, and a value the platform supplies is indistinguishable from one
    the library sets until something asserts which. The scanner that found it
    had until then been read on pull-request refs, where a clean row means the
    branch added nothing.
  - **Fix:** #83 declared `MINIMUM_TLS_VERSION` on both endpoints and set it
    after the caller's options, which are OR-ed in and can only add a
    restriction. Deliberately not done: `ssl_options` was neither removed nor
    narrowed, so a caller can still pin a session above the floor and only
    above it.
  - **Prevention:** four assertions on the constructed context, in
    `tests/test_tls_integration.py`, which fail against the unfixed source
    with 769 where 771 is required. The enumeration that was short by one is
    fixed rather than left: #141 adds the declared floor to CLAUDE.md 2.4 and
    says it is the one default taking no relaxing argument, so the list the
    tests mirror now matches the code.
- **Lesson:** a control that proves a check is not blind belongs in the suite,
  and it has to discover its subjects. A roster of the checks under control
  carries the same blind spot as the checks themselves — a member missing from
  it is never controlled, and the roster reports success while covering less
  than it claims. Blinding the one call the family shares covers a gate nobody
  has written yet and needs no knowledge of what each named its enumeration.
- **Lesson:** a poll that exits on an empty list reports silence as success.
  Waiting on a pull request's checks with a condition that every one is not
  pending is true over an empty array, so the wait ended before the first
  check had registered and printed that no checks were reported on the branch.
  Read straight that says the workflows never fired; both were in fact
  running. CLAUDE.md already carries this shape for `gh run list --commit` on
  an abbreviated hash, and the fix is the same one — require the list to be
  non-empty before believing what it says.
- **Lesson:** a divergence can be absorbed upstream tags before anyone reads
  it that way. The format-migration boundary was taken at `v2.47.0` and the
  ASCII rule was narrowed at `v2.46.0`, both below the pin the previous
  session reconciled against. That session reported no record refuted, which
  was true and is not the same statement: a diff cannot show that a departure
  had already stopped being one. Dating the clause with a pickaxe search
  against the tags is what separates the two, at one command per record.
- **Upstream:** one filing. braboj/solid-ai-templates#1161 against
  `templates/base/core/testing.md`: the coverage rule names a meta-test as the
  route to enforcing it and does not say how a family of checks is controlled.
  Two additions, both measured here — replace the single call the family reads
  through rather than each member's own reader, and derive the members from
  that call rather than listing them. A second candidate, how to size the
  floor an append-only corpus takes against a churning one, was left out as a
  separate addition to the same rule rather than folded in. #1076, #1104 and
  #1150 have closed since the previous entry; #1058, #1077, #1127, #1133,
  #1140 and #1161 are open.
- **Pending:** the backlog is empty. The templates repository's own release
  procedure still wants the `v2.51.0` cut recorded as its own unmilestoned
  journal entry, which remains unwritten and is now three tags behind.

## 2026-08-28 — Bump the pin, file the gaps (morning)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Bumped the pin to `v2.56.0` and reconciled the divergences.** The issue
    was filed against `v2.55.0`, which upstream superseded the same day, so
    the range was three chain files rather than the two the body named and
    `git.md` moved 144 lines rather than the seven it reported. The scope
    correction went on the issue before any work started, because the
    acceptance criteria were written against the narrower range. None of the
    four divergence records is touched: neither `quality.md` nor `docs.md`
    appears in the range at all.
  - **Named where the suite already stands against each rule the range adds.**
    `testing.md` adds five sections and one drift-guard bullet, and the suite
    satisfies all six as it stands. Each was checked against the code rather
    than assumed: the published CRC vectors in `test_rtu_crc.py`, the lock
    exercised rather than typed in `test_stream_locks.py`, the bind failure
    `occupy_a_port()` injects, the port-0 allocation ADR-021 settled, the
    autouse guard in `conftest.py`, the TLS 1.0 context
    `test_tls_integration.py` substitutes at the seam the module under test
    reads, and every `__all__` entry resolved in `test_package_exports.py`.
    The sixth, an AST comparison proving a whole-tree rewrite preserved
    meaning, binds a rewrite this project already did: ADR-004 adopted `ruff
    format` before the rule existed, so nothing is owed and nothing is
    retrofitted.
  - **Recorded the divergence position in PLAYBOOK 4.1 as a command rather
    than a sentence.** The previous bump left the settled position in prose,
    which the next bump has to take on trust. It is now two commands: one
    naming the files it reached, one reporting whether they moved. The first
    exists because the second cannot tell a range that changed neither file
    from a path that no longer exists.
- **PRs merged:** #146.
- **Issues closed/created:** #143 closed by #146. #144 and #145 created while
  reconciling the pin, filed rather than absorbed into it, and both open.
  Upstream, filed braboj/solid-ai-templates#1181.
- **Lesson:** a claim written about a check is not a property of it. PLAYBOOK
  4.1's new command was first shipped with the sentence that a mistyped path
  turns into a git error rather than into silence, which would have made an
  empty result a real pass. `git diff --stat <a> <b> -- <mistyped>` prints
  nothing and exits zero. It is the shape ADR-022 was written for, one level
  up: the reasoning that licences reading an empty result as a pass is itself
  the thing that needed the negative control. Running it before committing is
  the whole difference, and it cost one command.
- **Lesson:** fixing a rule upstream does not fix the copy this project runs.
  Three of the range's changes are this project's own filings landing --
  #1076 in `v2.55.0`, #1127 and #1150 in `v2.56.0`. #1150 retired the pass
  condition the template's rewritten label check no longer met, and
  reconciling it is what sent the reading to PLAYBOOK 1.6, where this project
  runs the older jq form. Its pass condition is correct for that form, so the
  filing's own subject is absent here; what is absent instead is any report
  of what the check read, which is #145. A filing that lands upstream leaves
  a downstream copy that no longer matches either the old text or the new.
- **Lesson:** a tag named in an issue body is a claim with a short life. #143
  was filed at 07:35 naming `v2.55.0` as the target, and `v2.56.0` already
  existed. Nothing in the issue could have said so, and the acceptance
  criteria were sound against the range they were written for. One `git tag
  --sort=-v:refname | head` before starting is what separates reading the
  body from trusting it.
- **Upstream:** one filing. braboj/solid-ai-templates#1181 against
  `templates/base/core/testing.md`: the check shipped with the
  unique-resource rule greps `tests/` for the class-counter pattern and
  requires no output, but matches inside a comment. It therefore reports the
  project that hit the defect, fixed it, and left the reasoning at the
  fixture, while a project that never had it passes. Found by running the
  check rather than reading it -- this repository's only hit is the comment
  in `test_server_connections.py` explaining why the fixture takes an
  OS-assigned port. #1058, #1076, #1077 and #1127 have closed since the
  previous entry, and #1150 with them; #1133, #1140, #1161 and #1181 are
  open.
- **Pending:** #144 and #145 are filed and unshipped, and they are the only
  open issues. The templates repository's own release procedure still wants
  the `v2.51.0` cut recorded as its own unmilestoned journal entry, which
  remains unwritten and is now five tags behind.

## 2026-08-28 — Bump the pin, declare the paths (midday)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Bumped the pin to `v2.57.0` and reconciled the startup block.** The
    first range in three to change the resolved chain rather than only the
    text inside it: `templates/manifest.yaml` wires `base-python` and
    `base-cli` into `stack-python-lib`, so
    `templates/base/language/python.md` and `templates/base/core/cli.md`
    govern this repository for the first time. Verified three ways, since a
    block edit that happens to satisfy the guard proves nothing on its own:
    the check passes at `v2.56.0`, fails at `v2.57.0` naming exactly those
    two files, and passes again once the block names them. Most of the range
    is relocation rather than new rules -- the 21 lines out of `quality.md`
    are the `eslint-plugin-sonarjs` table and the complexity bullet
    delegating its tool binding, and the rows dropped from
    `python-lib.md`'s gate table are the same bindings restated in
    `base-python`. Separating the two is what kept the already-satisfied
    tool bindings, lock rules and sdist anchoring from being filed as gaps.
  - **Declared the off-limits paths, and added one the default set misses.**
    `git.md` requires the context file to carry the section and `CLAUDE.md`
    had none. The default list cuts down to `.github/workflows/` here, since
    this project has no auth, billing, migrations or `.env`. The list adds
    `docs/solid-ai-templates`: a submodule pointer is a one-line diff that
    replaces every rule the project binds, with the suite, the linters and
    the diff itself reporting nothing about it. That is the section's own
    criterion, and the default list misses it because every member there
    earns its place by what it executes. ADR-023 carries the reasoning and
    why `pyproject.toml` stays off. The check reads the declared list out of
    `CLAUDE.md` rather than restating it, and lives in PLAYBOOK 1.3 rather
    than section 3 because a hit is an escalation trigger and a gate would be
    muted within a week.
  - **Adopted the template's label check instead of extending the local
    one.** PLAYBOOK 1.6 ran a `jq` form whose whole output was the offender
    list, so an authentication failure, a wrong repository context and full
    compliance all printed `[]`, and a hardcoded limit truncated in silence.
    The Python form upstream ships closes all four and is the copy upstream
    maintains, which is the argument that settled it: a local variant means
    every fix has to be re-derived here rather than arriving with the pin.
    Negative-controlled against planted input rather than by mislabelling a
    real issue -- a missing type label, a missing priority label, two type
    labels, an empty listing and a listing at the limit are each flagged, and
    a well-formed issue is not.
- **PRs merged:** #151, #152 and #153.
- **Issues closed/created:** #148, #144 and #145 closed by the pull requests
  that carry them, and the closure list was read by `closedAt` afterwards
  rather than trusted. #149 and #150 created while reconciling the pin, filed
  rather than absorbed into it, and both open. Upstream, filed
  braboj/solid-ai-templates#1204.
- **Lesson:** `git add -A` stages a submodule pointer left over from another
  branch. The working tree still held `v2.57.0` from the pin branch, so the
  off-limits commit carried a pointer bump it had nothing to do with -- and
  the path it contaminated is the one that commit exists to declare. What let
  it through is the ordering: the check had been run before committing, when
  `origin/main...HEAD` compared nothing and printed the same silence a clean
  branch prints. The staleness rule already says to compare after the edit;
  this is that rule reaching a diff-reading check rather than a regenerated
  artifact.
- **Lesson:** a document gate cannot see a file that is not staged, and the
  window where that matters is the one where a new document is written.
  ADR-023 shipped with an 82-column title. The width gate passed before the
  commit, having enumerated through `git ls-files` and never read the record
  under review, then failed the moment the file was tracked. ADR-022 states
  this gap and declined to close it; this is the first time it has cost
  anything, and the cost was one follow-up commit because force-push is
  denied.
- **Lesson:** a poll that hides its own errors reports silence as success.
  Waiting on the first pull request's checks ran 37 attempts printing "no
  checks reported yet" while all eleven were passing, because `python` is not
  on `PATH` in this shell and the loop routed the failure to `2>/dev/null`
  with a fallback of zero. The previous entry recorded the same shape one
  level down, in a condition that was vacuously true over an empty array.
  Here the poll itself was the blind check, and the tell was available
  throughout: eleven attempts of nothing on a repository whose CI finishes in
  under a minute is not a slow queue.
- **Lesson:** an upstream reference written before the filing names a number
  that already belongs to something else. ADR-023 was drafted citing
  `#1194`, which was taken by an unrelated issue upstream, so the placeholder
  would have resolved rather than 404ed and pointed a reader at the wrong
  thread. File first, then cite.
- **Upstream:** one filing. braboj/solid-ai-templates#1204 against
  `templates/base/core/git.md`: the off-limits default set assembles its
  members from paths whose danger is what runs from them, so a path whose
  danger is what it *governs* does not suggest itself -- and the hybrid model
  this repository recommends puts exactly such a path in every consuming
  project. #1133, #1140, #1161 and #1181 have all closed since the previous
  entry; #1204 is the only one open.
- **Pending:** #149 and #150 are filed and unshipped, and they are the only
  open issues. Upstream cut `v2.58.0` during this session, so the pin is one
  tag behind again and no issue names that bump yet. The templates
  repository's own release procedure still wants the `v2.51.0` cut recorded
  as its own unmilestoned journal entry, which remains unwritten and is now
  seven tags behind.

## 2026-08-28 — Finish the audit (midday, continued)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Named the stray submodule pointer in CLAUDE.md 2.1.** `git add -A`
    stages a pointer left at another branch's revision, which is a standing
    hazard here rather than a one-off: this repository carries a submodule
    that legitimately sits at different revisions on different branches, so
    every branch switch leaves the working tree holding a pointer the new
    branch does not record. Placed against the doc-placement tree rather than
    defaulted -- it is not a code invariant, weighs no alternatives, and is
    not user-facing setup, but it fires on every commit.
- **PRs merged:** #155.
- **Issues closed/created:** none either way. Upstream, filed
  braboj/solid-ai-templates#1211 and #1212.
- **Correction:** the previous entry's Upstream line states that #1204 is the
  only open filing. Two more were filed after that entry merged, so the count
  was accurate when written and is not now. Open upstream: #1204, #1211 and
  #1212.
- **Lesson:** the end-of-session audit writes the journal at item 4 and
  produces new work at items 5 through 11, so an entry written in checklist
  order cannot name the pull requests the later items open or the issues they
  file. Every one of its **PRs merged**, **Issues closed/created** and
  **Upstream** fields is incomplete by construction, and the rule that an
  entry's account is fixed forbids repairing them in place. The correction is
  a second entry for one session, which reads as two sessions to the next
  agent -- the opposite of the continuity the document exists for. Filed as
  #1212; until it lands, write the entry last and number it fourth.
- **Upstream:** two filings, both from this session's own defects.
  braboj/solid-ai-templates#1211 against `templates/base/core/git.md`: the
  off-limits check compares `origin/main...HEAD`, so a run against uncommitted
  work reports zero, and the pass condition names two causes for a zero
  without naming the one a reader will actually hit. That is the
  staleness rule's run-it-after-the-edit instruction, which the same file
  already states for regenerated artifacts and not for this check.
  braboj/solid-ai-templates#1212 against
  `templates/base/workflow/scope.md`, described in the lesson above.
- **Pending:** #149 and #150 remain the only open issues here. The pin is one
  tag behind `v2.58.0` with no issue naming that bump. The templates
  repository's own `v2.51.0` journal entry is still unwritten.

## 2026-08-28 — Close the wrap (midday, third)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Made PLAYBOOK 4.1 resolve the bump target rather than accept it.** The
    section said to pin a released tag and never a branch tip, which a stale
    released tag satisfies, and the procedure went from `fetch --tags`
    straight to `checkout <tag>` -- so the tag name arrived from the issue
    asking for the bump. One command between the two is the fix. The failure
    is not that the cited tag is absent; it resolves, it checks out, and
    everything the body says about it is true. It is simply no longer the
    newest, and existence is the wrong predicate for that.
- **PRs merged:** #158.
- **Issues closed/created:** none closed. #157 created, naming the `v2.59.0`
  bump with the range already read: the manifest is untouched so the chain
  does not move, `quality.md` gains 132 lines across five new sections with no
  deletions, and nothing in the range mentions the character set. Upstream,
  filed braboj/solid-ai-templates#1215.
- **Correction:** the previous entry's Pending line states that the pin is one
  tag behind `v2.58.0` and that no issue names that bump. Both halves have
  since gone false -- `v2.59.0` was cut, and #157 names it. The count in a
  Pending line is a claim with the same short life as a tag in an issue body,
  which is the session's own lesson arriving one level up.
- **Lesson:** a stale version identifier passes every check written for a
  wrong one. `review.md` tells an agent to verify anything an issue cites as
  existing, and a superseded tag satisfies it: the three shapes it enumerates
  -- narrower, wider and wrong as filed -- all describe an issue whose content
  is off, while this one's content is correct and its target has moved. The
  cost lands on acceptance criteria written against the narrower range, so it
  surfaces after the work is scoped rather than before. Filed as #1215.
- **Lesson:** three journal entries for one session is what the audit's
  ordering costs, not what the session's shape justifies. Each was written at
  item 4 and each was falsified by items 5 through 11 of the same run, so each
  correction is itself a record that needed correcting. #1212 proposes moving
  the entry to the end; until it lands, the practice here is to write it last
  and leave it numbered fourth, which is what this entry does.
- **Upstream:** one filing. braboj/solid-ai-templates#1215 against
  `templates/base/core/review.md`: a fourth shape for the verification step,
  where the version an issue names was the newest when written and is not now.
  The window is short and the cadence is what makes it likely -- an upstream
  that tags often outruns any issue describing a bump to it. Open upstream:
  #1204, #1211, #1212 and #1215.
- **Pending:** #149, #150 and #157 are open here and none is blocked. The
  templates repository's own `v2.51.0` cut is still unrecorded as its own
  unmilestoned journal entry, and is now eight tags behind; that is work in
  that repository rather than a filing from this one.

## 2026-08-28 — Read the range, file what it finds (afternoon)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Moved the templates pin to `v2.59.0` and read the range against the
    tree.** 462 insertions and 8 deletions across nine template files, seven
    of them in this project's chain. `templates/manifest.yaml` is untouched,
    so the chain does not move and the startup block needed no edit -- run at
    the new pin rather than inferred from the unchanged manifest, which is the
    difference the acceptance criteria asked for.
  - **Carried the divergence position forward in PLAYBOOK 4.1.** ADR-014 stays
    the one record standing apart, and the worked example for "a named file is
    not a moved rule" now runs off this range rather than `v2.57.0`'s: 132
    lines added to `quality.md`, none deleted, all three hunks landing ahead of
    the Code style section the record bounds.
- **PRs merged:** #164.
- **Issues closed/created:** #157 closed. Four created from the reading --
  #160 on the control's unmargined floor, #161 on the procedure-step audit,
  #162 on a test edit that weakens the suite, #163 on a trigger with no
  detector. None absorbed into the bump.
- **Correction:** the previous entry's Upstream line lists #1204, #1211, #1212
  and #1215 as open upstream. Three of the four closed as completed the same
  day. #1212 is the one that matters here -- it moves the journal entry to the
  end of the end-of-session audit -- and `scope.md` did not move in this
  range, so the change landed after `v2.59.0` and arrives at the next bump.
  The practice of writing the entry last and leaving it numbered fourth is
  settled upstream and not yet inherited.
- **Lesson:** a control is a member of the family it controls, for the purpose
  of every rule that family follows. Six document gates each size their
  coverage floor from a measurement, classify the corpus, and sit at roughly
  half where it churns. The seventh module, the one that proves the six are
  not blind, sets its floor at the measured six with no margin and no corpus
  classification. ADR-022 states the sizing rule in the words the template now
  uses, and its scope is the six -- so the control escaped the rule the record
  exists to impose, by not being one of the things the record is about. Filed
  as #160 here and as braboj/solid-ai-templates#1225 upstream, because a
  reader applying the template as written lands in the same place.
- **Lesson:** read a range for what it says about this tree, not only for what
  it says. Two of this range's edits were made for a shape this repository
  already has. The unique-resource check gained a `^[^#]*` prefix so it stops
  flagging a comment that discusses the pattern rather than using it, and the
  only such comment anywhere is at `tests/test_server_connections.py:52`,
  beside the fixture that fixed the defect. Running the old form and the
  shipped form side by side took one command and turned an abstract edit into
  a confirmed clean result across 136 files. The same command run only in the
  shipped form would have printed nothing and proved nothing.
- **Upstream:** one filing. braboj/solid-ai-templates#1225 against
  `templates/base/core/testing.md`: `testing-negative-assertion-coverage`
  gained both the floor-sizing clause and the control clauses in this range,
  and they do not meet -- nothing says the control's own discovery count is a
  floor taking the same margin. It is the floor most likely to be set at the
  measured count, because the author is counting members they have just
  written. Open upstream: #1215 and #1225.
- **Pending:** nothing blocked. Six issues open here, none milestoned: #149,
  #150 and the four filed today. #160 is the smallest and has its evidence
  attached; #161 is an audit rather than a fix. The templates repository's own
  `v2.51.0` cut is still unrecorded as its own journal entry, now ten tags
  behind, and remains work in that repository rather than a filing from this
  one.

## 2026-08-28 — Clear the backlog, surface the debt (evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Moved the pin to `v2.60.0` and carried the divergence position.** Three
    of the four moved files sit in this project's chain. `quality.md` and
    `docs.md` did not move, so no record on PLAYBOOK 4.1's list could have
    been touched. ADR-023 joined that list in the adopted state rather than
    the divergent one: `git.md` took the templates-submodule pointer into the
    off-limits default set with the reasoning the record gave, so
    `CLAUDE.md` 2.5's second entry is now the template's own default.
  - **Retired both ruff freeze slices.** The `tests/` half was 39 entries and
    77 findings; the `scripts/` half arrived at two entries because ADR-024
    had deleted five of its seven files first. The freeze now holds `src/`
    only -- 8 entries, 734 findings -- plus the `tests/**` docstring rule,
    which is a convention rather than a freeze.
  - **ADR-024 settled what `base-cli` reaches and emptied `scripts/`.** Eight
    files there, one reachable from anything. Three of the seven modules were
    not runnable as written: methods orphaned from their class, a class whose
    every method is `pass`, two helpers nothing imports. A stray text file was
    a stale draft of the `packets.py` docstring disagreeing with the shipped
    text about the PDU-ID range. Six deleted.
  - **Triaged 44 in-source TODOs to zero.** Seven filed with verified
    evidence, the rest deleted with the verdict recorded. One was false and
    one was wrong in the other direction.
  - **Adopted three rules the ranges added.** Check timing across PLAYBOOK 1.3,
    3.9 and 3.11; the test-edit boundary in 1.3 and `CLAUDE.md` 3; the
    revisit-trigger detector in 4.2 and 1.6.
- **PRs merged:** #179, #181, #182, #184, #185, #186, #188, #189, #197, #198,
  #199.
- **Issues closed/created:** ten closed -- #150, #160, #162, #163, #166, #168,
  #169, #174, #176, and #183 closed as deferred per ADR-016. Twenty-three
  created, #167 through #200.
- **Correction:** the entry counts this session first put on #168 and #170
  were wrong -- 24 named `tests/` entries where the table holds 39, and 23
  `src/` entries where it holds 8. Both bodies were corrected before any work
  ran off them, and a comment on #168 records the correction. The finding
  counts, which were measured rather than read, were right.
- **Lesson:** a check that reads git's index or git's history is evidence about
  whichever tree it was pointed at, and the natural moment to run one is
  before the change is in that tree. It happened twice. The off-limits check
  reported `files changed: 0` against the uncommitted pin bump and named the
  path correctly once committed; the document gates passed against an unstaged
  ADR-024 and failed in CI. `CLAUDE.md` 3 already states the index half and
  the second failure still happened, so the fix that worked was mechanical
  rather than a rule: stage first, then run. ADR-025 was written under that
  order and its two findings surfaced locally.
- **Lesson:** the freeze was camouflage as much as a ratchet. Six dead files
  and 100 findings survived in `scripts/` because every gate that would have
  seen them was silent -- the `src/` layout keeps the directory out of the
  wheel, no test imports it, and all seven modules sat inside
  `per-file-ignores`. Nothing was wrong with any single gate. The union of
  their blind spots was a directory.
- **Lesson:** auditing a backlog is net-generative and that is not a defect.
  Ten issues closed and twenty-three filed, every one carrying a measurement
  rather than a suspicion. The seven inherited issues were process work; under
  them sat a lock nothing acquires whose test cannot see it (#190), a bare
  `raise Exception` in the server (#180), and a transport that logs nothing so
  a swallowed failure looks like silence (#195). Say so early rather than
  reporting a shrinking number that is not shrinking.
- **Upstream:** six filings, five captured on the records at decision time.
  braboj/solid-ai-templates#1230 on `SECURITY.md` having two required facts
  and no structure where the README gets nine sections; #1231 on no rule
  shaping a changelog entry; #1238 on `cli.md` and `examples.md` wanting
  opposite things from the same file; #1239 on `scripts/` being named the
  home for probes a probe rule says never land; #1240 on the per-file freeze
  being specified where the site-local suppression beside it is not; #1241 on
  a sixth shape for the filed-issue list, where an issue's classification does
  not cover every member. Open upstream: #1215, #1225 and all six.
- **Pending:** nothing blocked. Nineteen issues open, none milestoned. #200
  bumps the pin to `v2.61.0`, cut after this session's bump and moving
  `quality.md`, which puts ADR-014 back on the reading list. The two spikes
  need the owner rather than the agent: #167 on the comment convention, where
  the owner has stated the preference but not the ceiling, and #173 on the
  simulator rename, which is a public API break. #172 and #170 are the two
  epics and the largest remaining work.

## 2026-08-28 — Ship the pin, cut the release (late)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Moved the pin to `v2.61.0` and read the range.** Three chain files
    moved. `quality.md` did too, so PLAYBOOK 4.1's cheap short-circuit did not
    apply and the diff was read against ADR-014's own subject — both hunks
    land below the character-set rules, which the range leaves untouched, so
    the record is unrefuted a second time and still stands the stricter way
    round. Three of the rules the range adds were already satisfied here and
    were named as such rather than assumed: the control floor's margin, the
    absence of backslash shorthands in embedded checks, and the gate control
    planting a behavioural break. One was adopted, into PLAYBOOK 3.10, where
    "run it both ways" had covered only the case where a fix is observable.
  - **Released `v0.3.1`.** A patch, because nothing in the library's behaviour
    changed since `v0.3.0`: the only diff under `src/` is 57 deleted lines,
    every one a TODO comment or a commented-out log line, with no additions.
    `release.yml` attached the wheel, the sdist and the SBOM in 21 seconds.
    No rehearsal was owed — the workflow is byte-identical to the one that
    produced `v0.3.0` and has three prior executions.
  - **The `Unreleased` block was two entries deep against thirty-seven
    commits.** Cutting it as it stood would have published a `[0.3.1]` entry
    naming 2 of 37 changes. Four notable omissions were added at release time:
    the document-gate coverage control, both retired ruff freeze slices, the
    TODO triage and the emptied `scripts/`.
  - **The 360 audit was skipped deliberately**, on the owner's call, and the
    release pull request records that this is the fourth consecutive release
    to skip it. `v0.2.0`, `v0.2.1` and `v0.3.0` each shipped without one and
    nothing reported it.
- **PRs merged:** #202, #205.
- **Issues closed/created:** one closed — #200. Five created here — #203, #204,
  #206, #207 and #208 — and two upstream.
- **Lesson:** a count far larger than expected is a defect in the check before
  it is a backlog. The range's new comment-layout check reported 209 findings
  on this tree; 164 were one false-positive class, a comment opening a `try:`
  or a bracketed literal, where the comment sits correctly above what it
  documents. Working that list would have been 164 edits to well-formed code.
  The rule that says triage the check first is the only thing standing between
  the two readings, and it turned a backlog into an upstream filing.
- **Lesson:** a plan-time placement is a hypothesis, and it failed twice in one
  session. The behavioural-break rule was planned into a PLAYBOOK section that
  does not exist, and the rule turned out already satisfied. The comment-layout
  findings were planned onto #167, which settles comment density rather than
  layout and whose six acceptance criteria do not reach it; they went to their
  own issue instead of widening a spike that already needs the owner.
- **Lesson:** a rule's stated reason rots independently of the rule it
  justifies. The changelog gate's docstring and PLAYBOOK 5 step 4 both justify
  cutting the entry before the tag by saying it ships inside the tagged sdist.
  It never has — the include list carries four paths and `CHANGELOG.md` is not
  among them. The conclusion survives, because the tag's own tree carries the
  entry; only the named artifact is wrong, and it is falsifiable in one
  command, which is how a step loses its justification and then itself.
- **Lesson:** the working directory persists across shell calls, and a `cd`
  into the submodule made a later diagnostic read the templates repository's
  journal and issue count as though they were this project's. The numbers were
  plausible — 55 open issues, a journal with dated entries — which is what
  makes the failure worth recording rather than the error itself.
- **Upstream:** two filings, both landed rather than named.
  braboj/solid-ai-templates#1245 on the comment-layout check flagging a comment
  that opens a block or a bracketed literal, carrying the 164/19 split and a
  fix tested against this tree; #1254 on the release procedure cutting an
  accumulator nothing checked was maintained, which is the generic form of the
  two-entries-against-thirty-seven-commits finding.
- **Pending:** nothing blocked. Twenty-four issues open, none milestoned. #208
  bumps the pin to `v2.62.0`, cut after this session's bump and moving
  `git.md`, which puts ADR-023 on the reading list rather than the four records
  the cheap short-circuit covers. #206 carries the stale 360 audit and the
  uncounted skips. The three library defects — #190, #180 and #193 — remain the
  sharpest items and none of them was touched.

## 2026-08-28 — Fix the defects, ship v0.4.0 (night)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Fixed the three library defects that three sessions had shipped process
    work around.** #193: a close that raised escaped the client teardown and
    left `self.sock` set, so the client held a socket it had already given up
    on. #180: the server's manual-accept refusal raised the base `Exception`,
    which a caller could not catch without catching everything. #190: the
    stream sender's lock was created and never acquired.
  - **#190 turned out to be two defects.** Reading the class rather than the
    issue found that *neither* component ever read its stop event, so `stop()`
    was a no-op on both. ADR-026 records the decision to make the contract real
    rather than withdraw it, and the three alternatives weighed.
  - **Released `v0.4.0`.** Minor rather than patch, because `ModbusModeError`
    is a new exported name and new public API is minor however small the class.
    125 insertions across five source files -- the first release in four whose
    changelog names actual library fixes.
  - **The changelog block was current when it was cut.** Four entries, one per
    fix, each added on the pull request that made the change. The previous
    release found the opposite and reconstructed the omissions by hand.
- **PRs merged:** #211, #212, #213, #214.
- **Issues closed/created:** three closed -- #193, #180 and #190. None created
  here; one filed upstream.
- **Lesson:** a test named for a defect can be blind to the defect beside it.
  `test_stream_locks.py` was written for a lock bound without parentheses and
  asserts four things: that each component holds a working lock, that the two
  are not shared, and that both are the same type. Every one is a property of
  the lock object. All four passed against a sender that never acquired its
  lock, and coverage reported the lines as covered, by a witness that could not
  disagree. The module named the right subject and measured the wrong property.
- **Lesson:** one inert primitive is grounds to grep for its siblings. The
  unacquired lock prompted a search for `is_set` and `wait(` across the module,
  which returned nothing at all and exposed both dead stop events. Same author,
  same file, same mistake one field over -- which is the shape the
  rejected-mechanism sweep describes, applied to a field rather than a
  construct.
- **Lesson:** an issue's acceptance criteria are evidence about its filing
  date. #180 said its count "is part of the work rather than known now" -- it
  was one, and the checker said so in a second once the freeze was bypassed.
  It also said the change was breaking for a caller catching the current type,
  which is wrong: the new class subclasses `Exception`. Both were checked
  rather than implemented.
- **Lesson:** a release can be empty in a way the commit count hides. The
  session opened with a request to cut the next release, and one commit had
  landed since `v0.3.1`. Diffing the paths that actually reach the artifacts --
  `src/`, and `src/ tests/ README.md LICENSE` for the sdist -- showed both
  empty, so the tag would have published byte-identical artifacts and a
  changelog entry with nothing under it. The commit count was 1, which reads
  like something.
- **Upstream:** one filing. braboj/solid-ai-templates#1267 on a test that a
  guard exists not being a test that the guard is used. The base chain says to
  exercise a lock rather than inspect it, which asks whether the guard works;
  nothing asks whether the code under test takes it, and the two are
  indistinguishable from a suite and from a coverage report.
- **Pending:** nothing blocked. Twenty-two issues open, none milestoned. The
  pin is now two releases behind at `v2.61.0` -- `v2.63.0` is out, and #208
  carries the bump with a comment recording that its target has moved a third
  time. #206 carries the 360 audit, which this release skipped for the fifth
  consecutive time; the skip is recorded in the release pull request, and the
  issue's second half exists so it stops depending on someone remembering to
  write it down.

## 2026-08-29 -- Audit the tree, gate the step, ship v0.4.1

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Ran the second 360-degree audit, nine dimensions, and graded the tree
    B+.** The first report graded it C- with Security as the bottleneck and
    three critical findings. All three are closed: secret scanning, push
    protection and Dependabot are enabled, CodeQL and bandit both run, every
    action is pinned to a commit SHA, and `main` is protected with the
    administrator exemption off. Ten findings, none critical.
  - **Gated the step four releases had skipped.** The newest report in
    `docs/audits/` must postdate the release before the one being cut. It
    reads the changelog's dated entries rather than `git tag`, because the CI
    checkout is shallow and fetches none -- a tag-based rule would have found
    nothing and reported a clean tree from it. ADR-027 carries the choice.
  - **A skip is now a document rather than a silence.** A dated `-skipped`
    record naming the release and the reason clears the same gate. Declining
    the audit was always legitimate; doing it four times with three leaving no
    trace was the defect.
  - **Released `v0.4.1`.** Patch rather than minor: no library code changed,
    and `v0.3.1` set the precedent for a release whose content is a gate.
  - **Grouped the vendor specifications under `docs/specs/`.** #175. The
    fourth PDF was on no list in `CLAUDE.md`; its cover page identifies it as
    the Modicon Modbus Protocol Reference Guide PI-MBUS-300 Rev J, so it is
    declared rather than deleted. ADR-028 records the layout and that no
    `docs/` index is wanted.
- **PRs merged:** #218, #219, #220.
- **Issues closed/created:** two closed -- #206 and #175. Two created -- #216
  and #217, both audit findings. #196 was corrected rather than refiled, and
  #172's gate count was corrected from 13 to 14 by the gate this session
  added.
- **Lesson:** a count carried between two audits is not a comparison unless
  the method is carried with it. The first report counted 510 wire vectors by
  scanning for byte-string escapes. The same pattern returns 15812 today, not
  because the suite grew thirtyfold but because it also matches every hex
  escape inside an ordinary string. Parsing each module and counting bytes
  constants gives 118. Three numbers, one tree, and only the third is
  reproducible -- which is why the new report states its method beside the
  figure and says the two are not comparable rather than reporting growth.
- **Lesson:** an edit that matched nothing and a check that never fired print
  the same thing. Proving the moved path in the line-endings control fixture
  was load-bearing meant planting a violation in it. The first attempt used
  `sed`, whose pattern did not match, and the run reported six passing tests
  -- which reads exactly like a control that fired and found the tree clean.
  Confirming the plant by diff before reading the run is the whole check, and
  it cost one command.
- **Lesson:** a remedy message can promise an escape the gate does not have.
  The first draft told an operator that overriding the audit gate "takes an
  argument", which was false -- nothing accepted one, and the only way past it
  was to write an audit. The message was written before the escape existed and
  read as though it described one. Either build the escape or describe what is
  actually there; a failure message is read at the worst moment and is not the
  place to be aspirational.
- **Lesson:** where a gate reads its input from is a decision a later reader
  will reverse. Tags are the obvious source for "the date of the last release"
  and the reasoning against them is invisible from the code: the rule would
  keep passing, having measured nothing. That is why it is an ADR rather than
  a comment -- a comment explains the line it sits on, and this needed to
  survive someone deleting the line.
- **Upstream:** no filings. ADR-027 and ADR-028 each record `none` with the
  reason and a revisit trigger, judged at decision time rather than deferred
  to the wrap. Both generalize -- a gate reading a project's own dated record
  where a shallow checkout hides the tags, and third-party reference material
  living apart from the documents a project authors -- and one project wanting
  each once is not evidence either does.
- **Pending:** nothing blocked. Twenty-three issues open, none milestoned. The
  pin is now three releases behind at `v2.61.0`, with `v2.64.0` out; #208
  carries the bump and needs no edit, because its body already says to resolve
  the target from the tag listing rather than from itself. An empty
  `docs/design/` directory sits untracked in the working tree; git does not
  record it, and it was not created by this session's work.

## 2026-08-29 -- Markdown leaves the ASCII rule (evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Lifted the printable-ASCII rule off Markdown.** ADR-029 supersedes
    ADR-014. The templates narrowed their own ASCII rule to identifiers at
    `v2.46.0` and say documentation carries no charset restriction; the docs
    template blesses plain ASCII and Unicode box-drawing equally for diagrams.
    The local rule forbade a form the rule it extends permits, and charged
    that to every document.
  - **Kept control characters failing in both halves.** This was the half
    worth arguing about. `test_line_endings.py` names `test_source_is_ascii.py`
    in its own remedy text as the thing that finds a stray NUL, and a NUL is
    what made git store this journal as binary with 1127 CRLF endings while
    that gate read clean. Dropping Markdown from the character gate entirely
    was the obvious reading of the request and would have left that remedy
    pointing at a check that no longer looks.
  - **Reviewed the architecture direction note against the tree and filed
    #224.** Six findings. The one that matters: #196 asks for field-range
    validation, the note's rule 5 says serialization must not imply
    validation, and implementing #196 as filed would remove the ability to
    build malformed frames deliberately -- the differentiator. Also: the
    roadmap assigns work to `0.4`, which shipped without it, and twelve of the
    thirteen function codes it lists as a target already exist.
  - **Committed the note as written under `docs/design/`.** ADR-030 gives the
    directory its record and the rule that keeps a note from reading as a
    decision: it binds nothing, and adopting part of one takes a decision
    record rather than an edit to the note. Its two known errors are tracked
    in #224 rather than corrected in place.
- **PRs merged:** #223, #225.
- **Issues closed/created:** #222 created and closed by #223. #224 created and
  open -- the note review, which #225 deliberately does not close.
- **Lesson:** the project's own record of the last time a question was asked
  is worth more than the upstream diff that appears to answer it. The first
  reading here was that upstream had moved and the local rule was stale
  debt. `PLAYBOOK.md` 4.1 recorded that a prior session had already
  reconciled exactly this record twice and chosen to stay stricter. Same
  evidence, opposite conclusion, and the difference was one section of a
  document written for that purpose. A reconciliation note pays for itself
  the first time it stops a session from "closing a gap" that is a decision.
- **Lesson:** a check's remedy text can name another check as the thing that
  finds the underlying cause, and narrowing the named check falsifies that
  remedy silently. Nothing fails, because the remedy is prose in a failure
  message no passing run prints. Grep the suite for a module's own name
  before relaxing what it checks.
- **Upstream:** one filing. ADR-029 records `none` -- it converges on the
  position the templates already hold, so there is nothing to contribute.
  ADR-030 records `none` with a revisit trigger. The remedy-text lesson above
  generalizes and was filed as braboj/solid-ai-templates#1290 against
  `templates/base/core/testing.md`.
- **Pending:** nothing blocked. The pin is now four releases behind at
  `v2.61.0`, with `v2.65.0` out; #208 carries the bump, and the submodule is
  an off-limits path needing a proposal before it moves. #224 is the live
  thread: #196 should not be implemented before it is settled.

## 2026-08-30 -- Constraints move onto the packet

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **ADR-031 settles how specification constraints enter the library**, which
    is #224 finding 1 and the mechanism half of #196. Neither open proposal as
    filed: not a per-call check, not STRICT/PERMISSIVE/RAW. Every packet
    component declares its own constraints, `violations()` returns named
    findings, `validate()` raises, and `serialize()` gains no parameter so the
    design note's rule 5 holds by construction.
  - **The record reversed itself four times under review, each time on a
    question rather than a preference.** A central table lost to per-class
    declaration because FC15 ties `quantity`, `byte_count` and `values`
    together and no per-field lookup holds that. The docstring stopped
    repeating the bound, so the drift guard an earlier revision owed is not
    needed. `validate()` joined `violations()` because `validate_crc` and
    `validate_mbap_length` already raise. Scope widened past PDU fields once
    the protocol identifier and the slave address turned out to be unchecked.
  - **PLAYBOOK 1.7 records how to write an issue or pull request body**, after
    three tickets filed this session came out accurate and unreadable. Five
    habits, three tells, and a before-and-after from #228. `CLAUDE.md` 3
    carries the one-line pointer. Deliberately ungated -- a sentence-length
    check passes prose nobody can follow.
- **PRs merged:** none. #227 (ADR-031, eight commits) and #230 (PLAYBOOK 1.7)
  are both open, both green, both awaiting the owner.
- **Issues closed/created:** created #228, #229, #231 and #232; none closed.
  #224 gained finding 7, on the serial tier the note describes and the tree
  lacks end to end. #196 carries three correcting comments.
- **Lesson:** a number copied from a ticket body is a claim, not a fact. The
  record cited `0x07D0` as the FC3 quantity cap, carried from #196 without
  checking; that is the coil cap, and registers cap at 125. The correction is
  what exposed the argument the record now turns on -- FC1 and FC3 both
  declare `">BHH"` precisely because the format is not where the bound lives.
  The error was load-bearing in the right direction only by luck.
- **Lesson:** a ticket filed from a plausible reading can contradict a finding
  written hours earlier. #231 argued RTU needs a direction-agnostic packet for
  sniffing. Probing showed `ModbusTcpPacket` is parse-agnostic rather than
  direction-agnostic, a wrong-direction parse raises rather than misparsing,
  and unknown function codes already degrade to the generic PDU. #224 finding
  6, written the same day, already said that capability class traces to no
  requirement. The rewrite says what the ticket actually is: the codec slice
  of a serial tier that does not exist.
- **Lesson:** a polling loop that cannot evaluate its condition is
  indistinguishable from one whose condition never fires. Four CI watchers ran
  to timeout in silence because `jq` is not installed here; `gh --jq` is a
  built-in and had been working the whole time. Nothing in the output said so.
- **Lesson:** `ai-workflow-pwd-on-negative` fired during this very audit. A
  `cd` into the templates submodule persisted, and the next journal check
  reported the newest entry as 2026-08-28 and no commits ahead of main. Both
  readings were correct for where the shell was standing.
- **Upstream:** two filings. braboj/solid-ai-templates#1293 argues that
  replacing a boolean flag with an enum is wrong where the caller needs the
  name of the rule that broke, and was updated to carry the findings-plus-guard
  pair the record landed on. braboj/solid-ai-templates#1301 proposes that
  `base-issues` govern the prose inside a ticket, not only which sections it
  has -- an agent fills the sections correctly and still writes an opaque body.
- **Pending:** three decisions, all the owner's. Whether ADR-031 merges as
  `Accepted` or `Proposed`; whether #227 and #230 merge, and in which order,
  since the second will want `gh pr update-branch`; and whether
  `templates/base/workflow/communication.md` joins the startup block. The last
  is blocked rather than unanswered -- `tests/test_startup_block_resolves.py`
  derives the block from the manifest plus a hand-declared set of exactly two
  files, so a third needs that set widened and ADR-008 amended. The pin stays
  four releases behind at `v2.61.0`; #208 carries it.

## 2026-08-31 -- Groom the backlog, ship v0.4.2

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Cut v0.4.2**, a patch release carrying `docs/design/`, the Markdown
    charset change and the `docs/specs/` move. The library code is unchanged;
    the only source edit is the version literal. The wheel, sdist and SBOM are
    attached to the tag and the README's install URL resolves to the published
    wheel.
  - **Declined the 360-degree audit and recorded the decision.**
    `docs/audits/2026-08-31-360-skipped.md` names the release and the reason:
    the 2026-08-29 report is two days old, graded B+ with zero critical
    findings, and the five commits since are documentation. The record states
    what it does not claim -- the ten findings that report raised still stand
    -- and commits the next release to running the audit rather than declining
    twice.
  - **Held three ready pull requests until after the tag**, per PLAYBOOK 5.
    #227, #233 and #230 were all green and mergeable before the release
    branch existed. Merging any of them first would have shipped it inside
    v0.4.2 with no changelog entry naming it, which is #217 and is still
    enforced by nothing but attention.
  - **Verified all 27 open issues against the tree and closed none.** Both P2
    codec bugs reproduce exactly as filed -- #228 still serializes the old
    value after a field is written, and #196 still emits a quantity one past
    the specification cap. Every other claim checked out too.
  - **Corrected four issue bodies whose measurements had decayed**, and left
    #204 and #173 alone where the drift was one site and a dozen lines.
- **PRs merged:** #234 (the release), then #227, #233 and #230 after the tag.
  #235 is open -- a one-line docstring rewrap, deliberately framed as
  declinable.
- **Issues closed/created:** none created, none closed. #208 retitled and
  rewritten, #203 recounted from eleven sites to nine, #171 and #172
  re-measured, #210 given a re-check comment.
- **Lesson:** an issue can anticipate one kind of decay and be undone by
  another. #208 says outright to resolve the target tag from the listing
  rather than from its body, because a named tag had been wrong twice before.
  What went stale was not the tag but the reasoning attached to it: the body
  argued the divergence re-read would be cheap because `quality.md` and
  `docs.md` had not moved, and that held at `v2.62.0` and fails at `v2.66.0`,
  where the two carry 389 changed lines and four decision records between
  them. The self-aware caveat covered the number and not the argument built
  on it.
- **Lesson:** a verifiable claim written into a dated record can be falsified
  by the very commit that ships it. The audit skip record said
  `git diff --stat v0.4.1..HEAD -- src/` reports nothing, which was true while
  the version bump sat unstaged and false the moment it was committed, because
  the release edits the version literal. Checking the claim before pushing
  cost one command; the alternative was a record refuted by its own commit on
  the day it was written.
- **Lesson:** a crude re-measurement disagreeing with a filed one is not
  evidence the filed one was wrong. A quick classifier split the test suite
  8/20/34 where #172 records 14/10/36. The classifier is the weaker
  instrument, so the correction says the totals moved and leaves the split to
  be re-derived when the layout decision needs it, rather than overwriting a
  considered number with a hastier one.
- **Lesson:** grooming that closes nothing is still grooming. Twenty-seven
  issues verified and twenty-seven still live says the backlog is real work
  rather than accumulated noise, which is the opposite of what a sweep
  usually finds and is worth knowing before the next planning pass.
- **Upstream:** one filing. braboj/solid-ai-templates#1314 against
  `templates/base/core/docs.md`: the falsified-by-its-own-commit lesson above
  generalizes past this project. A dated report asserting a command's output
  is a load-bearing claim whose truth can depend on whether the change
  carrying the report is committed yet, and neither half of the
  observations-versus-instructions split reaches it -- the claim was not
  made stale by the world moving, it was made false by the act of recording
  it. `quality-gates-check-timing` is the nearest neighbour and governs when
  a check runs rather than what a document asserts.
- **Pending:** #235 awaits the owner and is fine to close. The pin is now five
  releases behind at `v2.61.0` with `v2.66.0` out, and #208 now carries the
  wider range and the expensive divergence step. The next release owes a real
  audit rather than a second skip.

## 2026-08-31 -- Merge the held work and the editor rulers (evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Merged #235**, the docstring rewrap the earlier entry left with the
    owner. Its body carried eight measured numbers and the base had moved
    under it, so the measurements were re-run before the merge rather than
    read. All eight held -- the intervening commit was the journal entry and
    touched no source.
  - **Added an 88-column ruler to the Python editor guides (#237)**, and
    repaired the sentence it falsified. `.editorconfig` described the ruler
    set as exactly two markers, the preferred width and ruff's ceiling, so a
    third made that description wrong. The sentence now names the two
    configured widths without counting the rulers drawn from them.
  - **Contributed the version-staleness finding to the open upstream issue
    rather than filing a second.** braboj/solid-ai-templates#1215 already
    covers a cited version going stale; what this session found is the
    measurement built on that version going stale with it, which is a comment
    on that issue rather than a near-duplicate of it.
- **PRs merged:** #235 and #237.
- **Issues closed/created:** none. The backlog stands at 27 open, unchanged
  from the grooming pass in the earlier entry.
- **Lesson:** a comment that enumerates a set is a claim about the set's size,
  and it goes stale the first time the set grows. `.editorconfig` said the
  rulers show ruff's ceiling "alongside the preferred width" -- true of two
  markers and false of three, falsified by a one-element edit in a different
  file. The repair is to stop enumerating rather than to update the count,
  because updating the count leaves the same defect waiting for the next
  ruler.
- **Lesson:** the guard an issue writes against its own decay can be narrower
  than the decay. #208 said outright to re-resolve its target tag from the
  listing, and that guard worked. What it did not cover was the measurement
  the body offered as a reason to skip the expensive step, which was scoped
  to the same range and went stale with it. A stale measurement that enlarges
  the work announces itself when the work is done; one that shrinks it is
  acted on and never revisited.
- **Upstream:** no new filing. The candidate above was added to
  braboj/solid-ai-templates#1215 as a comment, because that issue already
  proposes the row this finding extends and `base-issues-duplicate` wants
  exactly one ticket to survive. braboj/solid-ai-templates#1314, filed
  earlier today, is the session's one new issue.
- **Pending:** nothing blocked, and no pull request is open. The pin stays at
  `v2.61.0` with `v2.66.0` out; #208 carries it and the submodule is an
  off-limits path needing a proposal before it moves. The next release owes a
  real 360-degree audit rather than a second skip. The 88-column ruler has no
  recorded rationale beside it -- it matches neither configured width, and a
  line in `.vscode/settings.json` would close that.

## 2026-08-31 -- Loosen the audit gate, ship v0.4.3 (late evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Groomed the backlog against the tree and corrected seven bodies.** #210
    is the one that changed meaning rather than numbers. It was filed as an
    unidentified bind collision with a careful elimination list; a full suite
    run named the site in its traceback, and it is not a defect at all. Two
    `TestStartup` tests call `occupy_a_port()` and start a server on the port
    they just took, asserting the server reports the failure -- so the
    collision is the mechanism under test and the warning is a negative
    control announcing itself. Re-scoped from finding a binding site to
    stopping expected noise from burying a real one. The other six were
    measurement drift: #167's whole density table, #173's module sizes,
    #178's entry count plus a forward reference to an issue v0.4.2 closed,
    #192's line numbers, #204's file count and one of its two violations, and
    #229's internal call count.
  - **Loosened the release-audit gate to accept a same-day record (#239).**
    The comparison was strictly-later, and v0.4.2 had shipped that morning, so
    v0.4.3 could not be cut at all: no record can carry a date later than
    today. Declining did not help either, because a skip record carries the
    same date and failed the same comparison. ADR-032 records the reversal and
    what it gives up. ADR-027 keeps its other three decisions and is not
    marked superseded, since supersession is for a record wholly replaced.
  - **Cut v0.4.3 (#240)** with each pre-release check recorded rather than
    asserted, including the two that did not simply pass: 217 unreachable
    commits accounted for as squash and stash residue with one traced to its
    landed content, and a 360-degree audit declined for the second release
    running.
- **PRs merged:** #239, #240 and #241.
- **Issues closed/created:** none either way. The backlog stands at 27 open,
  unchanged across the whole day.
- **Lesson:** a gate can be correct, current, and impossible to satisfy. The
  audit rule was right about staleness and had simply never run on a day when
  two releases were wanted. Its strictness answered a real ambiguity -- a date
  carries no time, so an audit written before a release and one written after
  it read alike. What nobody checked was whether the refused set contained a
  state the project legitimately needs, and it did. A step an operator is
  invited to decline, with no form that clears the gate, is a worse failure
  than the ambiguity being guarded against.
- **Lesson:** an issue's diagnosis decays faster than its measurements. #210's
  eliminations were each sound and its conclusion was wrong, because pytest's
  attribution had moved to two tests whose entire purpose is to fail a bind.
  One suite run settled what the body had held open since 2026-08-28. The
  counts in the other six issues were the cheap half of grooming; re-running
  the diagnosis was the half that changed what the work is.
- **Lesson:** the record that warns about a thing is the one that gets
  overridden. The v0.4.2 skip record closed by saying the next release runs
  the audit rather than declining again, and the next release declined again.
  That is the owner's call and the procedure allows it. What it does not allow
  is taking it in silence, so the record gained a dated addendum superseding
  its own forward instruction and naming the cost -- three releases now rest
  on one report, against a trigger nothing watches.
- **Upstream:** two filings, both from the gate change.
  braboj/solid-ai-templates#1331 against `git.md`, that a currency gate
  comparing dates carrying no time must compare non-strictly or one granule
  becomes unreachable. braboj/solid-ai-templates#1332 against
  `quality-gates.md`, that a loosened gate pins the case it was loosened to
  admit, or the surviving diff reads as a typo the next reader reverts. Two
  further candidates were judged already covered upstream, by
  `docs-record-amendment` and by the rule against superseding a record to
  correct one claim.
- **Pending:** the 360 deferral is the open question and it is not recorded
  anywhere a release will meet it. The owner scheduled the next audit for the
  point the backlog reaches zero, which reads as a standing condition rather
  than a one-off, and PLAYBOOK 4.4 still says to run one before a release.
  Only the audit addendum carries the new position. Whether that is a
  procedure change belongs to the owner and was left unasked rather than
  guessed. The pin moved twice during the session and stands at `v2.61.0`
  with `v2.68.0` out; #208 carries it and the submodule stays off-limits. The
  88-column ruler still has no recorded rationale beside it.

## 2026-09-01 -- Ship v0.4.4, then measure where the effort went

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Cut v0.4.4 across nine pull requests**, closing #243, #232, #248, #207,
    #249, #246 and #247. The release changed zero lines of library behaviour:
    seventeen source lines, all docstrings and a version bump. Five of its
    seven items were corrections to statements the tree was making about
    itself -- a protocol id no frame may carry, a freeze count wrong by three,
    a reason naming an artifact that never held the thing, two coverage floors
    below their corpora, and an assertion a class never promised.
  - **Narrowed the audit gate to minor and major releases (ADR-033).** Two
    consecutive declines had left three releases resting on one report, and
    the position standing was a deferral to zero backlog that nothing watched.
    v0.4.4 is the first release cut under it, and the gate is silent rather
    than cleared by a record. Filed upstream as
    braboj/solid-ai-templates#1337.
  - **Gated the docstring examples (#247).** Nothing had ever run them, which
    is how #246 sat on `main` green. Three transport examples are frozen one
    docstring at a time rather than by excluding their module, because a
    fourth in the same file needs no peer and stays gated.
  - **Re-ranked the backlog by risk to a user, on the owner's challenge.** The
    measurement is the substance: across 156 commits since the first release,
    `src/` took 605 of 19,937 changed lines, three per cent; sixteen of
    twenty-five open issues traced to the template chain; seven session
    headings here contain "bump the pin". Twenty-five issues became seventeen.
    #228 became the only P1. Eight closed as `wontdo`, including #208, the pin
    bump, which is closed with a trigger rather than deferred.
  - **Inverted the template-adoption default (ADR-034).** A rule is adopted
    when someone can name the defect it would have caught here; otherwise it
    is declined in one line, with no record and no ticket. The last clause is
    load-bearing, since requiring a record to decline is what built the
    asymmetry. CLAUDE.md carries it in the precedence block so a session meets
    it before reading the chain. Filed upstream as
    braboj/solid-ai-templates#1353.
- **PRs merged:** #244, #245, #250, #251, #252, #253, #255 and #256.
- **Issues closed/created:** sixteen closed, seven shipped and nine `wontdo`.
  Created #243, #246, #247, #248, #249 and #254.
- **Lesson:** a count from a tool is not a risk assessment. I told the owner
  the largest risk was 140 blind-except sites in the module that parses
  untrusted input, from a lint total. Reading them inverted it: all seventy
  broad handlers in `packets.py` re-raise as a typed error and none swallows,
  and the seven genuine swallows are in the simulators, four of which log. The
  real defect is error misclassification -- a bug in this library reported as a
  malformed frame -- which is diagnosability, not data loss. The correction is
  on #170, where the misleading number lives.
- **Lesson:** the same failure produced the session it was diagnosing. Every
  step of the release was individually defensible and the aggregate was a day
  spent on a library that parses hostile input, without reading one exception
  handler. Nothing in the process could report that, because each gate
  measured its own subject and none measured the ratio.
- **Lesson:** an issue written from a `grep` carries the `grep`'s blind spot.
  #249 asked for a floor of ten; the assertion compares against a reader that
  drops the `Unreleased` heading, so the answer was nine and ten would have
  failed a correct tree. Measuring through the reader the assertion uses is
  what caught it, and the issue was corrected rather than implemented.
- **Upstream:** two filings. braboj/solid-ai-templates#1337 against `git.md`,
  that a periodic review attached to every release decays into paperwork.
  braboj/solid-ai-templates#1353 against `scope.md`, that a vendored rule set
  shipping MUSTs on a schedule must state its adoption bar or downstream
  backlogs fill from the release schedule.
- **Pending:** #228 is the P1 and is not started -- changing a value on a
  packet still sends the old bytes. The pin stays at `v2.61.0` against
  `v2.70.0`, which is now the decision rather than a gap. #254's three
  transport examples remain unrunnable and are frozen, not fixed. Whether the
  process machinery this session left standing is still too heavy is a
  question the next measurement answers, not this entry.

## 2026-09-01 -- Single-source the packets, ship v0.5.0 (afternoon)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Cut v0.5.0 across eight pull requests**, closing #224, #228, #229 and
    #196 -- the whole `v0.5.0` milestone, created at the start of the session
    and closed at the end. Unlike v0.4.4 this release changes the library:
    `packets.py` grew by roughly 400 lines and gained a public type. Nothing
    on the wire moved, because the per-function-code suites assert against the
    published vectors and none was touched.
  - **Settled the architecture direction note (#224, ADR-035).** Its six
    layers are adopted as vocabulary for responsibilities the three packages
    already carry, not as a structure to build, so `CLAUDE.md` 1.2 is
    unchanged and no module was split. Six capabilities tracing to no
    requirement are refused with no tracking issue. Serial transport is in
    scope because the project claims RTU and ships only its codec half.
    Refusing the restructure is what unblocked #173, #192 and #194, which had
    been waiting to be sequenced behind a document change that will not
    happen.
  - **Single-sourced the packet fields (#228, ADR-037).** The only P1: every
    concrete class stored each value twice and serialized the copy nobody
    wrote to, so setting a quantity of 2001 still emitted a frame asking for
    10. Classes now declare `PDU_FIELDS` and derive the payload on every
    read. Deleting the second copy is also what repaired equality, since a
    property leaves the instance dictionary -- that was one fix, not two.
  - **Made the payload take bytes and retired the format string (#229,
    ADR-036).** Two routes produced identical frames and the documented one
    was the narrower. `pack` and `unpack` warn and go in 0.6.0 rather than
    being removed outright, because a documented escape hatch removed without
    warning surfaces as an `AttributeError` far from the cause.
  - **Declared the specification's bounds and made them queryable (#196,
    ADR-031).** The deliverable was the reading: quantities, the coil value
    set and the MEI type from the Application Protocol, the protocol
    identifier from the Messaging Implementation Guide, the slave address
    range from PI-MBUS-300. `serialize()` calls neither `violations()` nor
    `validate()` and gains no parameter, because emitting a frame a device
    rejects is the product.
  - **Ran the third 360 audit.** Overall stays B+, 8 findings, 0 critical.
    Protocol correctness moves B+ to A- on the field-range work. Code quality
    and CI/CD hold at B+ on #149 and #217, neither of which moved.
- **PRs merged:** #258, #259, #260, #261, #263, #264, #265 and #267.
- **Issues closed/created:** four closed, all shipped rather than declined.
  Created #262, #266 and #268.
- **Lesson:** a per-item declaration with a permissive default is a blind
  spot no coverage assertion reaches. Every packet class declares its bounds
  and the base declares an empty mapping, so a class that never declared one
  inherits it, reports clean, and is indistinguishable from a class the
  specification bounds in no way. The enumeration was correct and the data
  was vacuous. The test asserting each class declares its own failed on its
  first run and named `ModbusPdu` -- four lines, written as an afterthought,
  finding a real hole in the work they were meant to confirm.
- **Lesson:** a filter that returns a plausible wrong answer twice in one
  session. During the audit a piped `grep` reported no `fetch-depth` in the
  secrets job, which reads exactly like a scan covering only the tip; the job
  carries it. At wrap-up `git tag --list 'v2.6*'` reported the newest
  upstream tag as `v2.69.0`, and it cannot match `v2.70.0`. Neither was
  caught by a check. The first was caught by disbelieving a result that
  contradicted the prior audit, the second by the previous journal entry
  naming a tag my glob could not produce -- so the record caught what the
  tooling did not.
- **Lesson:** a mechanical migration should delete and insert whole lines,
  never regenerate them. Rewriting 27 constructor calls from the syntax tree
  lost the original indentation and turned `fc=0x03` into `fc=3` -- both
  correct, both wrong to ship. Deleting only the line being removed left
  every surrounding byte untouched, and the diff became reviewable instead of
  noise. The script is scaffolding; the diff is the audit trail.
- **Upstream:** one filing. braboj/solid-ai-templates#1384 against
  `testing.md`, that `testing-negative-assertion-coverage` covers a check
  reaching nothing but not one reaching everything and asking a question the
  subject cannot fail. ADR-035, ADR-036 and ADR-037 each judged reusability
  at decision time and recorded `none` with a revisit condition.
- **Pending:** the pin sits at `v2.61.0` against `v2.71.0`, 76 commits and
  eleven bound files, now proposed as #268 rather than left as a standing
  gap -- the pointer is off-limits and needs the owner's approval before it
  moves. #262 is a gap in the work this session shipped: the constraint pass
  encoded ranges, fixed values and cross-field rules, and the Diagnostics
  sub-function code is an enumerated set it cannot express. #266 leaves the
  new capability with a feature bullet and no runnable example. #149 is a
  FAIL in three consecutive audits.

## 2026-09-01 -- Groom the backlog, ship v0.5.1 (evening)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Groomed all sixteen open issues against the current tree.** Ten held
    exactly as filed, line numbers included. Seven took dated correction
    notes: #268 was measuring a range two releases short, #172 and #170 had
    drifted on counts again, #210's open question was answerable from CI,
    #187's second criterion asks for a convention its destination does not
    carry, and #231 was still telling a reader to consult a spike that had
    closed. The corrections are notes above the body, never rewrites of it --
    a body edited in silence reads as freshly measured.
  - **Documented the constraint capability and shipped v0.5.1 (#266, #270,
    #271).** A runnable example, a usage section, and the examples index
    entry with its real output. The release exists because the tagged tree of
    v0.5.0 documented the capability nowhere, which the section below covers.
  - **Scoped v0.6.0 to the simulator public API.** ADR-035 unblocked #173,
    #192 and #194 the session before, and all three name each other as
    wanting one release because they break the same public API. #173 is a
    spike and goes first: it settles the module names, the class names, the
    call sites and the alias policy that the other two implement against.
    The milestone carries the sequence and the out-of-scope list.
  - **Wrote PLAYBOOK 4.7 for the grooming pass.** Three prior sessions left
    correction notes in issue bodies and the convention lived only in those
    notes, so the next session had nothing to copy but an example.
- **PRs merged:** #270 and #271.
- **Issues closed/created:** one closed, #266, shipped rather than declined.
  None created here; the two findings worth a ticket went upstream instead.
- **Lesson:** a tag freezes the documentation as well as the code, and the
  rule meant to prevent that does not reach it. `readme.md` requires the
  README to change in the same commit as the behaviour it describes. v0.5.0
  satisfied it -- the feature bullet merged eleven minutes after the tag, the
  usage section the next afternoon, both correctly reviewed and gated -- and
  the tagged tree still described the new capability nowhere, in the source
  archive, the sdist and the wheel metadata alike. A rule phrased against
  commits cannot see a tag. `git show v0.5.0:README.md | grep -c
  'violations\|constraint'` returns 0, and nothing else in the pipeline reads
  that file as the tag froze it.
- **Lesson:** an issue that cites a sibling's approach cites a plan. #254
  described #247's chosen route as marking three examples with a skip marker,
  and set two acceptance criteria against it. #247 shipped deselect entries
  in the manifest instead, which is the better answer, and left #254 naming a
  mechanism nobody built. Both mechanical checks the review template gives
  came back clean: no open pull request closed it, and no decision record had
  moved it. What moved it was an implementer making a better choice, which
  leaves no trace in either place.
- **Lesson:** a listing read straight after the writes it should reflect
  reported one of three. Assigning the milestone to #173, #192 and #194
  succeeded three times, and `gh issue list --milestone` then returned #173
  alone; reading each issue directly confirmed all three carried it. Whether
  that was propagation or a limit was not established, and the fix does not
  depend on knowing: read back per item after a batch of writes, never
  through the listing that aggregates them. This is the third instance in two
  sessions of a filter answering plausibly and wrongly, which makes it a
  pattern rather than three accidents.
- **Upstream:** two filings, both against rules that passed while the defect
  shipped. braboj/solid-ai-templates#1397 against `review.md`, proposing a
  sixth shape for the issue-verification section -- stale by a sibling's
  route -- since its two checks look at pull requests and decision records
  and this moves through neither. braboj/solid-ai-templates#1398 against
  `git.md`, that a pre-release check should confirm the tree being tagged
  documents the features its own list claims.
- **Pending:** the pin still sits at `v2.61.0` against `v2.71.0`, and #268
  now carries the corrected range -- ten releases, 76 commits, eleven bound
  files. It needs the owner's approval before the pointer moves. v0.6.0 is
  scoped and unstarted. #262 and #149 are where the previous entry left them,
  and #149 is now a FAIL in three consecutive audits with no work against it.
  Both upstream filings are open rather than landed.

## 2026-09-01 -- Rename the simulators, PEP 8 their API (night)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Ran spike #173 to a record (ADR-038).** `omb_client.py` and
    `omb_server.py` promised a client and a server, held simulators, and
    repeated the package name in a prefix. The record settles the module
    names, the class names and the alias policy the two follow-ons implement
    against. One acceptance criterion was already met on arrival: the two
    TODOs proposing the rename went under an hour after the issue was filed,
    in the TODO triage pass, so the spike owed nothing there.
  - **Carried the move (#274, PR #276).** 28 files and 115 lines, two of them
    strings rather than imports. One of those two was a defect in its own
    right and is covered below.
  - **Gave the public API PEP 8 names (#192, PR #277, ADR-039).** The issue
    counted seven camelCase names; running ruff past its own freeze found
    eighteen, plus four instance attributes no lint rule reaches at all. The
    server now takes `host`, a string, where it took `ipAddress` as a 32-bit
    integer unpacked with `inet_ntoa`, and `frag_count` became `frag_size` --
    the server alone had carried one value under three spellings.
  - **Broke every renamed name rather than aliasing.** The class rename
    earlier the same day kept aliases because the resolver already existed.
    Here a method alias is cheap and a keyword alias is not, and aliasing the
    methods alone leaves a call that resolves and then raises on its own
    keyword, naming a method the caller never wrote.
  - **Took `N802` and `N803` off both freeze entries**, rule lists otherwise
    byte-identical, and gave PLAYBOOK 3.4 the command that sizes a frozen
    family without editing the freeze.
- **PRs merged:** #273, #276 and #277.
- **Issues closed/created:** three closed -- #173, #274 and #192. Created #274
  and #275; the first closed the same session, the second is unmilestoned and
  holds the 0.7.0 alias removal so the obligation does not live only in a
  record. Correction notes on #210, #170 and #268.
- **Lesson:** a guard that matches live state against a string constant fails
  open, and no run reports it. `conftest.py` held the leak guard's thread name
  and nothing pinned it to the class that sets it, so the rename would have
  left the guard comparing against a name nothing produces -- matching no
  thread, returning empty, passing every test including one leaking the thread
  it exists to catch. The rename is what surfaced it, not a failure.
- **Lesson:** a negative control aimed at one break says nothing about
  another. The `host` tests were drafted asserting the attribute and a
  loopback connection, with a docstring claiming they would catch a server
  that accepted `host` and ignored it. They would not: a wildcard listener
  serves a loopback client the same way. Only planting that second shape
  showed it, and the control for the first break had passed convincingly.
- **Lesson:** an edit that rewrites line endings destroys the evidence a plant
  landed. Scripting one with `write_text` on Windows turned the file's LF into
  CRLF, so the diff meant to confirm a single planted line reported all 1,065.
  Nothing was wrong with the plant; the confirmation was unreadable, which is
  indistinguishable from a plant that missed. Re-planting with newlines
  preserved is the fix, and confirming before reading the run is what caught
  it at all.
- **Upstream:** three filings. braboj/solid-ai-templates#1404 against
  `python-lib.md`, that a package already binding a name through a module
  `__getattr__` owns the mechanism a deprecation alias needs.
  braboj/solid-ai-templates#1405 against `quality.md`, that a rename spanning
  one call site is deprecated whole or not at all. And
  braboj/solid-ai-templates#1406 against `quality-gates.md`, that sizing a
  frozen rule family needs no edit to the freeze. A fourth candidate, the
  drift guard above, is already covered by `testing-drift-guard` and was not
  filed.
- **Pending:** #194 is the last of v0.6.0 and is unstarted -- the TLS settings
  are still loose keyword arguments and a raw OpenSSL cipher string, and it
  wants a config-object shape decided before code. The pin stays at `v2.61.0`
  against `v2.72.0`, now 88 commits over 12 of the 16 bound files, and the
  pointer needs the owner's approval. #210 now has three tests producing its
  warning rather than two. All three upstream filings are open rather than
  landed.

## 2026-09-01 -- Make every documented example run (late night)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Settled the client's `host` on a string (#279, PR #280).** The
    constructor documented `str` and defaulted to `b"localhost"`, `connect`
    documented the same value as bytes, and `run_client` passed the bytes
    form, so the shape the module demonstrated was the one its own docstring
    contradicted. Two of the four new checks are drift guards over the same
    fact written twice; a third reads `run_client` as a tree, because the
    entry point builds its client inline and no signature carries the value.
  - **Promoted the CRC walkthrough to `examples/` (#187, PR #283).** It
    carried the only single-place statement of why the RTU checksum is sent
    low byte first and nothing ran it. It now compares rather than prints,
    against complete published frames, and CI executes it against a
    consumer-shaped install. `scripts/` holds `gen_test_certs.py` alone, so
    ADR-024's decision 4 covers all of it -- the gap that record left open.
  - **Moved the transport demonstrations out of the docstrings (#254, PR
    #284, ADR-040).** Three class docstrings each opened a socket to a server
    nothing starts. They had been frozen by a deselect each, which was the
    right first move and settled nothing: the gate then read as covering the
    docstrings it was added to catch. `ModbusTcpStream` names an example that
    already existed; the sender and receiver name one added here that holds
    both ends of a connection in one process.
  - **Dropped two stale counts from the guide documents (PR #285).**
    ONBOARDING described the examples index as four patterns when there were
    six, and PLAYBOOK said the two socket examples start the simulator when
    there are three and the new one starts none.
- **PRs merged:** #280, #283, #284 and #285.
- **Issues closed/created:** three closed -- #279, #187 and #254. Created #281
  and #282, both unmilestoned: the first is the sibling example that reports a
  failed check by printing `False`, the second the encoding gate that does not
  reach `examples/`, which #187's correction deferred rather than settled.
- **Lesson:** designing a negative control is what tests a check; running it
  only tests the control. The CRC example first compared the 16-bit checksum
  value, which reads as the obvious assertion. Choosing what to plant is what
  exposed the hole -- flipping the byte order leaves the value identical, so
  the check would have passed on the exact defect the file exists to explain.
  The comparison moved to the complete frame bytes before any control ran.
- **Lesson:** a count written into prose rots from a direction no diff shows.
  ONBOARDING had said four examples since before this session and nothing
  reported it, because nobody edited the file -- every other document gate
  here compares a document against the system when one of them changes. It
  surfaced only from deliberately sweeping the guide documents for counts
  after the directory grew twice, and the fix is to carry no number at all.
- **Lesson:** the hypothesis that read as most obviously true was the one that
  fell. The client's bytes host looked like it must break TLS, because the
  `ssl` module wants a string for the name it sends. Probed rather than
  asserted, and `wrap_socket` accepts bytes -- so the case for a string rests
  on the docstrings and on matching the server, and the commit says so rather
  than claiming a breakage that is not there.
- **Upstream:** two filings. braboj/solid-ai-templates#1408 against
  `examples.md`, that an exemption from an example gate is a holding position
  and a demonstration needing a peer moves to the examples directory.
  braboj/solid-ai-templates#1410 against the same file, that an example
  printing its verdict cannot fail the smoke job that runs it -- which lands
  hardest on the examples asserting against a specification vector, the ones
  making the strongest claim.
- **Pending:** #194 is still the last of v0.6.0 and still unstarted; it wants
  the TLS config-object shape decided before code. The pin stays at `v2.61.0`
  against `v2.72.0` and #268 needs the owner's approval on the pointer. #281
  and #282 are open from this session. All five upstream filings, the three
  from the previous session and the two from this one, are open rather than
  landed.

## 2026-09-02 -- Give the example gates teeth

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Made a failed check fail the job that runs it (#281, PR #287).**
    `round_trip_a_packet.py` reported both comparisons by printing them, so a
    run producing `frame matches the written-out vector: False` was a green
    examples job and a merged regression -- the job reads exit status. That
    silenced the one comparison a self-consistent encoder and decoder cannot
    satisfy. Both are now printed and then enforced, in that order.
    `capture_a_burst_of_packets.py` carried the same defect from the previous
    session and was fixed with it.
  - **Brought the examples under the output-encoding gate (#282, PR #288).**
    The gate read `src/pyomb/` and `scripts/`, the two directories a
    maintainer runs, and not `examples/`, the one a stranger runs. All seven
    gained the call inside their `__main__` guard.
  - **Restated the examples index claim.** It said nothing there can rot
    quietly, which is stronger than the directory delivers: three examples
    compare a result and exit non-zero, two fail only on a startup or parse
    error, and two demonstrate without verifying. It now says which is which.
- **PRs merged:** #287 and #288.
- **Issues closed/created:** two closed -- #281 and #282, both filed in the
  previous session. None created.
- **Lesson:** a control that exits non-zero for the wrong reason is not a
  control. The first plant against the round-trip example lengthened the MBAP
  length field, which raised inside `deserialize` before either comparison
  ran. It failed loudly and convincingly and said nothing about whether the
  check works. The replacement changed a quantity, producing a frame that
  parses and simply is not the vector, which is the break the check exists to
  catch.
- **Lesson:** the authority on a decision can be inside the file about to be
  edited. #282 was filed arguing to widen the gate; checking its premise found
  that the character-set rule already holds every example to ASCII, and the
  decline started to look better supported than the filing. The gate's own
  module docstring had answered that argument already, for the package -- the
  ASCII rule is a property of the strings and not of the boundary, and a
  message formatted at run time escapes it. Twenty lines above the roots being
  edited, and it reversed the conclusion back.
- **Lesson:** an acceptance criterion asking what a claim now means is worth
  more than it reads. #281's last criterion asked whether the index claim
  needed rewording or simply held. Answering it meant surveying all seven
  examples, which is what turned up the second file with the same defect and
  the fact that the claim had never held for four of them.
- **Upstream:** nothing new filed. The rule #281 demonstrates went up in the
  previous session as braboj/solid-ai-templates#1410. The second lesson above
  looked like a candidate and is not: `ai-workflow-read-edit-site` already
  requires reading the target file for recorded prior reasoning before
  changing it, and a module docstring carrying a settled argument is exactly
  what that rule describes.
- **Pending:** #194 is still the last of v0.6.0 and still unstarted. The pin
  stays at `v2.61.0` against `v2.72.0` and #268 needs the owner's approval on
  the pointer. Five upstream filings are open across the two sessions, none
  landed.

## 2026-09-02 -- Align the guides with the gates (wrap)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Corrected three guide passages the example work had left stale (PR
    #290).** ONBOARDING told a new contributor that deselected examples are
    normal, which now means something is wrong rather than nothing. PLAYBOOK
    3.24 described three exemptions that no longer exist and cited the issue
    that removed them. PLAYBOOK 3.19 said a new *script* that prints fails the
    encoding gate, one root short of what the gate now reads.
  - **Gave PLAYBOOK 3.20 the rule the session established**, that an example
    which verifies something raises rather than printing the verdict, together
    with the statement that nothing enforces it. Detecting which examples make
    a claim is not mechanical, and an unenforced step sitting beside enforced
    ones reads as enforced.
  - **Left the 2026-09-01 audit untouched** where it names the three
    deselected tests. That is a dated observation carrying a grade, which a
    later report re-derives rather than an instruction that has gone stale.
- **PRs merged:** #290.
- **Issues closed/created:** none either way.
- **Lesson:** writing the journal before the audit runs costs a second entry.
  The previous entry was written when the work looked finished, and the audit
  then produced a pull request, two upstream filings and three document fixes
  -- every one of them a line that entry should have carried. The end-of-
  session order puts the journal last for exactly this reason, and an entry's
  account is fixed once merged, so the correction is another entry rather than
  an edit. Cheap here, and only because the audit was run at all.
- **Lesson:** the stale-document defect this session fixed twice is the same
  one it then committed. Yesterday's finding was that a count in prose rots
  from a direction no diff shows; today's was three passages describing gates
  that had changed underneath them. Both were found by sweeping deliberately
  rather than by any check, and the second sweep only happened because the
  audit's items name the documents one at a time.
- **Upstream:** two filings, both from the previous entry's work rather than
  this one. braboj/solid-ai-templates#1415 against `quality-gates.md`, that a
  negative control must reach the check rather than merely be behavioural --
  a plant rejected by a layer in front of the check exits non-zero and looks
  identical to one that fired. And braboj/solid-ai-templates#1416 against the
  same file, that a gate scoped by a list of directories omits the one nobody
  on the team runs, which is the one with the weakest guarantee. A third
  candidate was dropped: reading the target file for recorded prior reasoning
  is already `ai-workflow-read-edit-site`.
- **Pending:** unchanged from the previous entry. #194 is the last of v0.6.0
  and unstarted, the pin stays at `v2.61.0` against `v2.72.0` under #268, and
  seven upstream filings are now open across the three entries, none landed.

## 2026-09-03 -- Group the TLS settings, ship v0.6.0

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Grouped the eight TLS keyword arguments into one `TlsSettings` record
    (PR #294, ADR-041).** Both simulators take `tls`; `secure` is gone, so
    certificates can no longer be handed over and silently ignored. Every
    option defaults to `UNSET` rather than a value, which is load-bearing
    rather than tidy: the protocol constant and hostname checking differ by
    side, so no stored value is right for both. `relaxations(role)` names each
    weakening and both simulators log the list at construction, which is what
    turns a relaxation from explicit into inspectable. The cipher string stays
    OpenSSL format, decided rather than assumed.
  - **Ran the 360-degree audit rather than skipping it (PR #297).** Overall B,
    down from B+, nothing critical. Security and Documentation both reach A,
    closing findings three consecutive reports carried. The bottleneck moved to
    Dependencies and viability, where the update-mechanism row is new.
  - **Cut v0.6.0 (PR #298).** Version literal, changelog entry with its compare
    link, README install command. The release pipeline ran green through every
    step and attached the wheel, sdist and SBOM.
  - **Corrected ADR-041's upstream citation.** It shipped naming an issue
    number written before the filing existed, which turned out to belong to an
    unrelated changelog issue by another author.
- **PRs merged:** #294, #297, #298, and the wrap.
- **Issues closed/created:** #194 closed by #294, which was the last of the
  v0.6.0 milestone; the milestone is now closed. Created #295, that split
  CodeQL action bumps deadlock each other, and #296, that the `TlsSettings`
  sentinel cannot be named from the public API. Commented on #210 correcting
  its mechanism, and on #170 recording that the freeze denominator moved.
- **Lesson:** a negative control has to be planted in the artifact the check
  reads, not the one on disk. Two audit reports were moved out of
  `docs/audits/` to make the newest one stale, the move was confirmed by
  re-reading the directory the way the rule asks, the gate passed, and the
  conclusion drawn -- that the gate was blind -- was wrong. It reads git's
  index, so the plant never reached it. Staging the deletions made it fail with
  the exact message it exists to produce. The comfortable answer and the wrong
  one were the same answer, and nothing in the output separated them.
- **Lesson:** two claims were made in this session that were not checked before
  they were made. The session-start report said there were no open pull
  requests when two Dependabot ones had been open since the day before, and
  ADR-041 shipped citing an upstream issue that had not been filed. Neither
  changed what was built. Both are the same failure -- writing a fact in the
  shape it was expected to take rather than the shape it had -- and the second
  is worse, because a merged decision record is the surface a later reader
  trusts most and the one nothing rereads.
- **Lesson:** the audit found a defect in the release it was auditing rather
  than only in the tree behind it. #296 is a gap in the object shipped hours
  earlier: the settings record defaults every field to a sentinel the public
  surface does not name. An audit run on the release branch is the only pass
  positioned to catch that, and it is the argument for running it there rather
  than after the tag.
- **Upstream:** two filings, both from this session's work.
  braboj/solid-ai-templates#1424 against `config.md`, that a sentinel is also
  required where a setting has no single default because the right value
  depends on which consumer is asking -- the template argues only from the
  default also being a legal value, so the correct design fails its own test.
  And braboj/solid-ai-templates#1425 against `quality-gates.md`, the
  planted-in-the-wrong-artifact lesson above, which is distinct from #1415:
  there something rejects the plant before the check runs, here the check runs
  to completion over a corpus that still holds what the operator removed.
- **Pending:** nine upstream filings are open across four entries, none landed.
  #295 blocks the CodeQL action pins from moving at all and is the audit's
  named bottleneck. The pin stays at `v2.61.0` against `v2.73.0` under #268.
  Cognitive complexity is ungated for the fourth consecutive audit, #149.

## 2026-09-03 -- Unblock the pins, read the range (afternoon)

- **Tool:** Claude Code (Opus 5, 1M context).
- **Key changes:**
  - **Broke the CodeQL bump deadlock (PR #300).** The action ships as `init`
    and `analyze`, each refusing to run against the other's version, and
    Dependabot bumped them as separate pull requests. Neither could merge in
    any order. One `groups` entry fixes it; a new gate reads the workflows for
    actions referenced under more than one name and fails when no single group
    covers them, so the next release cannot deadlock the same way. Confirmed
    rather than assumed: Dependabot closed #292 and #293 itself and opened a
    grouped #301, which merged on its own checks.
  - **Made the unset sentinel public, as an enum (PR #302, ADR-042).** A probe
    changed the fix. Exporting it as the plain class it was would have shipped
    a guard a caller can write and cannot act on, because mypy narrows a union
    on identity against an enum member and not against an arbitrary instance.
    The switch introduced a regression it also caught: an enum brings its own
    `__str__`, so `f"{UNSET}"` leaked the private type name until the override
    covered both spellings.
  - **Bumped the templates pin from v2.61.0 to v2.75.0 and read the range
    (PR #303).** Fourteen releases, 108 commits, 12 of the 16 bound files
    changed. Twenty-four distinct rules: five adopted, nineteen declined per
    ADR-034. Four of the range's rules were written from this repository's own
    incidents, which is why so many decline as already implemented.
  - **Gave the transport a logger and chained its causes (PR #305, ADR-043).**
    The three I/O classes take one; the module's own carries a null handler and
    writes nothing, which is the opposite default from the simulators and
    deliberate. Five raises inside excepts now carry `from e`, which took
    `B904` off `stream.py`'s ruff freeze.
- **PRs merged:** #300, #301, #302, #303, #305.
- **Issues closed/created:** #295, #296, #268 and #195 closed, each against
  evidence rather than on a green suite. Created #304, that two bound templates
  now disagree on whether moving content between documents needs a decision
  record. Commented on #170 recording the freeze shrink.
- **Lesson:** two tests in this session were blind when written, and only
  planting the control found them. `test_the_default_logger_writes_nothing`
  asserted that nothing reached stderr in-process, which passes whether or not
  the null handler exists, because the test runner installs a root handler and
  logging's last-resort path never fires. The fragment-boundary test asserted
  `x == x[:1]`, true of any list of one or fewer, over a list that was empty
  because the failing socket raises before the line under test is reached. Both
  would have shipped. Running the controls is what separated them from the
  tests that work, and neither was distinguishable from a passing test.
- **Lesson:** an issue's premise decays like any other claim. #195 said the
  transport holds eight blind excepts that swallow failures; the tree holds
  five and every one re-raises, so nothing was swallowed. It also named two
  modules the 0.6.0 rename retired. What was true -- no logging, every cause
  discarded -- is narrower than what was filed, and reading the five sites
  before building is the only thing that would have caught it.
- **Lesson:** a bound template nothing lists is a template nobody reads.
  `communication.md` states how this agent answers and has been in the chain
  the whole time, absent from the startup block, which is a hand-maintained
  copy of what the manifest resolves. Nothing reported the gap because the gate
  checks the block names nothing the chain fails to resolve, not the reverse.
  The session ran verbose until the owner named the file.
- **Lesson:** the working directory persists across shell calls, and a `cd`
  into the submodule survived into a later call, where `git add` reported a
  path that did not match. The rule says to check the working directory first
  on an unexpected negative, and doing so turned a puzzling result into one
  line. Absolute paths for the rest of the session cost nothing.
- **Upstream:** two filings, both open. braboj/solid-ai-templates#1435 against
  `python-lib.md`, that a sentinel a caller compares against is public API and
  that its type decides whether the guard narrows -- the templates say when a
  sentinel is required and nothing about what it then has to be. And
  braboj/solid-ai-templates#1445 against `python.md`, that a library attaches a
  null handler and the application tier is what constructs a writing one, with
  the note that a test runner's root handler hides the difference.
- **Pending:** #304 is unresolved and needs a call on which template governs.
  Upstream moved again during the session, so the pin is at `v2.75.0` against
  `v2.76.0`. Cognitive complexity is ungated for the fifth consecutive audit,
  #149. The previous entry counted nine open upstream filings across four
  entries; this session's two are additional and neither has landed.
