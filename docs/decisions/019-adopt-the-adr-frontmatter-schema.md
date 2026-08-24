---
id: "019"
status: Accepted
date: 2026-08-24
category: process
supersedes: []
superseded_by: []
---

# ADR-019: Adopt the upstream front-matter schema, decline its prose rule

**Upstream:** filed as braboj/solid-ai-templates#1056 against
`templates/base/core/docs.md`. With the domain skin off, the convention is that
a decision recorded in a repository's own log does not reach the consumers of
what it ships. The follow-up that would carry it into the shipped template is
itself a consequence of that decision, so nothing outside the repository fires
when it never lands.

## Context

Two repositories under the same owner write decision records in two formats,
and each has a defensible claim to be following solid-ai-templates.

The templates repository decided this in its own ADR-010, dated 2026-06-02. It
mandates YAML front matter carrying `id`, `status`, `date`, `category`,
`supersedes` and `superseded_by`, and it ships a `docs/decisions/TEMPLATE.md`
to copy from. All 25 of its own records use it.

The template it ships does not say so. `templates/base/core/docs.md` carries
no mention of front matter and still prescribes the older bold-label form.
ADR-010 lists the reconciliation among its own consequences:

> `templates/base/core/docs.md` ADR rules are updated in a follow-up PR to
> point to the schema (the ADR is the source of truth; docs.md summarizes)

That follow-up never landed. The sibling one for the repository's own context
file was filed and closed; this one appears never to have been filed at all.

So this project read the shipped template and produced bold labels, and its
sibling copied the repository's own template and produced front matter. Both
followed their authority. The ambiguity is upstream, and finding it requires
reading a record that is not part of the chain a consumer resolves.

ADR-010 is explicit about which side wins: the ADR is the source of truth and
the template summarizes it. That settles the direction of this migration.

## Decision

1. Adopt the front-matter schema on every record: `id`, `status`, `date`,
   `category`, `supersedes` and `superseded_by`, with the two list fields
   present even when empty. Front matter is the source of truth for status and
   supersession, and the bold-label `Status` and `Date` fields are removed.
2. The category set is this project's own, and it is closed. Widening it takes
   a new record.

   | category | what it covers |
   | --- | --- |
   | `protocol` | the wire, the packet API, contracts a device sees |
   | `tooling` | linters, type checkers, scanners, the dependency lock |
   | `process` | session protocol, documentation, how decisions are recorded |
   | `release` | versioning, the release record, what ships |
   | `repository` | identity, naming, history, layout |

3. `tests/test_decision_frontmatter.py` is the check. It is the smoke check
   ADR-010 names as a follow-up, built here because this project needs it now.
4. Metadata on a merged record may be updated to record supersession. This is
   ADR-010's own exception to immutability, and it is narrower than the one
   this project already carries for readability.
5. The prose rule is declined. ADR-010 also forbids naming another record in a
   prose body, allowing it only through the link fields and a context-only
   Related section. This project does not adopt that part; see below.
6. The `Upstream:` field stays a bold-label block below the title. It carries
   several sentences of genericized convention rather than a metadata value,
   and a front-matter field is the wrong shape for prose.

```text
   record metadata            record prose
        |                          |
   front matter               body sections
   id/status/date             Context, Decision,
   category                   Alternatives, Consequences
   supersedes/superseded_by         |
        |                     may name another record
   source of truth for        by number, which the
   status and links           upstream rule forbids
        |                          |
   gated by the schema        gated for readability
   check                      and width
```

### Why the prose rule is declined

Measured before deciding: all 18 records cite another record in a prose body,
75 citations in total, with 13 in each of two of them.

The cost is not the edit count. Removing a citation removes the sentence's
subject. ADR-013 exists to correct the baseline ADR-012 established, and its
Context cannot explain what was wrong without naming what it corrects. A link
field records that a supersession happened; it cannot carry why.

It also contradicts a standing rule in this project's own context file, which
holds that a decision record cross-referencing other records by number is
doing its job, and which outranks a pinned template by that file's own
precedence order. Adopting the schema does not require adopting this, because
the schema is the metadata block and this is a separate rule about prose.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Stay on the bold-label format | It is what the shipped template says, and the shipped template is the stale side of an upstream drift its own governing record settles the other way. It also leaves two sibling repositories permanently divergent for no reason either could state. |
| Adopt the schema and the prose rule together | The literal reading of ADR-010, and the one this record declines with data. It would strip 75 citations from 18 merged records, destroy the reasoning that makes supersession legible, and contradict a rule in this project's own context file that outranks the template. |
| Wait for the upstream follow-up to land | Costs nothing to write and defers indefinitely: the follow-up has been outstanding since 2026-06-02, and nothing watches for it. The filing raises the issue; this record stops the project waiting on it. |
| Reuse the upstream category set verbatim | Its five values name the template repository's own domains, including its manifest shape and its sync tooling. A Modbus library has no decision that maps to them, so every record would land in `process` and the field would carry nothing. |
| Skip the category field | The one field with no obvious consumer here, at 19 records. It is also the field that makes a growing log filterable, and dropping it would diverge from the schema for convenience rather than for a reason. |

## Consequences

- The two repositories now write records in one format, and the difference
  that prompted this is gone.
- Supersession is checked in both directions. Neither superseded record
  pointed forward before the migration, and nothing would have noticed.
- The category set is a judgement that will be tested. Five values over 19
  records is thin evidence, and the first record that fits none of them is the
  signal to widen the set rather than to force a fit.
- This project now diverges from the upstream prose rule, deliberately and in
  writing. A reconciliation that touches it must say whether the divergence
  still holds rather than reading it as a gap.
- The check is the smoke check ADR-010 defers to a follow-up. If that follow-up
  ever lands upstream, this project already satisfies it.
- Four gates now read `docs/decisions/`, for characters, readability, width and
  schema. That is the point at which consolidating them is worth considering.

## Related

- ADR-017 — the readability boundary for editing a merged record, which this
  migration stays inside: no prose changed, only the metadata block
- ADR-018 — the width rule the new front matter is measured against
- ADR-001 — adopts the templates whose own governance record this follows
