# ADR-014: Prose may use the em dash; everything else stays ASCII

**Status:** Accepted
**Date:** 2026-08-21
**Upstream:** filed as braboj/solid-ai-templates#1045 against
`templates/base/core/quality.md`. With the domain skin off, the convention is
that a mechanically checkable content restriction must name its check, which
`quality-gates-pair-check` already requires in general and which the ASCII rule
itself does not do — so the one rule in the templates most likely to be
violated by the templates' own prose is also the one with no way to notice.

## Context

`templates/base/core/quality.md` states, under Code style:

> Encode all source files in UTF-8; content MUST be restricted to ASCII
> characters

The repository does not follow it. Measured across tracked files, excluding the
templates submodule and the specification PDFs, 23 files carried 357 characters
outside ASCII:

| character | count | what it is |
| --- | --- | --- |
| U+2014 | 353 | em dash |
| U+0422 | 1 | Cyrillic capital Te |
| U+201C, U+201D | 2 | curly double quotes |
| U+2013 | 1 | en dash |

The distribution is the whole argument. This is not drift in 23 directions; it
is one character used deliberately in prose, plus four accidents hiding behind
it.

The em dash is in the dev journal, every decision record, PLAYBOOK,
CONTRIBUTING, SECURITY, the README and CLAUDE.md. That put two binding rules in
direct conflict, because `ai-workflow-match-convention` makes a document's
prior entries the authoritative template for its format. Writing a new journal
entry in ASCII violates that rule; writing it with an em dash violates the
ASCII rule. There was no compliant option, which is why this is a decision
rather than a cleanup.

The four stragglers are a different thing entirely, and none is a style choice.
A Cyrillic capital Te opened a sentence in the Modbus tutorial where a Latin T
belongs; it renders identically, so no reader would ever see it. A quoted
exception name in `src/pyomb/errors.py` carried curly quotes, and an en dash
stood in for the hyphen in "long-duration".

That those four sat undetected among several hundred deliberate characters is
the point. The rule was stated and never checked, so it decayed exactly as
`quality-gates-pair-check` says a rule with no check decays, and the decay hid
real defects rather than merely permitting a style.

## Decision

1. Markdown prose may use the em dash. It is the only character permitted
   beyond ASCII, anywhere in the repository.
2. Everything that is not Markdown — source, tests, scripts, configuration,
   workflows — is ASCII without exception. `--` is the substitute where a
   comment wants a dash.
3. Markdown may use the em dash and nothing else. A homoglyph, a curly quote or
   an en dash in prose is a defect there exactly as it is in code. The
   allowance is deliberately the narrowest one that lets the documents stay as
   they are, so the class of defect this record was raised by still fails.
4. The rule is enforced by `tests/test_source_is_ascii.py`, which reads the
   tree as git tracks it and reports every offending character as
   `path:line:column U+XXXX`. It runs in the ordinary suite, so it gates on
   every pull request with no new tooling.
5. `RUF002` comes off the `src/pyomb/errors.py` entry in the ruff
   `per-file-ignores` freeze, its two characters having been fixed. ADR-003
   calls shrinking that table the migration.

```text
  tracked file
       |
       +-- *.pdf ------------------> not text, not checked
       |
       +-- *.md -------------------> ASCII + U+2014 only
       |                             (prose keeps its em dash;
       |                              a homoglyph still fails)
       |
       +-- everything else --------> ASCII, no exception
                                     (src, tests, scripts,
                                      pyproject, workflows)
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Convert all 353 em dashes to `--` and hold the rule as written | Fully conformant, and it rewrites every merged decision record and every journal entry to satisfy a rule about characters. `base-docs` permits a content-preserving format migration across merged ADRs, so it is available — but it spends a large diff across immutable records, and the em dash is the house style of every document a reader of this project encounters. The rule exists to keep encoding portable and diffs clean; a single well-supported punctuation mark in Markdown threatens neither. |
| Record the divergence and add no check | Cheapest, and it leaves the acceptance criterion unanswered. It is also precisely how the four stragglers survived: the em dash allowance would have covered them by omission, since nothing would be counting. A divergence without a boundary is not a decision, it is an amnesty. |
| Permit the em dash everywhere, code included | Simpler to state, and it gives up the property worth keeping. Source is read through more tools than prose is — terminals, diff viewers, `grep`, patch files — and a non-ASCII character in a comment buys nothing there. The measurement supports this: after the stragglers, no file outside Markdown carried anything beyond ASCII, so the code side of the rule was already being followed. |
| Enforce with a pre-commit hook instead of a test | A hook is bypassable with `--no-verify` and would need CI duplication anyway. The suite already carries meta-tests of this shape, so a test reuses the gate that exists rather than adding a layer. |
| Widen the allowance to a named set (em dash, en dash, curly quotes) | Each addition removes a defect class from the checker's reach. The en dash and the curly quotes in this tree were both mistakes, not choices; permitting them would have made the two `errors.py` defects permanently invisible. |

## Consequences

- The conflict between the ASCII rule and `ai-workflow-match-convention` is
  resolved in favour of the documents. A journal entry written the way the
  previous entries are written is now compliant.
- Prose gains a check it never had. A homoglyph in Markdown, which is the
  failure mode a human reader cannot catch by reading, now fails the suite with
  a file, line and column.
- The ruff freeze table shrinks by one entry. `src/pyomb/errors.py` is lint-
  clean on `RUF002` rather than exempt from it.
- The project carries a recorded divergence from the pinned templates. Per
  `base-docs`, a reconciliation that touches it must state whether it still
  holds — so a future submodule bump that moves the ASCII rule is read against
  this record rather than as a gap to close.
- The check is one-directional and cheap to widen. Removing the em dash
  allowance later is a one-line change plus a sweep, should the project ever
  decide the templates' rule should hold as written.

## Related

- ADR-003 — the ruff freeze table, and the rule that shrinking it is the
  sanctioned migration
- #80 — the ticket that measured the distribution and refused to sweep in
  either direction without a decision
