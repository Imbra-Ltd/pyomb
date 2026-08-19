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

Security vulnerabilities do **not** go in issues — see [SECURITY.md](SECURITY.md).

## 3. Branches and commits

Branch names: `feat/<scope>`, `fix/<scope>`, `docs/<scope>`, `chore/<scope>`.

Commits: `<type>(<scope>): <summary>`, where type is one of `feat`, `fix`,
`chore`, `docs`, `refactor`, `test`, `ci`. Write the body to explain why the
change is needed, not what the diff already shows. Reference issues with
`Refs #N` or `Closes #N`.

Keep pull requests small and focused on one concern.

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

Run the linter, the formatter and the type checker before opening a pull
request:

```bash
python -m ruff check src tests scripts
python -m ruff format src tests scripts
python -m mypy
```

Configuration is in `pyproject.toml`. The `per-file-ignores` table freezes the
violations that existed when ruff replaced flake8, so a file you create is
checked against the whole rule set while an existing one is held where it was.
Do not add your file to that table to make the gate pass, and do not widen an
existing entry — both defeat the point. The star imports that once needed
`F403`/`F405` frozen are gone, so a new one fails the gate outright.

CI runs the formatter as `ruff format --check`, which reports without
rewriting. Formatting is not a review topic: run the command above and the
check has nothing to say. ADR-004 records why the whole tree was reformatted
in one go.

mypy runs under `strict`, with the modules that predate the gate frozen by
error code in `pyproject.toml`. The same two rules apply as to the lint table:
a module you did not write is not added to make the gate pass, and an existing
entry is not widened. A module you create is held to all of strict. ADR-005
records why, and PLAYBOOK 3.5 has the detail.

## 5. Tests

Install the test tooling and run the suite:

```bash
pip install -e ".[test]"
pytest tests
```

With coverage, as CI runs it:

```bash
pytest tests --cov=pyomb --cov-report=term-missing --cov-fail-under=80
```

Add tests for any behaviour you change. Protocol changes need a test asserting
on the serialized bytes, not only on object state — the wire format is the
contract.

The coverage floor is deliberately below current coverage and is meant to be
ratcheted upward, never lowered.

## 6. Continuous integration

`.github/workflows/ci.yml` runs lint, format, type check, tests and coverage on
Python 3.10 and 3.13, plus a build, a static analysis pass and a secret scan,
on every push to `main` and every pull request. A red pipeline blocks merge.

Install the hooks once and the same checks run before a commit lands, so a red
pipeline is not the first you hear of a formatting or typing slip:

```bash
pre-commit install
```

The hooks are skippable with `--no-verify`, which is why CI repeats every one
of them.

## 7. Documentation

Update the documentation in the same pull request as the change:

- `README.md` — installation, requirements, usage examples
- `SECURITY.md` — the security posture or the disclosure process
- `CONTRIBUTING.md` — this file, when process or conventions change
- `docs/` — protocol reference and audit reports

Write in the present tense. Past or future tense usually signals documentation
that has drifted from the code.
