# ADR-017: Decision records carry bounded sentences, and a readability edit preserves immutability

**Status:** Accepted
**Date:** 2026-08-24
**Upstream:** filed as braboj/solid-ai-templates#1054 against
`templates/base/core/docs.md`. With the domain skin off, the convention is that
a format-migration exemption which enumerates permitted operations is
under-inclusive by construction. It omits the one edit an immutable record most
needs, restructuring that changes no claim, so the record stays permanently
unreadable and the rule protecting it is what keeps it that way.

## Context

A decision record is read once, months after it merges, by someone deciding
whether the decision still holds. What costs that reader is not length. It is a
single sentence carrying an enumeration, where three reasons are chained on
semicolons and the first must be held intact while the third is parsed.

The records here had drifted into exactly that shape, and nothing measured
them. Across the sixteen records that existed when this was written, the corpus
is 665 sentences, 128 prose paragraphs and 224 list items.

| corpus | median sentence | p95 | p99 | longest |
| --- | --- | --- | --- | --- |
| the 71 pinned template files | 11 | 31 | 42 | 71 |
| `README.md` and `CLAUDE.md` | 12 | 32 | 37 | 41 |
| `docs/decisions/`, before this record | 16 | 36 | 50 | 73 |

The distribution is the argument. The records run half again the sentence
length of the prose the project is measured by, and the tail is worse than the
median suggests. It holds 17 sentences past 40 words and 5 paragraphs past 80,
spread across 13 of the 16 files.

The offenders shared one shape. Every one carried a list written as a sentence.
The worst ran 73 words and held three reasons on semicolons. The most frequent
was the `**Upstream:**` block, where 8 records each packed a whole argument into
a single sentence. Seven of them hinged on an interpolated em dash.

That shape is why the fix is safe. A sentence that already contains a list can
be rendered as a list without touching a word of the argument, so the edit is
mechanical and its correctness is checkable by reading a word-level diff.

The obstacle is that `base-docs` makes a merged record immutable. It permits a
content-preserving format migration, but enumerates what that covers: headings,
titles, filenames and cross-links. Restructuring prose is not on the list, and
9 of the 22 offenders sit in the `**Upstream:**` block, which is project front
matter rather than one of the four sections the rule names.

## Decision

1. Every sentence in a decision record is at most 40 words, and every prose
   paragraph at most 80. The limits are calibrated, not chosen: 40 is where the
   pinned templates' own 99th percentile sits and where this project's tightest
   prose tops out, and 80 is two sentences at that limit.
2. `tests/test_decisions_are_readable.py` is the check, and it runs in the
   suite like any other gate. A limit without a check is decorative, which is
   how the ASCII rule went unenforced until a test was written for it.
3. The gate reads fenced blocks, tables, headings and block quotes past. A
   quotation of a pinned template is the rule a record is measured against, and
   rewriting one to fit a limit would falsify it.
4. The sentence limit applies to list items as well as paragraphs. Without
   that, a long sentence is legalised by putting a bullet in front of it.
5. A readability edit to a merged record that changes no claim is a
   content-preserving format migration, and needs no superseding record. The
   commit states that it is readability-only, and a word-level diff is what
   demonstrates it.
6. An edit that changes what a record claims is a new decision and takes a new
   record. The boundary is the claim, not the byte.

```text
   a merged record, hard to read
              |
              v
   +--------------------------+
   |  does the edit change a  |
   |  claim the record makes? |
   +--------------------------+
        |                | yes
     no |                v
        |        +------------------+
        |        | a new record     |
        |        | supersedes it    |
        v        +------------------+
   +--------------------------+
   | edit in place; the diff  |
   | shows only connectives   |
   | and capitalisation       |
   +--------------------------+
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Bind new records only, leave the merged ones | Fully conformant, and it leaves the problem the owner raised untouched. The records that are hard to read are the ones already merged, and every future record ages into that same protected state. |
| A superseding record per rewritten file | The strictly conformant reading. It would produce roughly a dozen records whose only content is that the previous one was hard to read, burying the decision log this rule exists to serve. |
| Rewrite freely, record nothing | Cheapest, and it is the option this record exists to reject. A merged record edited without a stated boundary is indistinguishable from a decision quietly changed after the fact. |
| A prose convention with no check | Lower ceremony and no threshold to argue about. It also decays silently, because an over-long sentence looks identical to a short one until something counts it. |
| Cap words per line rather than per sentence | Already covered by the line-length limit, and it measures the wrong thing. A 73-word sentence wrapped at 80 columns satisfies it while reading exactly as badly. |
| Extend the gate to the journal and PLAYBOOK | The journal is worse than the records on every measure, with a 128-word sentence and list items past 200. It is a session log written at speed, its entries are append-only history, and holding it to a record's bar is a separate decision. |

## Consequences

- The records are measurably readable and stay that way. The gate fails on the
  next over-long sentence rather than leaving it for a reader to hit months
  later.
- 13 of the 16 merged records were edited. No claim in any of them changed, and
  the word-level diff shows only connectives, capitalisation and the bullets
  that replaced three buried enumerations.
- The project carries a third recorded divergence from the pinned templates.
  A reconciliation that touches the format-migration rule must state whether
  this one still holds rather than reading it as a gap to close.
- The em dash is now rarer in the records, because the interpolation it enabled
  was the most common way a sentence ran past the limit. Nothing forbids it,
  and the allowance that permits it is unaffected.
- The journal and PLAYBOOK are ungated and measure worse. That is recorded here
  rather than fixed, and the table above is the evidence whenever it is picked
  up.

## Related

- ADR-014 — the precedent this follows exactly: a prose rule the templates
  state, a divergence the project records, and a test that makes the rule
  enforceable rather than decorative
- ADR-016 — the other recorded divergence, and one of the records edited here
- ADR-001 — adopts the templates whose format-migration rule this bounds
