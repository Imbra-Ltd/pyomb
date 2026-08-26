# Contributing

## 1. How to contribute

State your intent in a GitHub issue before you start, so effort is not
duplicated and the approach can be discussed while it is still cheap to
change. Work on a branch, then open a pull request.

All submissions require review, including those from project members.

## 2. Issues

Every issue carries exactly one type label and one priority label, applied at
creation.

| Type | Meaning |
| ---- | ------- |
| `bug` | Defect in existing functionality |
| `task` | Atomic implementable work |
| `spike` | Research or exploration — the output is a decision |
| `epic` | Large initiative spanning multiple tasks |
| `incident` | Outage or degradation affecting users now |

| Priority | Meaning |
| -------- | ------- |
| `P0` | Critical — blocks everything |
| `P1` | High — must fix before the next milestone |
| `P2` | Medium — important but not blocking |
| `P3` | Low — nice to have, including trivial |

Titles are sentence case with an imperative verb and no type prefix; the
labels carry the type. Describe the problem, not only the proposed fix, and
include a reproduction where one applies.

Security vulnerabilities do **not** go in issues — see
[SECURITY.md](SECURITY.md).

## 3. Branches and commits

Branch names: `feat/<scope>`, `fix/<scope>`, `docs/<scope>`, `chore/<scope>`.

Commits: `<type>(<scope>): <summary>` in the imperative, subject under 80
characters, where type is one of `feat`, `fix`, `chore`, `docs`, `refactor`,
`test`, `ci`. Write the body to explain why the change is needed, not what the
diff already shows.

Keep pull requests small and focused on one concern. Never force-push,
`--force-with-lease` included; when a branch falls behind `main`, merge `main`
into it. Reference an issue with `Refs #N`, and write a closing keyword only
where the change genuinely resolves that issue — GitHub matches the bare
substring, so it must be repeated before every number and it fires even when
negated.

PLAYBOOK 1.1 to 1.4 carry the rest: the commands that check a pull request body
for closing keywords before the merge and confirm afterwards what actually
closed, and what to do with a branch that has fallen behind.

## 4. Code style

- Maximum line length 120 characters, 80 recommended
- Indentation is 4 spaces
- `snake_case` for functions, methods, variables, modules and packages
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- Docstrings use triple double quotes and document arguments and raised
  exceptions

Some older code uses camelCase method names (`sendRequest`, `getPeers`). That
is legacy, not the convention; do not add more.

Markdown is a separate rule and a stricter one: every line wraps at the width
`.editorconfig` declares for it, and the decision records are held tighter
still. Both run in the test suite, so a long line fails the pipeline rather
than reaching review. PLAYBOOK 3.14 and 3.15 carry the exemptions and what a
failure prints.

Run the linter, the formatter and the type checker before opening a pull
request; PLAYBOOK 3.4 and 3.5 carry the commands. Configuration is in
`pyproject.toml`, including the two freezes — the `per-file-ignores` table for
ruff and the per-module error codes for mypy. Both work the same way: a file
you create is checked against the whole rule set, and neither table is a place
to add your file to make a gate pass. ADR-003 and ADR-005 record why.

## 5. Tests

Add tests for any behaviour you change. A fix for a reported defect ships with
a test that fails against the unfixed code — run it both ways and say so in the
commit message.

Protocol changes need a test asserting on the serialized bytes, not only on
object state. The wire format is the contract, and a round trip through this
library proves nothing about it; pair it with a vector from the specification.

The coverage floor is deliberately below current coverage and is meant to be
ratcheted upward, never lowered. PLAYBOOK 3.1, 3.3 and 3.10 carry the commands.

## 6. Continuous integration

A red pipeline blocks merge. Read the run rather than assume a green local one
settles it — CI runs Linux under two Python versions, and development here is
typically Windows.

Install the hooks once and the same checks run before a commit lands, so a red
pipeline is not the first you hear of a formatting or typing slip:

```bash
pre-commit install
```

The hooks are skippable with `--no-verify`, which is why CI repeats every one
of them.

PLAYBOOK 3.6 covers the hooks and 3.9 the pipeline, including which checks gate
a merge, why there are two of them, and how to read a failed run.

## 7. Documentation

Update the documentation in the same pull request as the change:

- `README.md` — installation, requirements, usage examples
- `SECURITY.md` — the security posture or the disclosure process
- `CONTRIBUTING.md` — this file, when process or conventions change
- `docs/` — protocol reference and audit reports

Write in the present tense. Past or future tense usually signals documentation
that has drifted from the code.
