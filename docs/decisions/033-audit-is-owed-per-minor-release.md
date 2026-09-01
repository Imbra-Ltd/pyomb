---
id: "033"
status: Accepted
date: 2026-08-31
category: release
supersedes: []
superseded_by: []
---

# ADR-033: The 360-degree audit is owed per minor release, not per release

**Upstream:** filed as braboj/solid-ai-templates#1337 against
`templates/base/core/git.md`. With the domain skin off: a periodic review
attached to every release event decays into a formality, because most events
change nothing the review reads. Scope it to the events that add what is
reviewed.

## Context

The release procedure requires a 360-degree audit before a release. The gate
refuses a release whose newest record in `docs/audits/` predates the release
before it. Declining is allowed and takes a dated skip record.

The audit is nine engineering dimensions reviewed one at a time. It costs about
half a day and produces a report.

Two releases in a row declined it. Version 0.4.2 wrote a skip record. Version
0.4.3 reused that record, after the comparison was loosened to accept a
same-day date.

Three releases then rested on the 2026-08-29 report. The skip record says so in
its own addendum, and names the cost: the deferral is open-ended rather than
dated, and nothing watches it.

### What the two declines have in common

| Release | What it carried | Dimensions it moved |
| --- | --- | --- |
| 0.4.2 | documentation, a test policy change | none |
| 0.4.3 | a gate comparison, a record, documentation | none |

Neither release changed a source module. A review of nine engineering
dimensions had nothing new to read, so the operator wrote a document saying so.

### The position that briefly stood in its place

The next audit was scheduled for the point at which the open backlog reaches
zero. The backlog is 27 issues. That is a condition rather than a date, nothing
polls it, and no release would meet it.

## Decision

| # | Rule |
| --- | --- |
| 1 | A minor or major release owes the audit |
| 2 | A patch release owes nothing, neither audit nor skip record |
| 3 | The gate reads the patch component and returns early when it is not zero |
| 4 | A version the gate cannot read is a finding, never a pass |
| 5 | The admitted case carries its own assertion |

```text
   version being cut    newest record     verdict
   -----------------    -------------     -------
   0.4.4  patch         2026-08-20        pass   no audit is owed
   0.4.4  patch         (none)            pass   no audit is owed
   0.5.0  minor         2026-08-20        fail   older than 0.4.4
   0.5.0  minor         (none)            fail   nothing recorded
   0.5.0  minor         after 0.4.4       pass
   not-a-version        (any)             fail   cannot tell what is owed
```

Rule 4 is the one that is easy to omit. An unreadable version and a patch
version both mean the comparison does not run. Reading them alike would turn a
typo in the version literal into a silent exemption.

Rule 5 covers a hazard specific to this gate. Its fixtures named a patch
version, so narrowing the rule without moving them would have retired every
negative control while the suite stayed green.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the audit on every release | The status quo, and two consecutive declines are what it produced. A rule dischargeable by writing a document trains the operator to write the document |
| Defer until the backlog reaches zero | The position this replaces. Nothing watches the count, on a backlog of 27, so it schedules nothing and no release meets it |
| Run the audit on a calendar, monthly or quarterly | Decouples the review from what it reviews. A quiet month gets an audit, and a month landing a new public surface may not |
| Scope by diff rather than by version | Closest to the real question, since what matters is whether source changed. It needs a threshold for how much change is enough, and that number has no principled value |
| Delete the gate | Returns the project to four releases cut with no audit, three leaving no trace. What failed here is the cadence, not the enforcement |

## Consequences

- A run of patch releases can go a long time with no audit. The next minor
  bounds it, and that bound is a version number rather than a condition.
- The obligation now lands where new surface arrives, which is what makes
  running the audit cheaper than declining it.
- The live assertion passes without comparing anything while the package
  reports a patch version. No green run distinguishes that from a real pass, so
  the fixture tests carry the rule in that state.
- A skip record stays available for a minor or major release. What it stops
  being is the routine way to clear a release.
- Version 0.4.4 is the first release cut under this rule, and it is the change
  carrying it. The gate on that branch is the narrowed one, so it clears its
  own release.
- Version 0.5.0 will fail until a report postdates 0.4.4. The 2026-08-29 report
  does not, so the audit is owed before that release rather than deferred.

## Related

- ADR-027 -- the decision that introduced this gate and chose the changelog as
  its input.
- ADR-032 -- the same-day comparison this narrowing sits on top of.
- #243 -- the issue this record closes.
