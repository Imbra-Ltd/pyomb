---
id: "053"
status: Accepted
date: 2026-09-08
category: repository
supersedes: []
superseded_by: []
---

# ADR-053: A gate belongs to the project it measures

**Upstream:** filed as `none` for now, because the rule set this would
target is being reworked to require fewer records. With the domain skin
off: a rule shipped as prose is weighed on arrival, and a gate built from
that rule is enforced on arrival. A vendored rule set that ships gates
therefore binds every consumer to every rule, which is the opposite of
what shipping rules does.

## Context

`checks/` holds this project's gates over its own conventions. A gate
there is a test module whose subject is the repository rather than the
library: it exercises no source module and never will.

Roughly half of it enforces rules that arrive from the pinned templates
rather than from Modbus. Turning one of those rules into a maintained
module is work this project has now done ten times, and none of it
reaches the next project pinning the same templates.

### What the tree holds, measured at `c8b3cf8`

| Claim | Command | Result |
| --- | --- | --- |
| The gates | `git ls-tree -r --name-only origin/main checks/` | 24 files, 4961 lines |
| The library they sit beside | `git ls-tree -r --name-only origin/main src/` | 12 modules, 8144 lines |
| The ten whose rule is upstream | the table below | 2304 lines, 46% of `checks/` |
| Modules reading a tracked-file listing | `git grep -l "ls-files" -- checks/ \| wc -l` | 11, eight of them in the ten |

The ten, each named for the rule it holds rather than for its subject:

| Module | Lines | The rule it holds |
| --- | --- | --- |
| `test_comment_length.py` | 360 | comment and docstring length |
| `test_line_endings.py` | 305 | LF in the index, including the binary case |
| `test_decisions_are_readable.py` | 268 | sentence and paragraph limits |
| `test_decision_frontmatter.py` | 240 | the decision-record schema |
| `test_source_is_ascii.py` | 223 | printable ASCII outside Markdown |
| `test_markdown_line_width.py` | 213 | the declared Markdown width |
| `test_entry_points_set_the_encoding.py` | 191 | output encoding at the entry point |
| `test_decision_citations.py` | 190 | records link through front matter |
| `test_document_gates_are_not_blind.py` | 166 | every gate above fails on an empty corpus |
| `test_doctests_are_gated.py` | 148 | docstring examples are collected |

### What of those 2304 lines is actually shared

The rule is, and the templates already carry it, as prose beside a fenced
command a reader runs by hand. What this project added on top is a
measurement of this tree, and it does not transfer:

```bash
grep -nE "^[A-Z_]+ *= *[0-9]+" <the ten>   # 18 constants, 13 of them floors
grep -n "pyomb" <the ten>                  # 3 hits, in 2 of the 10 modules
```

Thirteen floors, each sized from the corpus it guards: 70 Python files,
64 tracked text files, 23 records, 450 sentences, 48 non-Markdown files,
30 gated doctests. A floor derived from another project's corpus asserts
nothing about this one.

The part that is genuinely duplicated is the corpus reader -- the wrapped
`git ls-files` call every one of the eleven carries. Measured whole,
those readers are 256 lines, five per cent of `checks/`, not 2304.

## Decision

| # | Rule |
| --- | --- |
| 1 | The gates stay here; a gate belongs to the project it measures |
| 2 | The templates carry the rule, this repository carries the measurement |
| 3 | A gate names its own roots and its own floors, re-measured here |
| 4 | A gate carrying a project parameter stays whole, and names it |
| 5 | The corpus reader stays duplicated, because the coverage gate finds it |
| 6 | Upstream receives the rule and the command, never the gate |

```text
   the templates                 this repository
   -------------                 ---------------
   the rule, as prose            the roots it reads
   a command a reader runs       the floor it asserts
                                 the negative control
                                 the exemptions, each recorded
        |                              |
        +---------- weighed -----------+
                       |
        a rule arrives as prose and someone decides.
        a gate would arrive as a red build.
```

### 1. Why an upstream gate binds on arrival

This project adopts a template rule only when someone can name the defect
it would have caught here, and declines the rest in one line. That
decision is what stopped an upstream release schedule from generating
this project's backlog.

A gate shipped in the submodule inverts it. A pin bump would no longer
change prose a person weighs; it would change what fails, on a tree
nobody touched. The remedies left are unpinning, an exclusion list, or
adopting the rule under time pressure, and the decision that governs
adoption exists to prevent all three.

### 2. The rule is shared already

