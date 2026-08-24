---
id: "012"
status: Superseded
date: 2026-08-21
category: tooling
supersedes: ["007"]
superseded_by: ["013"]
---

# ADR-012: Adopt CodeQL as the platform half of the SAST gate

**Upstream:** filed as braboj/solid-ai-templates#1042 against
`templates/platform/github.md`, and braboj/solid-ai-templates#1041 against
`templates/base/core/quality.md`.

With the domain skin off, the first is that isolating an elevated-scope scan
into its own workflow costs the single-required-context property unless that
workflow carries its own fan-in. The template asks for both without noting they
collide. The second is that a recorded revisit trigger has no watcher, so the
obligation to reopen a decision belongs to whoever fires the trigger.

## Context

ADR-007 declined platform SAST and named the condition that would reopen it:

> **Revisit trigger:** the repository going public, which makes code scanning
> free, or GitHub Code Security being purchased for the organization. Either
> one reopens this decision; neither is on the roadmap today.

The repository was made public on 2026-08-21, so the trigger fired. Nothing
announced it. The record went on reading `Accepted` and describing a scanner
the host refuses to run, and would have kept reading that way, because a
decision record is a file nobody re-reads without a reason. It surfaced only
because the endpoint ADR-007 cited was re-probed and gave a different answer:

```text
  before                         after
  ------                         -----
  code-scanning/alerts           code-scanning/default-setup
  -> 403                         -> {"state":"not-configured",
     "Code Security must be          "languages":["actions","python"]}
      enabled for this
      repository"                the feature is present and unconfigured,
                                 which is a different answer from absent
```

ADR-007's whole objection to committing a CodeQL workflow was that it could not
run, leaving the permanently red or permanently skipped job that
`quality-gates-scope-agreement` names as gate-by-omission. That objection is
gone, so the alternative it rejected is available on its merits rather than by
default.

## Decision

1. Adopt CodeQL, in `.github/workflows/codeql.yml`, as a committed workflow
   rather than the repository's default-setup toggle, so the scoped permission
   is reviewed and version controlled like any other change.
2. Keep it out of `ci.yml`. It is the only analysis here needing
   `security-events: write`, and isolating it keeps that scope off the lint,
   test, build and secret-scan jobs.
3. Analyse both languages the repository resolves to, `python` and `actions`.
   The second reads the workflow files themselves, which is where an
   over-broad permission or an unpinned action would surface.
4. Run the `security-extended` suite, measured rather than assumed. See below.
5. Give the workflow its own fan-in job, `codeql`, mirroring `gate` in
   `ci.yml`, so branch protection names one context per workflow rather than
   one per language.
6. Keep bandit, and carry its rules forward into this record rather than
   leaving them in a superseded one. This is an addition to the Security row,
   not a replacement: the two answer different questions, and only one blocks
   a merge on a finding. Unchanged from ADR-007, restated because a reader who
   stops here has to find them:
   - Bandit runs in CI over `src`, `scripts` and `tests` and fails on any
     finding at any severity. No severity floor, no per-file freeze table,
     because the tree is clean at full strictness.
   - A suppression is site-local. It names the specific check (`# nosec B603`,
     never a bare `# nosec`) and the reason sits in a comment directly above
     the line, leaving every other check live there.
   - The analysis is never turned off to make the gate pass. The one
     config-level skip is `assert_used`, scoped by glob to the test modules,
     so the check still fires on `src/` and `scripts/`.

### Why both scanners, and what each actually gates

They are not redundant, and the difference is not severity coverage:

```text
  bandit    finding        -> job fails -> gate fails -> merge blocked
  CodeQL    finding        -> alert written to the Security tab
            analysis error -> codeql fan-in fails      -> merge blocked
```

Bandit gates on findings. CodeQL gates on having run. Blocking a merge on a
CodeQL alert is a separate platform control and is not turned on here, so the
`codeql` context is honest about being narrower than it looks. It proves the
scan happened, which is the property the fan-in exists to hold.

