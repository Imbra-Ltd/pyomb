---
id: "018"
status: Accepted
date: 2026-08-24
category: process
supersedes: []
superseded_by: []
---

# ADR-018: Markdown prose wraps at 80 columns

**Upstream:** filed as braboj/solid-ai-templates#1055 against
`templates/base/core/docs.md`. With the domain skin off, the convention is that
a formatting rule stated only for code is not stated for the prose around it.
An `.editorconfig` width and a contributor guide's Code style section both stop
at the source tree, so the documents keep a width by hand that nothing writes
down and no gate reads.

## Context

The documents already wrap at 80. The agent context file, the README,
CONTRIBUTING, PLAYBOOK, ONBOARDING, the journal, the audits and the decision
records all keep it, and kept it before anything checked.

What was missing is the rule. `.editorconfig` sets a maximum width under
`[*.py]` and gives Markdown only an indent size. CONTRIBUTING states 120 with
80 recommended, under a heading that reads Code style. Neither reaches prose.

So the width was real, unwritten, and held by hand. It was also already
slipping: a 98-column heading reached a green pipeline earlier the same day,
because no gate in the project reads the width of a Markdown line.

Measured across every tracked Markdown file, 165 lines run past 80 columns:

| where | lines | what they are |
| --- | --- | --- |
| `docs/Open_Modbus_Tutorial.md` | 160 | imported with the v0.1.0 tree, wrapped at about 96 |
| `README.md` | 2 | badge links, two long URLs and a label |
| everything else | 3 | genuine, and each wraps in one edit |

The tail is what makes the rule cheap. Outside one imported document and two
badge lines, the whole tree was three edits away from a convention it had been
keeping by hand since the repository was created.

## Decision

1. A Markdown line is at most 80 columns, counted in characters rather than
   bytes. The em dash the prose rule permits is three bytes in UTF-8, and
   counting bytes would charge a document three columns for one glyph.
2. `tests/test_markdown_line_width.py` is the check, and it runs in the suite
   like any other gate.
3. Three kinds of line are exempt, each because it cannot be wrapped rather
   than because it is inconvenient. A table row carries its columns on one
   line. A fenced block holds commands and output, where a break changes what
   the reader copies. A line carrying a URL cannot be split at all.
4. A relative link is not exempt. It is short, and the prose around it wraps
   like any other.
5. `docs/Open_Modbus_Tutorial.md` is outside the rule. It arrived with the
   v0.1.0 import rather than written to this convention, it is internally
   consistent at its own width, and rewrapping 160 lines would bury a change
   nobody asked for. A second test asserts the exclusion still names a tracked
   file, so a rename cannot leave it pointing at nothing.
6. The exclusion is the rule's scope, not a suppression inside it. A document
   this project authored gets no such escape, and the way to remove this one is
   to rewrap the tutorial.

```text
   a tracked .md line
          |
          v
   +---------------------------+
   | in a fence, a table row,  |  yes
   | or carrying a URL?        |------> not measured
   +---------------------------+
          | no
          v
   +---------------------------+
   | in the imported tutorial? |  yes
   +---------------------------+------> outside the rule's scope
          | no
          v
     at most 80 columns
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Leave it unwritten and hold it by hand | It is what the project was doing, and it had already produced a 98-column heading that passed every check. A convention with no check decays silently, because a long line looks like a short one until something counts it. |
| Gate only `docs/decisions/` | Matches the neighbouring readability gate's scope and is narrower than the convention. The width is kept by the README, CONTRIBUTING and PLAYBOOK too, and scoping the check below the convention leaves most of it unenforced. |
| Set the limit at 100 | Nothing outside the imported tutorial would have had to change, which is the appeal and the objection. The documents sit at 80, so a 100 gate would ratify a width nothing uses and permit drift up to it. |
| Rewrap the imported tutorial to 80 | Removes the exclusion entirely. It is a 160-line diff on protocol reference material nobody asked to touch, and it would bury the change it rides along with. |
| Adopt markdownlint | A maintained tool with this rule built in, and many others. It is a new toolchain and config for one line-width check, where the project already has the test-as-gate pattern and two modules using it. |
| Set `max_line_length` for `[*.md]` in `.editorconfig` | The natural home, and it should be set. It is an editor hint that no CI step reads, so it guides an author and gates nothing. |

## Consequences

- The width is now written down and checked, in a project that had been keeping
  it on discipline alone.
- Three lines were rewrapped, in CONTRIBUTING and two merged decision records.
  No word moved in any of them, which a word-level diff shows, so the two
  record edits are the format migration their own rule permits.
- The imported tutorial is the one document outside the rule, and the exclusion
  is asserted rather than assumed. It is also the obvious thing to reconsider,
  since removing it is a mechanical rewrap whenever the churn is acceptable.
- A badge line stays exempt, so the README's link block is never measured. That
  is a real hole: any line can be excused by putting a URL in it. It is
  accepted because the alternative flags a line no author can fix.
- The project has three prose gates now, for characters, readability and width.
  They read the same tracked-file list and share the same shape, which is worth
  consolidating if a fourth appears.

## Related

- ADR-017 — the neighbouring gate, bounding sentences and paragraphs in the
  decision records, and the record whose 98-column heading exposed this gap
- ADR-014 — the first prose rule with a test behind it, and the pattern both
  later gates follow
