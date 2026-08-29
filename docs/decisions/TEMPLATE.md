---
id: "NNN"
status: Proposed
date: YYYY-MM-DD
category: process
supersedes: []
superseded_by: []
---

# ADR-NNN: Title in sentence case

<!--
id matches the filename's leading digits. status is Proposed, Accepted or
Superseded. date is the day status last changed. category is one of protocol,
tooling, process, release or repository -- a new one takes its own record.
Both link fields are present even when empty. Superseding an earlier record
updates both sides in the same change.

Keep the title under 80 columns, every sentence to 40 words and every
paragraph to 80. A sentence that runs long is almost always carrying a list;
render it as a list.
-->

**Upstream:** filed as owner/repo#NNNN against `templates/path/to/file.md`, or
`none` with the reason. State the convention with the project's domain nouns
removed, so it reads as a rule that stands on its own.

## Context

<!--
Why this decision is needed now. What exists, what does not work, and what
changed to surface it. Descriptive, not prescriptive -- the Decision section
makes the call, this one shows the call is necessary. Measure rather than
assert: a threshold, a count or a distribution belongs here, with the command
that produced it.
-->

## Decision

<!--
What is decided, in imperative voice with RFC 2119 keywords. Number multi-part
decisions:

1. **Short label** — the rule
2. **Short label** — the next rule

One concern per record; multi-part decisions are allowed within it. A
non-trivial record carries an inline diagram here, in a ```text fence. Plain
ASCII (+ - |) and Unicode box-drawing both stay legible in a monospace font,
so use whichever reads better.
-->

## Alternatives considered

<!--
What was rejected and why, as a two-column table where the content fits. The
option that was nearly taken belongs here with the reason it was not, not
omitted because it lost.
-->

| Alternative | Why rejected |
| --- | --- |
| ... | ... |

## Consequences

<!--
What follows. Files that must change, follow-up work, constraints introduced
or removed, and what this makes harder. A consequence that is only good is
usually an incomplete list.
-->

## Related

<!--
Optional context-only pointers to other records and issues. Remove the section
if there is nothing genuinely related.
-->
