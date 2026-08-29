---
id: "029"
status: Accepted
date: 2026-08-29
category: process
supersedes: ["014"]
superseded_by: []
---

# ADR-029: Markdown carries any visible character

**Upstream:** filed as `none`. There is nothing to contribute, because this
converges on the position the pinned templates already hold. The general
convention -- a charset restriction serves the tools that read a file, so it
binds source and stops at documentation -- is `quality.md`'s own, and this
record only retires a local rule that was stricter than it.

## Context

The character-set rule this replaces held every tracked file to printable
ASCII and allowed Markdown past it by exactly one character, the em dash.

The templates narrowed their own ASCII rule to identifiers at `v2.46.0`, and
say in as many words that comments, docstrings, string content and
documentation carry no charset restriction. This project's rule was therefore
the stricter of the two rather than a departure from it. That reading was
re-confirmed against `v2.61.0`, which left the character-set rules untouched.

An architecture direction document surfaced the cost. It draws its layer
diagrams and its pipeline in box-drawing characters, and carries 744
characters outside ASCII across 13 code points:

```text
py - <<'EOF'
import collections, pathlib
text = pathlib.Path(<the document>).read_text(encoding="utf-8")
bad = collections.Counter(c for c in text if ord(c) > 127)
print(sum(bad.values()), len(bad))
for c, n in sorted(bad.items(), key=lambda kv: -kv[1]):
    print("U+%04X x%d" % (ord(c), n))
EOF
```

U+2500 accounts for 636 of them and U+2502 for 69. The rest are the corners,
the tees and three arrows. Not one is a defect, a homoglyph or an accident.

The stricter rule made that document uncommittable without redrawing every
diagram. The inherited docs template blesses plain ASCII and Unicode
box-drawing equally, and says to use whichever reads better, so the local rule
forbade a form the rule it extends explicitly permits.

The benefit being bought was homoglyph detection in prose. The original
measurement found four defects hiding among several hundred deliberate em
dashes, and one was a Cyrillic capital Te opening a sentence in the imported
tutorial. That is a real class, and it is not the class the rule is now being
paid for on every document a reader sees.

## Decision

1. **Markdown carries any character a reader can see** -- box-drawing, arrows,
   punctuation, any script. No printable character is a defect there.
2. **Control characters remain a defect everywhere** -- U+0000 to U+001F and
   U+007F to U+009F, with tab and newline excepted. They render as nothing, so
   reading cannot catch them.
3. **Everything that is not Markdown stays printable ASCII** -- source, tests,
   scripts, configuration and workflows, without exception. `--` is the
   substitute where a comment wants a dash.
4. **The gate keeps two halves and two coverage floors.** Each half is read by
   one rule, so a floor on the total would pass while one rule read an empty
   list.

```text
  tracked file
       |
       +-- *.pdf ------------------> not text, not checked
       |
       +-- *.md -------------------> any visible character
       |                             (control characters fail:
       |                              they render as nothing)
       |
       +-- everything else --------> printable ASCII, no exception
                                     (src, tests, scripts,
                                      pyproject, workflows)
```

Rule 2 is the half that is load-bearing beyond its own gate. A single NUL
makes git classify a file as binary, which stops `text=auto` normalising its
line endings and makes `git ls-files --eol` report `-text` where a value
belongs. That is how the dev journal came to be stored with 1127 CRLF endings
while the line-ending gate read a clean tree.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the rule and redraw every diagram in `+ - \|` | Conformant, and it charges the rule's price to every document rather than settling whether the price is worth paying. The docs template treats the two diagram styles as equals, so the redraw buys nothing a reader can see. It also has to be paid again by the next document, which is what makes it a standing tax rather than a one-off cleanup. |
| Drop Markdown from the gate entirely | Simplest to state, and it matches the upstream rule verbatim. It also gives up control-character detection in prose, and the line-ending gate depends on that: a NUL blinds it silently, and this was the only thing watching for one. Losing a check another check leans on is worse than the restriction it removes. |
| Widen the allowance to a named set of characters | Every diagram then needs its characters approved in advance, and the next document arrives with one that is not on the list. A list of permitted glyphs is a rule that fails open on the author's patience and closed on nothing useful. |
| Keep printable ASCII and add a confusables list for prose | Preserves the homoglyph detection, and costs a table of Cyrillic and Greek look-alikes to maintain forever against a defect class measured once. The detection is worth having and is not worth a hand-curated Unicode table in this repository. |

## Consequences

- Homoglyph detection in prose is gone. A Cyrillic Te where a Latin T belongs
  now passes, and nothing else in the tree is looking for one. This is the
  cost of the decision, not a side effect of it.
- Curly quotes and en dashes in Markdown stop being defects. Neither is swept
  in either direction; the documents are left exactly as they are.
- Control-character detection survives on both halves, so the line-ending gate
  keeps the check it silently depends on.
- The em dash allowance becomes moot rather than removed. Prose may use it,
  and may equally use anything else visible.
- The width rule is unchanged and counts characters rather than bytes, so a
  box-drawing character costs one column and not three.
- The project no longer diverges from the pinned templates on documentation.
  It stays stricter than them on source, which is a narrower divergence and
  still needs re-reading when `quality.md` moves.
- The context file, `PLAYBOOK.md` 3.13 and the reconciliation note in
  `PLAYBOOK.md` 4.1 are corrected in the same change as this record.

## Related

- ADR-018 -- the width rule, which counts characters and is what keeps a wide
  character costing one column.
- ADR-022 -- the control that keeps each half of this gate carrying a coverage
  floor rather than a non-empty check.
- Issue #222 -- the measurement that surfaced the cost and the acceptance
  criteria the change was held to.
