---
id: "025"
status: Accepted
date: 2026-08-28
category: tooling
supersedes: []
superseded_by: []
---

# ADR-025: A wrong lint rule is suppressed at the line, never in the table

**Upstream:** filed as braboj/solid-ai-templates#1240 against
`templates/base/workflow/quality-gates.md`. With the domain skin off, the
convention is that a project adopting a per-file lint freeze also states when
a single finding may be suppressed at its site. The two mechanisms answer
different claims, and only one of them is currently specified.

## Context

Two records already govern suppression here, and neither covers this case.

The lint-freeze record froze the violations that existed on adoption day in a
`per-file-ignores` table, generated from the linter's own output. Its rule is
that an entry is never added and never widened to make a gate pass.

The security-gate record set the shape for a scanner finding: site-local,
naming the specific check, with the reason directly above the line, and the
analysis never turned off tree-wide.

Between them sits a case neither reaches. Retiring the `tests/` slice of the
freeze surfaced a `B017` at
`tests/test_stream_locks.py`, where a test deliberately asserts on a broad
`Exception`. The breadth is the point. Entering an unconstructed
`threading.Lock` raises `AttributeError` on Python 3.10 and `TypeError` on
3.13, and this project runs both in CI, so naming either class writes one
interpreter's answer into a test that runs on both.

`testing-external-definition` asks for exactly that breadth:

> Where the test asserts a misuse fails, assert that it fails, not how

The linter asks for the opposite, and at that site the linter is wrong.

The two available moves were both bad. Narrowing the assertion reintroduces
the platform dependence the test exists to avoid. Adding the file to the
freeze table suppresses `B017` for every other assertion in it, and the
lint-freeze rule forbids the addition anyway.

The templates do not resolve it. `# noqa` appears once in the whole chain, in
a comment-layout rule naming it as an exception to the ban on trailing
comments. No rule says when one may be used.

## Decision

1. **Two claims, two mechanisms** -- the freeze table records "this file was
   already broken on adoption day". A site-local suppression records "this
   rule is wrong at this line". Neither substitutes for the other, and a
   finding that is a genuine defect gets neither.

2. **Form** -- a suppression names the specific rule, never bare, and the
   reason sits in a comment directly above the line. This copies the shape the
   security gate already uses, applied to the linter:

```text
+------------------------------+----------------------------------------+
| the rule is wrong here       | # noqa: RULE, reason in a comment above |
| the file was broken already  | the per-file-ignores table              |
| the finding is a real defect | fix it                                  |
+------------------------------+----------------------------------------+
```

3. **Never bare** -- a bare suppression absorbs every rule that later applies
   to that line. A named one keeps failing on the next finding, which is what
   makes the escape safe to permit.

4. **Never to clear a backlog** -- a suppression is written when the rule is
   wrong at that site, argued in the comment above it. Reaching for one to
   make a slice of the freeze migration finish is the move the lint-freeze
   record exists to prevent, in a smaller form.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Narrow the assertion to the classes seen today | Writes one interpreter's answer into a test that runs on two. The suite would pass on the author's platform and say nothing on the other, which is the failure the testing rule describes. |
| Add the file to the `per-file-ignores` table | Suppresses the rule for every assertion in the file, not the one site. The lint-freeze rule forbids adding an entry to make a gate pass, and the table is meant to shrink. |
| Drop `B017` from the selected rule set | Turns the analysis off tree-wide to accommodate one correct exception. This is the move `quality-gates-retrofit-ratchet` names as the look-alike that leaves no gate behind. |
| Leave it undocumented and rely on review | The tree had no suppression of this kind before, so the next one has no precedent to follow and the form drifts. A bare suppression and a named one are indistinguishable in review at a glance. |

## Consequences

- The repository carries exactly one site-local lint suppression today, at
  `tests/test_stream_locks.py`. Its reason names the two interpreter versions
  and why either class would be wrong.
- The check is a grep, and it is cheap: every suppression names a rule, so
  `grep -rn '# noqa' src tests scripts examples` listing only named forms is
  the pass condition. A bare `# noqa` is the failure.
- This makes it easier to suppress a finding than the freeze alone did, which
  is the cost. Decision 4 is what bounds it, and it is enforced by review rather
  than by a gate.
- The freeze migration is unaffected. A file's entry still comes off by fixing
  its findings, and a suppression written during that work would be visible in
  the diff as an addition rather than a removal.

## Related

- ADR-003 -- the per-file freeze this sits beside
- ADR-007 -- the site-local shape this copies from the security gate
