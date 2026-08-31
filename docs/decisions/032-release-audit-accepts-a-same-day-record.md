---
id: "032"
status: Accepted
date: 2026-08-31
category: release
supersedes: []
superseded_by: []
---

# ADR-032: The release-audit gate accepts a same-day record

**Upstream:** candidate for `templates/base/core/git.md`, filed as an issue on
the templates repository. The shape is reusable: a currency gate comparing
dates that carry no time must compare non-strictly, or two events on one day
become unreachable.

## Context

The release-audit gate requires the newest dated record in `docs/audits/` to
be newer than the release before the one being cut. The comparison was strict.

Version 0.4.2 shipped on 2026-08-31. Cutting a second release that day was
then impossible. The comparison reads the previous release's changelog date,
and no record can carry a date later than today.

Declining the audit did not help either. A skip record names the release and
the reason, and one dated the release day failed the same comparison. The step
had no satisfiable form that day.

That matters because the step is declinable by design. A judgement call an
operator is invited to make, and cannot make, is worse than a rule that simply
refuses.

Strictness was chosen deliberately and for a real reason. Dates carry no time,
so an audit written the morning before a release and one written the evening
after it are the same string. Refusing both was the safe reading.

## Decision

1. **Compare non-strictly** -- the newest record clears the gate when it is
   not older than the previous release. A record older than that release still
   fails, and no record at all still fails.
2. **One same-day record covers both releases** -- a single report or skip
   clears the gate for two releases cut on one day. That is the purpose of the
   change, not a side effect of it.
3. **The admitted case carries its own assertion** -- a loosening that nothing
   pins reads as an oversight to whoever later tightens the rule back.

```text
   previous release        newest record        verdict
   ----------------        -------------        -------
   2026-08-31              2026-08-20           fail   record is older
   2026-08-31              (none)               fail   nothing recorded
   2026-08-31              2026-08-31           pass   was fail before this
   2026-08-31              2026-09-01           pass
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the strict comparison and cut the release the next day | Free and correct, and it makes the calendar a release input. Waiting a day to satisfy a rule nothing can satisfy is a cost with no matching risk |
| Record a timestamp instead of a date | Removes the ambiguity properly, and renames every record in `docs/audits/`. The date is carried in the filename, which two gates and the readability suite read |
| Detect the release branch and exempt it | The gate is unconditional by an earlier decision. That property is what keeps it silent between releases, and a branch name is not reliably readable in CI |
| Delete the gate | Returns the project to the state that produced four releases cut with no audit, three leaving no trace. The ambiguity strictness guarded is far narrower than that |

## Consequences

- A same-day record written before the release passes while covering none of
  the changes that release carries. That is what strictness bought, and it is
  what this gives up.
- The loss is bounded by what the gate is for. It catches a record older than
  the previous release and a missing one, and neither case moves.
- The four releases cut with no audit fail the gate in either form, so the
  case it was written for is untouched.
- Two releases on one calendar day are now reachable. Nothing else in the
  release procedure assumes one release per day.
- The gate's negative controls lost the same-day break and gained a positive
  control in its place, so the admitted case fails loudly if it is reverted by
  accident.

## Related

- ADR-027 -- the decision that introduced this gate and chose the changelog as
  its input.
