# ADR-015: Gate the startup block against the chain the pin resolves

**Status:** Accepted
**Date:** 2026-08-22
**Upstream:** filed as braboj/solid-ai-templates#1050 against
`templates/base/core/agents.md`. With the domain skin off, the convention is
that a mandatory cache of a machine-readable source must be gated against that
source. The templates already call a consumer's chain list a cache that can go
stale and silently change governed scope, and they name no check for it. That
is the shape `quality-gates-pair-check` exists to refuse.

## Context

The startup block in `CLAUDE.md` names every template file that must be read
before the first response. It cannot live anywhere else. `base-scope` requires
it there because `CLAUDE.md` is the only file loaded before an agent acts, so
every other document is unreachable until something names it — a bootstrap, not
a preference.

`base-agents` describes what that list is:

> Any chain list a consumer writes into its own context file is a cache of that
> resolution, not the definition. It can go stale, and a stale one changes
> governed scope without any edit to the rule it drops

So the copy is mandatory and its drift is invisible. It originates upstream, in
another repository, and therefore never appears in a diff here.

PLAYBOOK 4.1 already states both directions the copy goes wrong. It ships a
runnable command for one of them — every entry must exist at the pin — and
leaves the other as prose instructing the reader to resolve the chain and
compare. Both have now fired, three weeks apart, and neither was reported by
anything:

| Direction | What happened | How it surfaced |
| --- | --- | --- |
| Block names a file the pin lacks | The pin sat three commits past the newest tag, so the block listed `examples.md`, which no released revision carried | A person read the block; #4 reverted the pin |
| Chain resolves a file the block lacks | `stack-python-lib` gained `base-examples` upstream, so the next bump resolves fourteen files against a block naming thirteen | A person read the manifest; #68 still carries it |

ADR-008 weighed a neighbouring option and rejected it:

> Derive the block from the manifest at commit time with a generator — Correct
> in principle and disproportionate here. The chain changes when the stack or
> the host changes, which has happened once.

That premise is refuted rather than merely aged. The chain has changed twice
since, and neither change was a stack or a host change: both were upstream
moving a template into or out of the resolution while this repository's own
identity stood still. The frequency estimate the rejection rested on counted
the wrong event.

## Decision

Gate the block with a test that resolves the manifest at the pinned revision
and asserts the block equals that resolution, reporting each difference by the
side it sits on.

```text
   docs/solid-ai-templates @ pin              CLAUDE.md
   templates/manifest.yaml                    ## Mandatory startup
            |                                          |
      core set + edges                          the listed paths
            |                                          |
   closed over the two axes                            |
   stack-python-lib, platform-github                    |
            |                                          |
      + scope.md, ai-workflow.md                        |
        (no stack declares them)                        |
            |                                          |
            +--------------------+---------------------+
                                 |
                        assert the sets are equal
                                 |
              +------------------+------------------+
              |                                     |
     resolved and not listed              listed and not resolved
     governed scope lost                  scope never adopted
```

Four facts stay written down: the two axis selections, which are what this
repository is rather than anything derivable from the tree, and the two
session-protocol templates no stack declares, which ADR-008 explains. Every
other name is derived, so an upstream file joining or leaving the chain moves
the expected set with no edit here.

This is a verifier, not the generator ADR-008 rejected. It produces no
artifact, needs no banner, no staleness tool and no formatter exclusion, and it
cannot rewrite the block — a failure names what differs and leaves the
correction to a person. The rejected option's cost was its machinery; a test
module carries none of it.

The manifest is read at the pin rather than from the working tree or
`origin/main`, per the same rule that governs reading any template here. Those
describe a future state of this repository, and a chain resolved from one would
report drift against rules that do not govern yet.

Reading it uses no YAML parser. `uv` is absent from at least one contributor
environment, so a dependency added here could not be locked in the same change,
and CI installs with `--locked`. A small reader takes the four shapes the
manifest uses and fails loudly on a fifth rather than resolving short.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Leave PLAYBOOK 4.1 as it is | It states the constraint and mechanizes half of it. The unmechanized half is the one that has fired and is still open, and a recipe step only runs when a reader reaches for the recipe. |
| Generate the block from the manifest | The option ADR-008 rejected, and its reasoning still holds even though its premise did not: generation brings a committed artifact, a banner, a staleness gate and a formatter exclusion, to pin a fact a test pins for free. Verifying is the cheap half of generating. |
| Read `generated/stack-python-lib.md` upstream instead of resolving | It is upstream's own resolved chain and would remove the reader entirely, but it covers the stack axis only — the platform axis and the two session-protocol additions are still unresolved — and `base-scope` requires the block to list every file, so the list cannot shrink to a bundle name. |
| Add `pyyaml` and parse properly | Correct in principle, and blocked in practice: the dependency cannot be locked where `uv` is unavailable, and CI fails a stale lock. The manifest's four shapes are narrow enough that a reader guarded by its own test is the smaller risk. |
| Depend on `pyyaml` arriving transitively through bandit | A gate resting on another tool's dependency breaks when that tool drops it, and the failure names neither tool nor cause. |

## Consequences

- The block stops being maintained by attention. A bump that changes the chain
  fails the suite naming the file and the side, in the same run that already
  gates everything else.
- PLAYBOOK 4.1 loses its manual reconciliation half and names the test instead.
  The existence check it shipped is subsumed: a block entry the pin lacks is
  also a name the chain does not resolve.
- The guard was verified against the real case before landing, not only against
  synthetic drift: resolved against the manifest on `origin/main`, it reports
  the block omits `examples.md` — which is #68's entire subject, produced
  mechanically in under a second.
- #68 keeps its trigger and loses its risk. Whenever the bump happens, the
  reconciliation it describes is a test failure with the answer in the message
  rather than a step someone has to remember.
- Four facts remain hand-written and unguarded. If this repository changed stack
  or code host and the axes were not updated, the guard would confidently check
  the wrong chain. That is the irreducible input, and it is the pair ADR-008
  already identified as the axes.
- The reader is this project's own code and can be wrong. It is checked before
  it is trusted: an id it cannot resolve to a file fails its own test first, so
  a dropped edge cannot masquerade as a short block.

## Related

- ADR-008 — the record that resolved both axes, and whose rejected generator
  option this revisits on refuted grounds
- ADR-014 — the neighbouring case of a stated content rule that had no check
  until one was written
- #88 — the issue this closes
- #68 — the open reconciliation whose recurrence this prevents
- #4 — the pin revert that was the other direction of the same drift
