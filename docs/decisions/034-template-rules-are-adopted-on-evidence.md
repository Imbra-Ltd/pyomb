---
id: "034"
status: Accepted
date: 2026-09-01
category: process
supersedes: []
superseded_by: []
---

# ADR-034: A template rule is adopted on evidence, not by default

**Upstream:** filed as braboj/solid-ai-templates#1353 against
`templates/base/workflow/scope.md`. With the domain skin off: a vendored rule
set that a project treats as binding on arrival converts every upstream release
into unbudgeted work, and the conversion is invisible because each individual
rule looks reasonable.

## Context

This project vendors its governing rules as a pinned submodule. Moving the pin
imports a range of new rules, and each rule the repository does not yet satisfy
has become a ticket.

Measured on 2026-09-01, over the 156 commits since the first release:

| Area | Lines changed | Share |
| --- | --- | --- |
| `docs/` | 9,352 | 51% |
| `tests/` | 5,802 | 32% |
| config, CI, other | 4,178 | 14% |
| `src/pyomb/` | 605 | 3% |

Of the 27 commits that reached the source, nine were version bumps and about
five were docstring edits. Roughly ten commits in 156 changed what the library
does.

Two further counts point the same way. Sixteen of the twenty-five issues open
that morning traced to the template chain rather than to the product. Seven
session headings in the development journal contain the phrase "bump the pin".

### The mechanism is an asymmetry, not a misjudgement

Adopting a rule needs no argument, because the rule states itself as a MUST.
Declining one needs a decision record. So the cheaper path is always adoption,
and nothing in the sequence asks whether a given rule reduces risk here.

The result is a backlog that grows from an upstream release schedule rather
than from what the library does wrong. The release cut this same day changed
zero lines of library behaviour.

## Decision

| # | Rule |
| --- | --- |
| 1 | A rule is adopted when someone names the defect it would have caught here |
| 2 | Otherwise it is declined in one line, in the pull request or the issue |
| 3 | A decline needs no record and no ticket |
| 4 | The pin still moves for a security fix in anything this project executes |
| 5 | Rules already adopted stay adopted; this governs arrivals |

Rule 3 is the load-bearing one. Requiring a record to decline is what created
the asymmetry, so leaving that requirement in place would preserve it under a
new name.

```text
  a rule arrives
        |
        +--> can you name a defect here it would have caught?
        |        |
        |        yes  -> adopt it, and cite the defect
        |        no   -> one line in the pull request, and stop
        |
        +--> does it fix a security hole in something we execute?
                 yes  -> take it regardless
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the current default | It produced the table above. Three per cent of change reaching the product is the measurement, not an impression |
| Unvendor the rules entirely | Throws away the part that works. The gates on line endings, packaging and release currency each caught something real |
| Adopt everything, but batch it per release | Changes the arrival rate and not the total. The work still lands, and batching hides which rule caused which ticket |
| Cap process work as a ratio of product work | Attractive and unenforceable. It needs a classifier for every change, and the argument would move to the classification |
| Freeze the pin permanently | Confuses the symptom with the cause. The pin is fine to move; adopting its contents unexamined is not |

## Consequences

- The backlog stops growing from an upstream release schedule. What remains is
  what the library does wrong, which is the list worth having.
- Some rules that would have caught a future defect will be declined. That
  cost is real and is accepted, because the evidence bar is the only thing
  that distinguishes a useful rule from a plausible one.
- A declined rule leaves no trace, so the same rule may be re-argued when the
  pin next moves. Cheaper than the record it replaces.
- The startup block still requires reading the pinned files in full. This
  changes what obliges the project, not what informs it.
- The pin stays where it is until the product backlog is clear or a named
  defect reopens the question. The tracking issue was closed with that trigger
  rather than left open.
- Whoever applies this can be wrong about a rule. Being wrong about a rule
  costs one defect; being wrong about the default cost this project a
  fifty-one per cent documentation share.

## Related

- ADR-001 -- the decision to vendor the rule set that this one governs the
  adoption of.
- #208 -- the pin bump closed with the trigger this record states.
