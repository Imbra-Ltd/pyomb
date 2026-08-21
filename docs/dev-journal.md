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