### Why `security-extended`

Both suites were run against this tree before choosing, because a suite picked
by feel is the guess `quality-calibration` warns about:

| suite | python rules | actions rules | findings |
| --- | --- | --- | --- |
| default | 43 | 17 | 0 |
| `security-extended` | 50 | 23 | 0 |

Thirteen more rules, no additional noise, on a library whose stated purpose is
parsing untrusted bytes off a socket. This is ADR-007's own reasoning about a
severity floor, run the other way: a narrower suite is worth choosing when the
wider one is noisy, and it is not.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Leave ADR-007 standing | Its trigger fired. Declining again would need a reason, and there is none: the measured objection was that the scan could not run, and it runs. |
| Enable the default-setup toggle in repository settings | Faster, and it produces the same analyses. The scoped permission then lives in a settings page rather than a reviewed file, which `platform-github` rules out, and this repository could no longer state what its own scanner runs. |
| Put the analysis in `ci.yml` as another job | Keeps one required context for the whole repository, which is what PLAYBOOK 3.9 is built around. It also puts `security-events: write` in the same workflow as the secret scan and the build, so a compromised step in any of them could write findings. The isolation rule wins, and the fan-in in decision 5 is what pays for it. |
| Run the default suite | Thirteen rules cheaper, and it buys nothing measurable. Both suites report zero on this tree, so the wider one costs only seconds already being spent. |
| Drop bandit now that CodeQL is here | Bandit is the half that blocks a merge on a finding. Dropping it would trade a gate for an advisory feed and leave the Security row weaker than ADR-007 left it. |
| Make the `codeql` context required in branch protection in this change | The workflow is proven green, so this is defensible. It is a repository policy change rather than a code change, it binds administrators, and it belongs to the owner rather than to the change that adds the scanner. Recorded as a consequence below, with the command that applies it. |

## Consequences

- The Security row of the gate table is wired on both halves for the first
  time. ADR-007's "declined rather than missing" record is superseded by this
  one; its status is flipped rather than its prose edited, per the
  immutability rule.
- The repository gains a second workflow that can block a merge, once its
  `codeql` context is added to branch protection. Until it is, CodeQL runs,
  reports, and gates nothing, which is the shape the `gate` job in `ci.yml`
  was built to correct. Called out rather than left implicit, and readable at
  any time:

  ```bash
  gh api repos/Imbra-Ltd/pyomb/branches/main/protection \
    --jq .required_status_checks.contexts
  ```

- Findings arrive as alerts rather than as a red pipeline. Nobody is notified
  by a green run, so the Security tab has to be read. PLAYBOOK 3.8 says where.
- The scheduled Monday run means a quiet file is re-analysed against moving
  query packs. Without it, the newest analysis of untouched code is whenever
  it was last edited.
- Two more action pins to keep moving, both `github/codeql-action` at one SHA.
  Dependabot reads the trailing version comment as it does the others.
- `docs/solid-ai-templates` is not analysed, because the checkout does not
  fetch submodules. That is the right answer rather than an oversight: it is
  upstream prose, and findings there are not this project's to fix.
- The divergence ADR-008 records still holds. `platform/github.md` claims code
  scanning is free on all repositories, private ones included, and ADR-007
  supplied the 403 that refutes it. Superseding ADR-007 does not retract that
  measurement, and braboj/solid-ai-templates#1030 still carries it upstream.
  What changed is narrower than it looks: this repository is no longer the
  case the claim is wrong about. It is stated here because a superseded record
  is exactly where a live divergence goes missing.

## Related

- ADR-007 — declined platform SAST and named the trigger this record acts on,
  superseded by this one
- ADR-008 — records the template divergence that ADR-007's measurement
  supports, which this record leaves standing
- ADR-003 and ADR-005 — the freeze rules bandit inherits, unchanged here
- #71 — the ticket raised when the trigger was found to have fired
