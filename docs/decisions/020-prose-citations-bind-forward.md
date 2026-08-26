---
id: "020"
status: Accepted
date: 2026-08-26
category: process
supersedes: []
superseded_by: []
---

# ADR-020: The prose-citation rule binds new records only

**Upstream:** filed as braboj/solid-ai-templates#1104 against
`templates/base/core/docs.md`. With the domain skin off, the convention is that
a rule constraining the form of documents that are immutable once merged has to
say whether it binds forward or retroactively. The two readings differ by an
unbounded amount of work, and by whether the existing corpus is compliant or in
violation.

## Context

`templates/base/core/docs.md` arrived at `v2.46.0` carrying a new rule:

> ADRs MUST NOT cite other ADRs in their prose body -- the only ADR-to-ADR
> links are the frontmatter `supersedes` and `superseded_by` fields, which are
> the only ones a check can validate.

A closing section of context-only pointers is still permitted, provided nothing
in it is decision-bearing.

Nineteen records were merged before that rule existed. Fourteen of them cite
another record in a prose body, and eight of those carry the citation inside
the Decision section:

```bash
for f in docs/decisions/[0-9][0-9][0-9]-*.md; do
  own=$(basename "$f" | cut -c1-3)
  awk '/^## Decision/{p=1;next} /^## /{p=0} p' "$f" \
    | grep -oE "ADR-[0-9]{3}" | grep -v "ADR-$own" | sort -u \
    | sed "s|^|$(basename "$f") |"
done
```

That second number is the one that decides this. A citation inside a Decision
section is frequently the decision itself rather than a pointer beside it. One
record decides nothing except that an evidence table belonging to the record it
supersedes is withdrawn, and that the rest of it stands. Move the reference and
the decision stops saying anything.

The same file declares merged records immutable, with two narrow exceptions:
supersession metadata, and a content-preserving format migration that changes
no decision prose. Neither exception reaches a load-bearing citation. So the
two rules point opposite ways, and nothing in the template says which wins.

## Decision

1. **Forward only** -- the prohibition binds records numbered 020 and above.
   A record merged before this one keeps its prose citations unchanged.
2. **Immutability outranks a later formatting rule** -- rewriting fourteen
   merged records to satisfy a rule that arrived after they merged is not a
   format migration, because for eight of them it would change what the
   Decision section means.
3. **The boundary is checked, not remembered** --
   `tests/test_decision_citations.py` fails a record at or above the boundary
   that names another record outside its closing pointers section. Fenced
   blocks are skipped, so a record quoting the rule or the command that
   measures it does not fail itself.
4. **This record obeys the rule it sets** -- the counts above are given as
   measurements with the command that produces them, and no record number
   appears in this body. The boundary is the first record the check covers,
   not the first one exempt from it.
5. **The exemption is scope, not suppression** -- a merged record that is ever
   superseded gets the ordinary treatment, and the superseding record is
   authored under the rule like any other.

```text
   a decision record
          |
          v
   +----------------------------+
   |  numbered below 020?       |  yes
   +----------------------------+-----> prose citations stay as written;
          | no                          the check does not read it
          v
   +----------------------------+
   |  names another record       |  yes
   |  outside Related?           |-----> the check fails it
   +----------------------------+
          | no
          v
   frontmatter and Related carry every link
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Rewrite all fourteen records, moving citations into the closing section | The compliant-looking option, and it is not available. Eight of the fourteen carry the citation inside a Decision section, where moving it changes what was decided -- so it is a decision change, which needs a new record rather than an edit. The remaining six would be a genuine format migration, but splitting the corpus into "migrated" and "could not be migrated" leaves a reader unable to tell which state a record is in. |
| Supersede each affected record | Honest about the immutability rule and absurd in practice. It produces fourteen supersessions that change no decision, doubles the size of the directory, and buries five real supersessions among them. |
| Record nothing and rely on the rule reading as forward-binding | Cheapest, and it is how a rule with no boundary decays. The corpus reads as fourteen standing violations, so the next reader files it as debt and someone eventually attempts the rewrite this record exists to refuse. |
| Gate every record and add the fourteen to a suppression list | Reuses a mechanism the project already has, and it is the wrong shape. A freeze table records what was broken on the day it was written; this is a scope boundary, and the records below it are not broken. |
| Set the boundary at the tag rather than at a record number | More precise about when the rule arrived, and unusable as a check. A record carries its number in its filename and its frontmatter; deriving which template version was pinned when it merged needs history nothing reads at test time. |

## Consequences

- The check covers this record and everything after it, so the rule holds from
  here without a migration. Fourteen records stay exactly as merged.
- A reader of an older record still meets prose citations. That is now a stated
  property of records below the boundary rather than an inconsistency, and the
  boundary is one constant in one test module.
- The project gains a fourth prose gate over the decision records, beside the
  character set, the readability limits and the width. They read the same
  tracked-file list and share a shape, which is worth consolidating if a fifth
  appears.
- A record that quotes the rule, or the command that measures it, has to keep
  that text inside a fenced block. This is a real constraint on how such a
  record is written and the reason the check skips fences.
- Nothing here reduces what the frontmatter carries. Supersession links stay
  the only machine-checkable relationship between records, which is what the
  upstream rule was after.

## Related

- ADR-017 and ADR-018 -- the neighbouring gates over the same directory, whose
  shape this check follows
- ADR-019 -- the frontmatter schema that makes the link fields authoritative
- #110 -- the issue that carries the per-record table of which record cites
  which, kept out of this body so this record obeys its own rule
