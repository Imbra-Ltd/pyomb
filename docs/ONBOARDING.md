# Onboarding

How to get pyomb running locally and make your first change.

This document describes the repository **as it is today**. `CLAUDE.md`
describes the shape it is being rewritten towards; where the two differ, follow
this document to get working and `CLAUDE.md` to decide what new code looks
like.

## 1. Prerequisites

| Tool | Version | Why |
| --- | --- | --- |
| Python | 3.10 or newer | CI runs 3.10 and 3.13 |
| uv | 0.9 or newer | installs the locked toolchain |
| git | any recent | submodules are used |
| OpenSSL | any recent, on `PATH` | mints the throwaway TLS chain |

No database, no container, no build step. The library has no runtime
dependencies beyond the standard library.

Every other tool arrives with `uv sync`, so uv is the one to install by hand.
Astral's installer is the documented route and needs no Python on `PATH`:

```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Where a Python is already present, `py -m pip install uv` on Windows or
`python3 -m pip install uv` elsewhere reaches the same place. That route
leaves uv importable as a module even when the installed script misses
`PATH`, so `py -m uv sync --locked --extra dev` works where `uv` alone
reports a missing command.

## 2. First-time setup

```bash
git clone --recurse-submodules https://github.com/Imbra-Ltd/pyomb.git
cd pyomb
uv sync --locked --extra dev
uv run pre-commit install
uv run python scripts/gen_test_certs.py
```

The `test` extra carries pytest, pytest-cov, ruff, mypy and bandit, which is
what CI installs; `dev` adds the hook runner and the build tools on top of it
and is what a contributor wants. The library itself has no runtime
dependencies, so `pyproject.toml` is the only place this project declares a
dependency.

`uv sync` creates `.venv/` and installs the exact versions `uv.lock` records.
`--locked` is what makes it exact: uv refuses a lock that no longer matches
`pyproject.toml` rather than re-resolving quietly, so you get what CI gets or
you get told why not. Activate `.venv` and the commands in this document work
unprefixed; otherwise prefix them with `uv run`. ADR-010 carries why the
toolchain is locked and why the lock is the universal kind.

`pre-commit install` is a one-off. From then on the gates run against your
staged files before each commit, so you find a formatting or typing slip
locally rather than in a red pipeline. PLAYBOOK 3.6 lists the hooks.

If you cloned without `--recurse-submodules`, fetch the templates separately —
they carry the conventions `CLAUDE.md` depends on:

```bash
git submodule update --init --recursive
```

`scripts/gen_test_certs.py` writes a throwaway CA, a server certificate and
three client certificates into `assets/certificates/`. That directory is
gitignored and the keys are unencrypted. Never commit them, and never trust
this CA anywhere but a test network.

## 3. Verify the setup

```bash
uv run --no-sync python -m pytest -q
```

Every command in this section is prefixed. A bare `python -m pytest` resolves
against whatever interpreter is active, which after step 2 may not be the
`.venv` uv just built — and if a global pytest exists it will run, pass, and
verify an environment you are not about to develop in. `--no-sync` keeps the
command from quietly re-resolving what step 2 pinned.

Expect every test to pass and none to be skipped. A skip means the TLS chain is
missing — rerun step 2's certificate command; the mutual-TLS tests skip
silently without it, and a suite reporting skips still exits zero.

The count is deliberately not written down here. It changes with every branch,
and a number in a setup document is wrong more often than it is right.

```bash
uv run --no-sync python -m ruff check src tests scripts examples
uv run --no-sync python -m mypy
uv run --no-sync python -m bandit -c pyproject.toml -r src scripts tests examples
```

Expect `All checks passed!` from the first and a `Success:` line from the
second. The module count in mypy's line is not written down here for the
same reason the test count above is not. Bandit prints a run summary and exits
zero; every severity row should read zero, and the two suppressed findings in
the certificate generator are reported on their own line.

## 4. Key files

| Path | What it is |
| --- | --- |
| `src/pyomb/packets.py` | The codec — MBAP header, one class per function code, the PDU registry, TCP and RTU frame wrappers |
| `src/pyomb/stream.py` | The transport — length-driven framing, deliberate fragmentation |
| `src/pyomb/omb_client.py` | Client simulator and the request builder |
| `src/pyomb/omb_server.py` | Server simulator, its select loop and the response factory |
| `src/pyomb/errors.py` | Modbus exception codes as a Python exception hierarchy |
| `tests/stub_socket.py` | The socket doubles most tests build on |
| `CLAUDE.md` | Conventions and the target the rewrite aims at |
| `docs/dev-journal.md` | What changed, why, and the post-mortems |

## 5. Project context

The library implements Modbus TCP and RTU: encoding and decoding frames, a
stream transport, and a client/server pair for exercising other
implementations. The authoritative specifications are in `docs/` as PDFs, and
`docs/Open_Modbus_Tutorial.md` is the readable introduction to the protocol.

Read `docs/dev-journal.md` before touching the wire format. Its post-mortems
record defects that a passing test suite did not catch, and section 2.3 of
`CLAUDE.md` states the resulting rules in one line each.

The repository, the distribution and the import package do not yet share a
name; ADR-002 settles what they become.

## 6. Daily workflow

Branch, commit, review and release steps are in `docs/PLAYBOOK.md` — see
PLAYBOOK 1 for git and PLAYBOOK 3 for the quality checks to run before
pushing. Conventions that bind every change are in `CLAUDE.md`.
