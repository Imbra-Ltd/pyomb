# ADR-007: Bandit is the whole SAST gate, and platform SAST is declined

**Status:** Superseded by ADR-012
**Date:** 2026-08-19
**Upstream:** filed as braboj/solid-ai-templates#1026 against
`templates/base/workflow/quality-gates.md`. With the domain skin off, the
convention is that a gate category naming more than one tool is satisfied by
the tools that can run plus a recorded decline carrying a revisit trigger. It
is never left blank because one of them is unavailable.

## Context

`templates/base/workflow/quality-gates.md` makes Security (SAST) a Layer 3
MUST, and `templates/stack/python-lib.md` names the tools for it: Bandit plus
platform SAST. Neither existed. Every other row of that table — lint, format,
type check, docstrings, secrets, tests, coverage, build — has been wired since
the gates were completed, so Security was the one gap, which is what #11
records.

The library parses untrusted bytes off a socket by design, which is the code
class static analysis is most useful on.

The platform half was measured rather than assumed. GitHub code scanning
refuses to report on this repository at all:

```text
$ gh api repos/Imbra-Ltd/pyomb/code-scanning/alerts
Code Security must be enabled for this repository to use code scanning. (HTTP 403)
```

The repository is private, and code scanning on a private repository requires
GitHub Code Security, which is a paid add-on. So the platform half cannot be
turned on by committing a workflow file — it needs a purchase, which is a
business decision and not one a gate change gets to make.

The bandit half measured better than expected. Against `src/` it reports
nothing at all: zero findings across 4,363 lines. The whole tree produces 35,
and they fall into two groups that are both explainable rather than latent:

| Finding | Count | Where |
| --- | --- | --- |
| `B101` assert_used | 33 | one test module |
| `B404` subprocess import, `B603` subprocess call | 2 | the cert generator |

Neither group is a defect. A test asserts because that is what a test is, and
the cert generator drives `openssl` because that is what it is for. This is
the material difference from ADR-003 and ADR-005, which both had to freeze
hundreds of real pre-existing findings to turn a gate on. Here there is
nothing to freeze.

## Decision

Bandit is the SAST gate. It runs in CI over `src`, `scripts` and `tests`, and
fails on any finding at any severity — there is no severity floor and no
per-file freeze table, because the tree is already clean at full strictness.

```text
                          bandit finding
                                |
              +-----------------+-----------------+
              |                                   |
      in a test module,                   anywhere else
      check assert_used                          |
              |                     +-------------+-------------+
        config skip                 |                           |
      (asserts are the           carries a site-local        no marker
       point of a test)          # nosec <ID> plus its           |
              |                  reason above it              gate fails
        gate stays quiet                 |
                                   gate stays quiet,
                                   and bandit counts it
                                   in the run report
```

Two rules govern the suppressions, inherited from ADR-005:

1. A suppression is site-local. It names the specific check (`# nosec B603`,
   never a bare `# nosec`), and the reason sits in a comment directly above
   the line. Every other check stays live on that line.
2. The analysis is never turned off to make the gate pass. A global `skips`
   entry for `B404` or `B603` would stop bandit looking at subprocess use
   anywhere, including at a call site added later that genuinely is unsafe.
   The single config-level skip is `assert_used`, scoped by glob to the test
   modules, so the check still fires on `src/` and `scripts/`.

That scoping was verified rather than asserted: a throwaway module carrying an
assert, a hardcoded password, `shell=True` and an MD5 digest was dropped into
`src/pyomb/`, and the gate failed on all four. The assert was included, which
is what proves the skip did not leak out of `tests/`. The tree is green again
once the module is removed.

Platform SAST is declined for as long as the 403 above holds. It is declined
rather than missing, which is the distinction this record exists to draw.

**Revisit trigger:** the repository going public, which makes code scanning
free, or GitHub Code Security being purchased for the organization. Either one
reopens this decision; neither is on the roadmap today.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Commit a CodeQL workflow anyway | It cannot run. The API refuses before any analysis starts, so the workflow would be a permanently red or permanently skipped job — the gate-by-omission shape `quality-gates-scope-agreement` names. |
| Make the repository public to get free code scanning | Out of scope, and backwards: repository visibility is a business decision that a quality gate does not get to force. #2 tracks the release question on its own terms. |
| Gate on medium severity and above | Buys nothing today, because the tree is clean at every severity, and costs the ability to notice a low finding arriving. A floor is worth adding when there is noise to floor out; there is none. |
| Global `skips` for `B101`, `B404` and `B603` | Rejected on ADR-005's rule. It freezes the analysis rather than the finding: bandit stops looking at asserts and subprocess calls everywhere, so a genuinely unsafe call added later passes silently. |
| Add bandit to pre-commit as well | `quality-gates-categories` puts Security at Layer 3 only, and the run needs the package installed. Layers 1 and 2 are marked `—` for this row deliberately. |
| Scan `src/` only | `scripts/` and `tests/` are not shipped, but a contributor runs them on their own machine, and the cert generator is the one place in the tree that executes an external binary. |

## Consequences

- The Security row of the gate table is wired, which closes #11 and leaves the
  table with no blank rows.
- The gate starts with no freeze, unlike ADR-003 and ADR-005. Any finding it
  reports from here is genuinely new, so there is no legacy backlog to read
  past when one appears.
- Suppressions stay countable. Bandit reports them as a separate line in every
  run, so the two in the cert generator cannot quietly become twenty.
- `bandit` is pinned to a minor range in `pyproject.toml`, for the reason ruff
  and mypy are: the clean tree records one version's check set, and a release
  adding a check would fail the gate on untouched code.
- The `toml` extra is required on the pin. Bandit reads no configuration from
  `pyproject.toml` unless pointed at it with `-c`, and cannot parse it at all
  on Python 3.10 without the extra.
- A local run and CI resolve to the same checks, because both name the config
  file. Dropping `-c` silently produces a different, noisier run.
- The project carries a documented reason for having half of what the stack
  template names, rather than an unexplained gap that the next audit
  rediscovers.

## Related

- ADR-003 — the per-file lint freeze whose suppression rules this inherits
- ADR-005 — freeze the finding, never the analysis; the rule the global-skips
  alternative is rejected on
- #11 — no static application security testing, which this closes
- #22 — the CI badge cannot render while the repository is private, the other
  consequence of the visibility this decision turns on
