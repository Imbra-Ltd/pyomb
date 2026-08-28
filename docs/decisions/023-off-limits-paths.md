---
id: "023"
status: Accepted
date: 2026-08-28
category: process
supersedes: []
superseded_by: []
---

# ADR-023: Off-limits paths include the templates submodule pointer

**Upstream:** filed as braboj/solid-ai-templates#1204 against
`templates/base/core/git.md`. With the domain skin off, the convention is that
a repository which vendors its governing rules declares that pointer
off-limits. The default set names the paths whose blast radius comes from what
they execute; a vendored-rules pointer has the same property and appears on no
list, because it executes nothing.

## Context

`templates/base/core/git.md` requires the context file to declare an
**Off-limits** section listing paths that may not be modified without explicit
approval. The rule arrived with the pin this project already carries.
`CLAUDE.md` had no such section.

The rule offers a default set and says to cut it down rather than adopt it
whole. Measured against this tree, most of it is absent:

| Default member | Present here |
| --- | --- |
| auth and session code | no |
| payment and billing code | no |
| database migrations | no |
| `.env*` and secret handling | no |
| CI/CD workflow definitions | yes |

A mechanical cut therefore yields one entry. That reading is defensible and
leaves out the change in this repository with the widest consequence per byte.

`docs/solid-ai-templates` is a submodule pointer. Moving it is a one-line diff
that replaces every rule the project binds. Nothing else reports the change:
the suite is unaffected, the linters are unaffected, and the diff shows a
before and after hash.

The rule's own reasoning covers it exactly. A change reads as ordinary, its
blast radius is not local, and the usual signals say nothing about it. The
default list simply does not reach it, because every member earns its place by
what it executes and a pointer executes nothing.

## Decision

1. **Two paths** — `.github/workflows/` and `docs/solid-ai-templates` are
   off-limits. The first because the release workflow fires on a tag that
   cannot be taken back and no suite runs it; the second for the reason above.
2. **Propose before changing** — a change inside either is proposed first, and
   the proposal carries a rollback strategy and the coverage that would catch
   a regression. The approval is for that plan, not for the area.
3. **Name it in the summary** — a diff touching either names the path at the
   top of its summary.
4. **One home for the list** — `CLAUDE.md` section 2.5 declares the paths and
   the check reads them from it. A check restating the list is a second copy
   that drifts, and the drift is silent in the direction that matters.
5. **The check is a pre-pull-request step, not a gate** — it lives in PLAYBOOK
   1.3 beside the closing-keyword check and is not wired into CI. Every line
   it prints is an escalation trigger rather than a failure.

```text
  branch diff vs origin/main
            |
            +--> no listed path ----> open the pull request
            |
            +--> a listed path -----> propose first:
                                        + rollback strategy
                                        + regression coverage
                                        + path named at the top
                                          of the summary
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Workflows only, the default set cut mechanically | Smallest and fully compliant with the rule as written. It leaves the highest-consequence one-line change in the repository undeclared, which is the outcome the rule exists to prevent. |
| Add `pyproject.toml` for the lint and type freeze lists | Those lists already carry a standing prohibition on being widened, recorded elsewhere. A second carrier for one signal can disagree with the first, and neither would be wrong. |
| Wire the check into CI as a required gate | The rule calls a hit an escalation trigger. A gate would fail every pull request that legitimately edits a workflow, so it would be muted within a week. |
| Restate the path list inside the check | One edit becomes two, and the copy that goes stale is the one nothing reads until it is needed. |
| Record no decision and put the paths in `CLAUDE.md` alone | The section holds one rule per line and cannot carry why the pointer is listed and the manifest is not. The next reader re-derives it or removes the entry. |

## Consequences

- A routine pin bump now states a proposal. The cost is small, because PLAYBOOK
  4.1 already prescribes most of what the proposal must contain.
- The check has no automated enforcement, so it holds only while it is run.
  That is deliberate, and it is the same trade the closing-keyword check beside
  it already makes.
- Adding a path is one line in `CLAUDE.md` and no change to the check.
- The list is short enough to read, which is the property that decides whether
  a reviewer uses it. A list covering everything plausible would be ignored.

## Related

- ADR-011 — what the release workflow produces, which is why a tag is
  irreversible
- ADR-018 — the width declaration a check reads rather than restates, the
  pattern decision 4 follows
- #144 — the issue that measured the default set against this tree
