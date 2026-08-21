# ADR-011: Generate the SBOM from a consumer environment on tag

**Status:** Accepted
**Date:** 2026-08-21
**Upstream:** filed as braboj/solid-ai-templates#1035 against
`templates/base/security/devsecops.md`. With the domain skin off, the
convention is that an SBOM must describe what a consumer installs rather than
what CI built with — every generator's most convenient mode reads the build
environment, which produces a schema-valid document naming the toolchain as
part of the product — and that the component set must be asserted, because a
misdirected generator succeeds.

## Context

#36 carries the one rule from `templates/base/security/devsecops.md` that binds
a library, kept alive when ADR-008 declined that template from the startup
block:

> A SBOM (Software Bill of Materials) MUST be generated per release. Attach the
> SBOM to the per-tag release record as a durable, per-version asset.

The issue deferred the work until the first release. Re-reading its trigger
found the premise had expired: `v0.1.0` was published 2026-08-18, annotated, a
day *before* the issue was filed saying no release existed. So the rule was
being violated rather than merely not yet applicable.

Checking that also turned up the wider gap. `v0.1.0` carries no assets at all —
no wheel, no sdist, no SBOM — because nothing produces them. CI builds a wheel
on every change and discards it with the run, and the repository has no release
workflow; `.github/workflows/ci.yml` was the only one. So the per-tag release
record the rule wants to attach to has no producer, and a consumer scanning the
release finds nothing to scan.

## Decision

1. Add `.github/workflows/release.yml`, triggered on a `v*` tag push. It builds
   the distribution, generates the SBOM, and attaches wheel, sdist and SBOM to
   the release record. The workflow is read-only at file scope; only the one
   job that uploads carries `contents: write`, at job scope.
2. Generate the SBOM from a **consumer environment**: create an empty venv,
   install the built wheel into it, and describe that. The generator is
   `cyclonedx-py`, carried in the `dev` extra so `uv.lock` pins it.
3. Assert the component set before attaching. For this library the SBOM MUST
   list exactly one component, `pyomb`, and the step fails otherwise.
4. Emit with `--output-reproducible`, so the SBOM for a tag can be regenerated
   and compared byte for byte. Verified: two runs over the same input produce
   identical 4,704 bytes.
5. Refuse a tag that does not name the version the package reports, before
   anything is built.
6. Do not publish to PyPI. That remains a separate decision; this workflow
   attaches assets to the GitHub release and stops there.
7. Do not backfill `v0.1.0`. Assets built now from a later tree would not be
   what that tag was, and a hand-uploaded asset carries no build provenance.

### Why a consumer environment

Every generator's convenient mode reads the environment at hand, and in CI that
is the build environment — the one that just ran the gates:

```text
  cyclonedx-py environment <build venv>     ->  81 components
    pyomb, pytest, ruff, mypy, coverage, lxml, ...
    schema-valid, and a machine-readable wrong answer

  pip install dist/*.whl into an empty venv
  cyclonedx-py environment <that venv>      ->   1 component
    pyomb 0.1.0
    what a consumer's install actually contains
```

The wrong one passes every check that is not about content, which is why
decision 3 exists: a generator pointed at the wrong environment succeeds.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| `pip-audit --format cyclonedx` | One tool for SBOM and vulnerability scanning, which is attractive. It is built to fail on findings, so it turns an asset step into a gate — and a release-gated gate cannot be dry-run on a PR, so it first surfaces mid-release. ADR-007 rejected the same shape for CodeQL. |
| `syft` on the wheel | Scans the artifact directly rather than an environment installed from it, which is closer to the thing being described and needs no venv step. Costs a pinned Go binary in a toolchain that is otherwise pure Python and entirely inside `uv.lock`. |
| Decline the rule for a zero-dependency library | Defensible: an SBOM over one component carries little information. It is still the difference between a machine-readable answer and a gap, the cost is one workflow, and declining would leave #36 open forever with no trigger that could ever fire. |
| Attach only the SBOM, per the literal issue | Would leave every release carrying an SBOM describing a wheel the release does not ship. The gap in `v0.1.0` is the assets, and the SBOM is only meaningful beside them. |
| Let the maintainer create the release, workflow uploads only | What `devsecops.md` describes. It leaves a window where a pushed tag has no release to attach to, and the workflow must then guard-and-exit, which is a silent no-op. See the divergence below. |

## Consequences

- Releasing changes from six manual steps to five: the tag push is the trigger,
  and the release record and its assets follow from it. PLAYBOOK 5 is updated.
- A tag pushed against a tree whose `__version__` disagrees fails the workflow
  before anything is built, rather than producing a release whose assets
  contradict its name.
- `v0.1.0` keeps its empty asset list permanently. The record of why is here.
- The `dev` extra grows `cyclonedx-bom` and the lock grows from 62 packages to
  93, most of it that generator's transitives. A contributor who only runs
  tests pays that on `uv sync`.
- Two documented divergences from `devsecops.md`, both because it describes a
  side-car scan job and this is the release pipeline itself:
  - It says the scan job reaches forward to a release it never creates, so a
    scan cannot have authority over the release record. Here the workflow *is*
    the release pipeline, so owning the record is its purpose rather than an
    overreach.
  - It marks the equivalent job `continue-on-error`, because an advisory scan
    against a vulnerability service goes red when the service has a bad minute.
    This generation reads a local environment, reaches no network and is
    byte-reproducible, so a failure is a defect worth surfacing. The ordering
    carries the rule's actual intent instead: wheel and sdist are attached
    before the SBOM is generated, so nothing downstream of them can leave a
    release empty.
