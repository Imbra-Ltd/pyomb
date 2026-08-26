---
id: "022"
status: Accepted
date: 2026-08-26
category: process
supersedes: []
superseded_by: []
---

# ADR-022: A document gate asserts the floor it read

**Upstream:** filed as `none`. Everything this implements is already in
`templates/base/core/testing.md`: a negative assertion asserts its inputs were
reached, the coverage assertion is its own test, and a corpus with a known
floor asserts the floor rather than non-emptiness. What is not upstream is an
answer to the unstaged-file gap the same file names. One project meeting it
once is not evidence an answer generalizes; revisit if a second project hits
it.

## Context

Six checks read documents and assert that a list of violations is empty. Each
enumerates its corpus through `git ls-files` and reports on what comes back.

A test asserting nothing was found passes identically when nothing was
examined. It cannot tell a clean tree from an unread one.

A negative control measured which ones could tell. It patched each module's
enumeration to return nothing and ran that module's tests:

```text
test_decision_citations           3 ran, 2 failed/errored  catches it
test_decision_frontmatter         3 ran, 0 failed/errored  BLIND
test_decisions_are_readable       2 ran, 0 failed/errored  BLIND
test_markdown_line_width          3 ran, 1 failed/errored  catches it
test_source_is_ascii              2 ran, 0 failed/errored  BLIND
test_line_endings                 6 ran, 1 failed/errored  catches it
```

The three blind ones enforce the character set, the readability limits and the
frontmatter schema. Each is the enforcement mechanism of a divergence this
project recorded, so each recorded rule was resting on a check that could not
report having run.

The three that caught it did so by accident rather than by design. One failed
on an exclusion naming a file it no longer found. Two asserted their listing
was not empty, and one of those also errored on an empty `max()`.

The non-empty assertion is the weakest of them. A listing holding a single file
satisfies non-emptiness while measuring almost nothing, so it catches a total
break and misses a filter that drops all but one entry.

There is a second hole in the same enumeration. `git ls-files` reads the
index, so a document written but not yet staged is invisible to all six.

## Decision

1. **Coverage is its own test** -- each gate carries one test asserting its
   enumeration reached the corpus, separate from the tests asserting the rule.
   A broken enumeration and a violating document want different fixes, and one
   test reports whichever fires as the same red.
2. **A floor, not a non-empty check** -- the assertion names a count the corpus
   is known to hold. This is the case non-emptiness misses: a listing returning
   one entry passes it while measuring nothing.
3. **The floor is measured, and its margin is stated** -- an append-only corpus
   takes the measured count, since a record merges and is never deleted. A
   churning corpus takes roughly half, so an ordinary deletion cannot fail a
   character-set rule. Every break mode observed returns nothing at all, so the
   margin costs no detection.
4. **Coverage reaches past the file list** -- the readability gate also floors
   the sentences it measured, because a unit reader returning nothing leaves
   both limits asserting over an empty set. The character-set gate floors each
   half of the tree, because its two rules read one each.
5. **The unstaged gap is recorded, not closed** -- the enumeration keeps
   reading the index. Each gate's coverage message names the gap, so the
   maintainer who adds a document and meets a floor reads the fix rather than
   deducing it.
6. **The control ships as a test** -- the measurement above runs on every
   pull request rather than once. It discovers its subjects by how they read
   their corpus, so a seventh gate is covered without anyone remembering to
   register it. It blinds each one through the call they share rather than
   through the name each gives its own enumeration.

```text
   a document gate runs
            |
            v
   +-----------------------------+
   |  did the enumeration reach  |  no
   |  the floor the corpus holds |-----> the coverage test fails, naming
   +-----------------------------+       the enumeration
            | yes
            v
   +-----------------------------+
   |  does a document break      |  yes
   |  the rule                   |-----> the property test fails, naming
   +-----------------------------+       the document
            | no
            v
   the rule was applied, and a pass now says so
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Enumerate the working tree instead of the index | Closes the unstaged gap and opens a worse one. A local scratch document would fail a run that CI passes, because CI checks out clean and carries no untracked files at all. The gate would report a defect that exists on one machine. |
| Add untracked-but-not-ignored files to the listing | The narrower form of the same trade, and it reads git's own view rather than walking the filesystem. It still fires only locally, where a document in progress is the ordinary state rather than a fault. |
| Assert the listing is not empty | One line per gate, and it is what two of the six already did. It catches a total break and misses a filter that drops all but one entry, which is the case a floor exists to catch. |
| Guard the property test rather than add a test | Fewer tests, and it reports a broken enumeration and a violating document as one red. The two want different fixes, and a single message can only describe one of them. |
| Compare the listing against a directory walk | Exact, and it needs no number at all. It reintroduces the untracked-file problem the first alternative turns down, since a scratch file in the directory makes the two disagree. |
| Consolidate the six enumerations into one helper first | Removes the duplication the floors sit on top of, and it is a different change. The trigger recorded for that work is a fifth prose gate over the decision directory, which this adds no part of. |
| Run the control by hand when a gate is written | What the issue asked for, and it holds only as long as someone remembers. The three blind gates were each written by someone who believed the check ran, which is the belief a one-off control confirms and then stops confirming. |
| Keep a list of the gates the control covers | Simpler than discovery, and it is the same defect one level up: a gate missing from the list is never controlled, and the list passes while covering less than it claims. |
| Leave the three blind gates to review | Cheapest, and it is what left them blind. A diff cannot show that a check read nothing, because a green gate and an unread one render identically. |

## Consequences

- All six gates fail when their enumeration returns nothing, and the control
  that says so now runs on every pull request. The two break modes below the
  file list -- a unit reader and a population split returning nothing -- were
  controlled separately, by hand.
- The control was itself controlled: a deliberately blind gate added to the
  suite was discovered and failed, then removed. A check that has never failed
  is a check nothing has tested.
- Adding a gate that reads a tracked-file listing now means adding its
  coverage test, because the control finds the gate by how it reads its corpus
  and fails it otherwise. That is a real constraint on a future gate, and it
  is the constraint this record exists to impose.
- A floor is a number that ages. For the decision records it only ever rises,
  because a record is never deleted; for the churning corpora the margin
  absorbs ordinary deletion, and a genuine halving of the tree fails loudly.
- The character-set gate splits its population once and hands each half to the
  rule that reads it. Its two rules no longer re-filter the whole tree.
- The readability gate parses each record once rather than once per limit, so
  the coverage assertion and both limits report on one reading.
- A document written but not staged is still ungated. That is now a stated
  property with a message naming it, rather than a silent hole.
- The six stay six separate modules, each carrying its own floor. The
  duplication between their enumerations is untouched and still waiting on its
  own trigger.

## Related

- #131 -- the issue carrying the measurement above and the acceptance criteria
- ADR-020 -- where the shape shared by the gates over the decision directory
  was last weighed, and where the consolidation trigger is recorded
- PLAYBOOK 3.12 to 3.17 and 3.21 -- the gates themselves, and how to run each
- PLAYBOOK 3.22 -- the control, and how to read the two reds it separates
