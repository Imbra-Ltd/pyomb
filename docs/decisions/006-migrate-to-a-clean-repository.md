---
id: "006"
status: Accepted
date: 2026-08-18
category: repository
supersedes: []
superseded_by: []
---

# ADR-006: Migrate to a new repository with clean history

**Upstream:** `templates/base/core/git.md`, filed as
braboj/solid-ai-templates#1021. This line first read `none`, on the reasoning
that a platform rule is not a convention a template could carry. That was
wrong: the platform rule is the *reason*, and the convention it implies —
verify a new repository's security settings, and sequence a migration around
what issue transfer permits — is exactly what a template holds

## Context

The predecessor repository, `Imbra-Ltd/protocol-modbus`, was briefly public on
2026-08-13. During that window a committed self-signed certificate authority
and its private key were served to unauthenticated clients. The material was
rotated, and a generator now mints a throwaway chain into an ignored directory,
so nothing in the tree references the committed files.

The history was rewritten on 2026-08-14 and force-pushed. That makes the old
objects unreachable, not absent: they stay fetchable by exact commit hash until
the host collects them, and only the host can collect them. A support request
to force collection was considered and declined, on the reasoning that a
self-signed authority installed in no trust store signs for a trust store with
no members.

That reasoning holds while the repository is private. It weakens when the
repository is published, because publication restores anonymous fetch-by-hash
to anyone who recorded a hash during the August window.

A separate pressure points the same way. ADR-002 settled the distribution and
import package on `pyomb` while leaving the repository named
`protocol-modbus`, calling that name cosmetic and noting it could change later
at no cost.

```text
protocol-modbus (private, archive)        pyomb (new)
+-----------------------------+           +---------------------+
| 27 commits + unreachable    |           | 1 commit at v0.1.0  |
| objects from the force-push |           |                     |
| 43 issues, 12 PRs, advisory |  issues   | 8 open issues       |
| dated 360 audit             | --------> | no history to mine  |
+-----------------------------+           +---------------------+
        stays private forever                goes public later
```

## Decision

1. Publish from a new repository, `Imbra-Ltd/pyomb`, whose first commit is the
   v0.1.0 tree. No history is carried across, so no unreachable object is
   either.
2. Keep `protocol-modbus` alive and private as the archive. It holds the
   closed issues, the pull requests, the dated 360 audit and security advisory
   `GHSA-wr8x-662m-m2rj`, which is the only unredacted home of that audit's
   security findings. Deleting the repository destroys the advisory.
3. Create the destination private and keep it private until the migration
   finishes. GitHub refuses to transfer an issue from a private repository to
   a public one, and requires both repositories to share an owner. The order
   is forced: create private, transfer, then publish.
4. Transfer the open issues and clone the label taxonomy first, because a
   label that does not already exist in the destination by name is dropped
   from the transferred issue.

Issue numbers, predecessor to here: 9 to 1, 11 to 2, 15 to 3, 31 to 4, 47 to 5,
51 to 6, 53 to 7, 54 to 8. The old URLs redirect.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Rename `protocol-modbus` to `pyomb` | Cheapest, and settles the name, but the repository keeps every unreachable object. Publishing it restores anonymous fetch-by-hash for anything recorded in August |
| Rename, then ask the host to collect the objects | The only route that keeps the tracker intact and clears the objects, but it depends on a support request that may be declined, and the decision to skip that request had already been taken |
| Publish as-is and accept the exposure | Defensible while private on the self-signed reasoning, but the reasoning was never argued against a public repository, and reversing publication does not un-serve a byte |
| Carry the history across | Defeats the purpose — the objects travel with it |

## Consequences

- The tracker splits. Closed issues and pull requests stay in the archive, and
  the eight open issues move. Anything needing the closed history reads the
  archive.
- Documentation in the archive carries roughly 175 references to its own issue
  numbers. They keep resolving there and are not rewritten.
- `docs/audits/` starts empty. The release pre-checks want a 360 before a tag,
  and this repository owes one against its own infrastructure once that exists.
- The predecessor's development journal does not travel. Its post-mortems
  describe defects fixed before v0.1.0 and reference numbers that resolve
  against the archive, and one of them documents the credential incident in
  detail — which is not content to carry into a repository heading for public.
- ADR-001 through ADR-005 travel unchanged. ADR-002 in particular still reads
  that the repository keeps the name `protocol-modbus`, which was true when it
  was written; an ADR is a dated decision, not a description of the present.
- The v0.1.0 tag exists in both repositories over slightly different trees: the
  archive's carries the audit report, this one does not.

## Related

- ADR-002 — the naming decision that left the repository name open