The duplication worth naming is not the ten modules. It is the rule, and
the templates carry it once for every consumer, which is the level the
sharing belongs at.

What a second project writing the same gate repeats is the skeleton in
rule 5 and nothing else. Its roots, its floors, its exemptions and its
remedy text are statements about its own tree.

### 3. Roots and floors are re-measured, never inherited

A floor exists so that a gate reporting nothing can be told from a gate
reading nothing. It is therefore a measurement of one corpus, and copying
it from elsewhere produces a floor that passes on an empty tree.

A consuming project would have to supply both, and both together are most
of what a module holds. What it would import is the parsing, which is the
part a reader of the rule can already write.

### 4. The modules carrying a project parameter

Four were named as generic in their rule and specific in a parameter, and
re-measuring finds a different four. One of them, the character-set gate,
now names no project path at all, and one carries a parameter nobody
counted:

| Module | Its project parameter | Kind |
| --- | --- | --- |
| `test_doctests_are_gated.py` | imports the package and walks it | real coupling |
| `test_entry_points_set_the_encoding.py` | the package directory as a scan root | a path |
| `test_markdown_line_width.py` | one imported specification, exempted by path | a path |
| `test_decision_frontmatter.py` | this project's closed category set | a decision |

None is split. A parameter is one line, extracting it would leave a
module that cannot run alone, and the last of the four is a decision this
project made rather than a value at all.

### 5. The corpus reader stays duplicated

The gate that proves every other gate fails on an empty corpus discovers
its subjects by reading their source for the listing call. Extracting
that call into a shared module would leave no gate carrying it, so the
discovery would find none and its own floor would fail.

That failure would be loud, and repairing it means rebuilding the
discovery on something else. The duplication is 256 lines and it is what
makes a gate findable, so it is kept deliberately rather than tolerated.

### 6. What upstream gets

A rule this project proves worth gating is offered upstream as the rule
and the command, in the form the templates already use. The module stays
here, because the module is this tree's answer and not the rule.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Move the ten into the submodule and have each consumer run them | The shape the issue asks about first, and the one the adoption decision refuses. A pin bump would then add enforcement rather than prose, so declining an arriving rule would cost an exclusion list instead of one line in a pull request. |
| Publish the gates as a package each project installs | The ordinary way to share Python, and it is closed here: nothing this project builds goes to a package index. It also does not answer the objection above, since an installed gate binds on upgrade exactly as a vendored one binds on a bump. |
| Split on what a gate reads rather than where its rule came from | A cleaner line -- the ten that read only tracked Markdown against the rest -- and it sorts the same modules into the same places while answering a different question. Ownership is decided by whose measurement the module carries, not by its corpus. |
| Extract the shared corpus reader into a local helper module | The genuine duplication, 256 lines, and removing it blinds the gate that discovers its subjects by finding that call in each module's source. Worth revisiting only together with a different discovery mechanism. |
| Strip the coverage assertions and the floors to shrink the ten | Halves the line count that prompted the question. It also deletes the part that distinguishes a gate reporting a clean tree from one that read nothing, which is the defect three of these gates were measured to have. |
| Leave the question open | Costs nothing today and leaves the next project pinning these templates to re-derive the same answer, which is what the issue asking this exists to prevent. |

## Consequences

- `checks/` keeps 4961 lines, and the ten stay where they are. Nothing
  moves, no module is split, and no gate changes behaviour.
- The next project pinning these templates writes its own gates. What it
  inherits is the rule and the command, and this record is what says so
  rather than leaving the duplication unexplained.
- A rule proved worth gating here is still worth offering upstream as
  prose. That path is unchanged and is the only one rule 6 leaves open.
- The corpus reader is duplicated eleven times on purpose. A future
  reader meeting it as an obvious extraction has this record and rule 5
  as the reason it survives, and a measurement of what removing it costs.
- The measurement ages. The ten were 2302 lines when the question was
  asked and are 2304 now, so the ratio is stable, and nothing polls it.
  A person re-running the commands above is the whole detection.
- Nothing changes for a consumer of the library. This record is about
  which repository owns a test module, and no shipped artifact carries
  one.

## Related

- ADR-034 -- the record making a template rule adoptable only on
  evidence, which rule 1 argues from
- ADR-044 -- the record that moved these modules out of the test tree and
  drew the line this one does not redraw
- ADR-022 -- the record requiring a document gate to assert the floor it
  read, which is where the thirteen floors come from
- ADR-011 -- the record keeping the distribution off a package index
- Issue #334 -- the spike this record answers
