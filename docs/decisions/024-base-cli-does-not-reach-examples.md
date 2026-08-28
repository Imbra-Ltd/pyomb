---
id: "024"
status: Accepted
date: 2026-08-28
category: process
supersedes: []
superseded_by: []
---

# ADR-024: base-cli reaches one entry point, and scripts holds no probes

**Upstream:** filed as braboj/solid-ai-templates#1238 against
`templates/base/core/cli.md` and braboj/solid-ai-templates#1239 against
`templates/base/core/examples.md`. With the domain skin off, the first
convention is that a rule for executable entry points states whether it
reaches a directory whose files exist to be read whole, because the two
demand opposite structure. The second is that a directory named as the home
for throwaway work needs an owner, or it accumulates.

## Context

`templates/base/core/cli.md` entered this project's chain at `v2.57.0`. It
applies to "any executable entry point -- a published CLI, an operational
driver, a maintenance script that outlives the afternoon it was written in".

This project publishes no console script. `pyproject.toml` has no
`[project.scripts]`. What it has is eight modules with a `__main__` guard,
four under `scripts/` and four under `examples/`.

An example is none of the three named things while being literally both
executable and an entry point. The ambiguity is not academic: applied to
`examples/`, `base-cli-plumbing` factors each example's body into a shared
module, and `base-examples` requires one file per pattern that a reader takes
in whole. The two rules ask for opposite structure in the same directory.

Reading `scripts/` against the templates found a second, sharper problem.
Eight files, and only one is reachable from anything:

```text
+---------------------------+----------+-----------+-------------------+
| file                      | guard    | main()    | referenced by     |
+---------------------------+----------+-----------+-------------------+
| gen_test_certs.py         | yes      | yes       | README, CLAUDE,   |
|                           |          |           | PLAYBOOK, ONBOARD,|
|                           |          |           | CI, examples index|
| demo_modbus_crc.py        | yes      | no        | nothing           |
| demo_metaclass.py         | yes      | no        | nothing           |
| demo_stream.py            | yes      | no        | nothing           |
| demo_validation.py        | no       | no        | nothing           |
| factory.py                | no       | no        | nothing           |
| pack_unpack.py            | no       | no        | nothing           |
| module_docstring.txt      | n/a      | n/a       | nothing           |
+---------------------------+----------+-----------+-------------------+
```

Three of the seven are not runnable as written. `demo_validation.py` holds two
functions taking `self` at module scope, extracted from a class that is not
there. `factory.py` declares a class whose every method is `pass`, with
`@classmethod` on methods taking `self` and a `@staticmethod` taking `cls`.
`pack_unpack.py` is two helpers nothing imports, wrapping `struct` and
raising bare `Exception`.

`module_docstring.txt` is a draft of the `packets.py` module docstring. That
module carries a docstring already, and the draft disagrees with it about the
PDU-ID range -- `0x0000` where the shipped text says `0x0001`. A stale second
copy of a docstring is worse than no copy, because a reader who finds it has
no way to tell which one the code follows.

Nothing reaches them. The `src/` layout keeps `scripts/` out of the wheel, so
the packaging gates are silent; no test imports them, so coverage is silent;
and all seven sit inside the `per-file-ignores` freeze, so the linter is
silent too. They carry 100 lint findings, 45 of them missing docstrings.

## Decision

1. **Scope** -- `base-cli` MUST NOT be applied to `examples/`. The directory
   is governed by `base-examples`, whose one-file-per-pattern rule is
   incompatible with `base-cli-plumbing`. This is recorded as a reading of an
   ambiguous scope sentence, not as a divergence, and the ambiguity is filed
   upstream rather than maintained here.

2. **Entry points** -- `scripts/gen_test_certs.py` is the project's only
   executable entry point in the `base-cli` sense, and is held to
   `base-cli-main` clause by clause.

3. **Dead scripts** -- a file under `scripts/` that no documented command, no
   test and no CI job reaches is dead code and is deleted, not reshaped. Six
   are deleted by this record's change. Git history holds them.

4. **What may live in `scripts/`** -- a file that a documented command names
   or that CI executes. `scripts/` is not a probe directory in this
   repository. `base-quality` requires a probe to be deleted before the commit
   that uses its findings, and that rule wins here. The description of
   `scripts/` in `base-examples` is drawing a boundary for `examples/`, not
   granting a permanent home.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Record a local divergence from `base-cli` and maintain it | A divergence needs re-reading against every future edit to the template. The scope sentence is ambiguous upstream, so fixing it at the source is cheaper and helps every consumer. PLAYBOOK 4.1 already names this case. |
| Apply `base-cli` to `examples/` and relax `base-examples` | Inverts which rule owns the directory. An example whose body lives in a shared import stops being readable in one piece, which is the only thing an example is for. |
| Give each dead script a `main(argv)` and docstrings | Reshapes files nothing runs. It would clear 100 lint findings by writing documentation for a class whose every method is `pass`. |
| Keep the dead scripts and exclude `scripts/` from the linter | Widens a freeze to hide the evidence, which the lint-freeze record forbids. The freeze is what let them survive this long. |
| Delete `demo_modbus_crc.py` with the rest | Its docstring carries the CRC polynomial, the reversed form, and why the checksum goes on the wire low byte first -- knowledge this project's protocol rules depend on. Deleting it loses that; it is promoted instead. |

## Consequences

- Six files leave `scripts/`: `demo_metaclass.py`, `demo_stream.py`,
  `demo_validation.py`, `factory.py`, `pack_unpack.py` and
  `module_docstring.txt`.
- `demo_stream.py` binds port 502, which the assigned-port record rules out
  for anything a contributor runs. Deleting it removes the last such caller.
- `scripts/gen_test_certs.py` gains the `-> int` return annotation
  `base-cli-main` requires. `scripts/` is outside `mypy`'s `files = ["src"]`,
  so nothing reads it and the annotation is documentation.
- `demo_modbus_crc.py` stays for now and is tracked for promotion to
  `examples/`, where CI would execute it. Until then it is the one file in
  `scripts/` that decision 4 does not cover, which is stated rather than left
  implied.
- The `scripts/` half of the `per-file-ignores` freeze shrinks from seven
  entries to two before anyone edits it, which is most of the work that slice
  was filed for. Only `.py` files carry an entry, so the text file removes
  none.
- `base-cli-plan` and `base-cli-persistence` are checked against
  `gen_test_certs.py` and neither applies: it takes no expensive step worth a
  plan flag, and it already writes its output by default.
- The README's one-line description of `scripts/` is no longer accurate and
  changes with this record.

## Related

- ADR-021 -- examples bind an assigned port, which `demo_stream.py` predates
- ADR-003 -- the lint freeze that kept these files unlinted
