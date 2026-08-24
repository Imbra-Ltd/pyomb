# ADR-008: Resolve the platform layer into the startup block

**Status:** Accepted
**Date:** 2026-08-19
**Upstream:** filed as braboj/solid-ai-templates#1029 against
`templates/base/workflow/scope.md`. With the domain skin off, the convention is
that a manifest selecting layers on independent axes needs each axis resolved
explicitly — a single-axis walk yields a chain that is internally consistent,
externally incomplete, and indistinguishable from a complete one.

## Context

#32 asks whether `templates/platform/github.md` or
`templates/base/security/devsecops.md` belong in the mandatory startup block.
It was raised while closing #7, where the gitleaks gate shipped scanning the
working tree while both templates already required the full history. The rule
was re-derived from a defect rather than read.

ADR-001 describes the block as "the twelve template files in the resolved
chain". That is close, and the distance is where the answer sits.

`templates/manifest.yaml` is the machine-readable dependency graph. Resolving
`stack-python-lib` through it yields ten files: the six in `core`, plus
`base-quality-gates` and `base-examples` from the stack entry, plus
`base-config` pulled in by quality gates, plus the stack template itself. The
block carries those ten and adds `scope.md` and `ai-workflow.md`, which the
session protocol needs and which no stack declares.

So the block is the stack chain plus two deliberate additions. What it has
never contained is a platform, and the manifest shows why nothing flagged that:

```text
$ git -C docs/solid-ai-templates show HEAD:templates/manifest.yaml \
    | awk '/^stacks:/,0' | grep -c "platform-"
0
```

No stack declares a platform dependency. The platform is selected by where the
repository is hosted, on an axis the stack graph never touches. ADR-001
resolved the stack axis and stopped, so the platform axis resolved to nothing —
not through a judgment that GitHub's rules do not apply here, but because
nothing in the procedure asked. A chain that terminates cleanly looks finished.

That `platform/github.md` already binds this repository is not a matter of
opinion. Its label section requires exactly one type label and one priority
label per issue, and supplies a conformance check. The check passes here:

```text
$ gh issue list --state open --limit 200 --json number,labels --jq '...'
[]
```

The project has been obeying the template without reading it. Where it has not,
it paid for each rule a defect at a time: the full-history scan in #31, and the
two defects recorded under Consequences, which surfaced from finally reading
the file rather than from anything failing.

`devsecops.md` is a different question with a different answer. It sits in the
manifest's `base:` list, but no library stack depends on it — not
`stack-python-lib`, not `stack-go-lib`, not `stack-nodejs-lib`. It enters
through `stack-python-service` and the other service and backend stacks. An
exclusion consistent across three languages reads as deliberate rather than
missed, and its content agrees: the DAST, IaC-scanning and penetration-testing
sections govern a deployed system, and this library has no deployment.

Its rules that would bite a library are already covered, or not yet live:

| devsecops rule | Status here |
| --- | --- |
| A failed SAST scan MUST stop the build | Already a MUST in `quality-gates.md`, which the block reads: a CI check that does not block merge is informational, not a gate |
| The scan MUST cover the full git history | Already in `platform/github.md`, which this record adds |
| Pin third-party actions to a commit SHA | Already in `platform/github.md` |
| A SBOM MUST be generated per release | Uncovered, and not yet live — this repository has cut no release |

## Decision

Two decisions, one concern: what the mandatory startup block resolves.

1. **Resolve the platform axis.** Add `templates/platform/github.md`, and
   `templates/base/workflow/issues.md`, which the manifest declares as its
   dependency alongside the already-present `base-quality-gates`. The block
   goes from twelve files to fourteen.

2. **Decline `templates/base/security/devsecops.md`.** The manifest excludes it
   from every library stack, and each of its rules that reaches a library is
   either already carried by a template in the block or governs a release
   process this repository does not yet have.

```text
                      templates/manifest.yaml
                                |
              +-----------------+-----------------+
              |                                   |
        stack axis                          platform axis
     (what it is built with)            (where it is hosted)
              |                                   |
      stack-python-lib                      platform-github
              |                                   |
   core + quality-gates +                 + base-issues
   examples + config                            |
              |                                   |
      ten files, resolved                 two files, never
      by ADR-001                          resolved until now
              |                                   |
              +-----------------+-----------------+
                                |
                    + scope.md, ai-workflow.md
                     (session protocol, no stack
                      declares them)
                                |
                        fourteen files
```

**Revisit trigger for (2):** the first release, which makes the SBOM rule live,
or the project growing a deployed component, which makes the rest of the
template apply. #36 tracks the SBOM obligation until then.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Add both templates | Buys one uncovered rule (SBOM per release) at the cost of reading 135 lines every session, most of which govern deployment, infrastructure-as-code and penetration testing that this library will never have. An issue tracks the one rule for a fraction of the cost. |
| Add neither, and rely on the audit | The audit is what this record is. It found two live defects by reading one file once; leaving the file unread returns the project to discovering those rules one defect at a time, which is the pattern #32 was raised to stop. |
| Add `platform/github.md` without `base/workflow/issues.md` | The manifest declares the dependency, and the label section carries `[EXTEND: base-issues-types]` — reading the extension without the base leaves the taxonomy it extends undefined. |
| Copy the binding rules into `CLAUDE.md` instead | The inline model ADR-001 already rejected, for the reason it gave: this repository vendors the templates, so a copy is a second representation that drifts from the file sitting on disk beside it. |
| Derive the block from the manifest at commit time with a generator | Correct in principle and disproportionate here. The chain changes when the stack or the host changes, which has happened once. A generator plus its staleness gate is more machinery than the fact it would pin. |

## Consequences

- The startup block lists fourteen files. Reading them is the cost paid on
  every session, and it rises by roughly 700 lines.
- ADR-001 stands. This record does not reverse its decision or its model; it
  resolves an axis that decision never reached, and the phrase "the resolved
  chain" there should be read as the stack chain it was.
- Reading `platform/github.md` surfaced two defects in CI that no gate reports,
  both fixed under #38:
  - the workflow has no fan-in `gate` job, so every job is individually
    required and `security` is required by nobody — which is why bandit has
    been able to fail without blocking a merge since ADR-007 wired it
  - the gitleaks download runs `curl -sSL` without `-f`, so a 404 exits 0 and
    writes the response body into the tarball; the run then fails at `tar`
    with "not in gzip format", naming the wrong thing
- The label conformance check now has an owner. It was passing by habit; it is
  now a check the project is expected to run.
- The SBOM obligation is recorded rather than adopted, and #36 carries the
  revisit trigger. Declining a rule with a trigger is a decision; declining it
  silently is a gap the next audit rediscovers.
- `platform/github.md` carries one claim this repository has already disproved
  — that CodeQL is free on private repositories. ADR-007 measured the 403 that
  refutes it. Filed upstream as braboj/solid-ai-templates#1030; until it is
  corrected, ADR-007 outranks the template on that point, per the precedence
  order in `CLAUDE.md`.

## Related

- ADR-001 — the adoption decision whose chain this extends
- ADR-007 — the recorded decline of platform SAST, and the measurement that
  refutes the template's CodeQL claim
- #32 — the startup block omission, which this closes
- #36 — the SBOM-per-release obligation, deferred with a revisit trigger
