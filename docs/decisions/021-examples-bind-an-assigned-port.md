---
id: "021"
status: Accepted
date: 2026-08-26
category: repository
supersedes: []
superseded_by: []
---

# ADR-021: The examples bind an assigned port, not the registered one

**Upstream:** filed as `none`. With the domain skin off the convention is that
a runnable example demonstrating a privileged or otherwise reserved resource
has to bind the unprivileged equivalent and say so, or it cannot be executed by
the automation that keeps it honest. The examples template already requires the
execution; it does not name the collision, and one project meeting it once is
not yet evidence the rule generalizes. Revisit if a second project hits it.

## Context

`templates/base/core/examples.md` entered the resolved chain at `v2.45.0` and
governs a project shipping an `examples/` directory. It requires one file per
journey, an index pairing each with real output, offline execution, and a
continuous-integration job that installs the project the way a consumer does
and runs every file. That job is the point: an example nothing executes rots
quietly, and the index then documents behaviour the library no longer has.

The four journeys this project documents come from the README. Two of them need
a Modbus server, and the README shows them against port 502, which is the
registered Modbus port and what a real device listens on.

A port below 1024 is privileged on Linux. The job runs as an ordinary user, so
an example fixed at 502 raises `PermissionError` before reaching anything the
example is about. The test suite already met this and answered it the same way,
binding port 0 so the operating system assigns a free port; the server
simulator reports the assignment once its listener is up.

So the requirement to execute every example and the wish to mirror the README
exactly cannot both hold. Something has to differ, and the choice is what
differs and where a reader is told.

## Decision

1. **Assigned port in the examples** -- an example needing a server passes
   `port=0` and reads the assignment back off the simulator once its listener
   is up. It never hard-codes a port.
2. **The README keeps 502** -- it documents what a consumer talks to, which is
   a real device on the registered port. Rewriting it to 0 would trade an
   accurate document for an executable one.
3. **The divergence is stated where it is met** -- `examples/README.md` says
   beside the affected commands that 502 is the registered port the project
   README shows, and that 0 is what lets the example run unprivileged. A reader
   who notices the difference finds the reason without leaving the page.
4. **Printed ports are shown as a placeholder** -- an assigned port differs
   every run, so the index shows `<assigned>` rather than a captured number
   that would read as reproducible and never reproduce.
5. **The rule is the reach, not the number** -- an example may not require a
   privileged resource of any kind. A future example needing one binds the
   unprivileged equivalent and says so, or it does not ship.

```text
   an example needs a server
             |
             v
   +----------------------------+
   |  can it bind unprivileged? |  no
   +----------------------------+-----> it does not ship
             | yes
             v
      port=0, read the assignment back
             |
             v
   +----------------------------+
   |  index states why it is    |
   |  not the registered port   |
   +----------------------------+
             |
             v
      the smoke job runs it unmodified
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Read the port from an environment variable, defaulting to 0 | Lets a privileged reader reproduce the README byte for byte, and buys that with a configuration surface on a file whose whole job is to be read in one pass. The configuration template asks for a prefixed name and fail-fast validation, which is a lot of apparatus around one integer, and the default path is what runs anyway. |
| Ship only the two examples needing no socket | Fully offline, no port question, and it drops the two journeys most worth executing. Fragmentation and the simulator pair are where this library differs from a general-purpose one; leaving them as prose keeps the untested half untested. |
| Rewrite the README to bind port 0 | Removes the divergence by making both sides wrong. A consumer talks to a device on 502, and a quick start that binds an arbitrary port teaches the wrong thing to save an explanatory sentence. |
| Give the job elevated privileges so 502 binds | Mirrors the README exactly and is the worst option here. It grants the smoke job a capability nothing else in the pipeline has, to run documentation, and a privileged job is not the environment a consumer has either -- so it would prove less while risking more. |
| Skip the socket examples in the job and run them by hand | Keeps the files and gives up the property that makes them worth keeping. A non-blocking or unrun example is a deleted example with extra steps, which the examples template names directly. |

## Consequences

- Every example runs in the job, unmodified, as an ordinary user. The count
  guard in that job means an empty directory fails rather than passing.
- The examples are not byte-identical to the README snippets. That is a real
  cost: a reader comparing them finds one line different in each of two files,
  and it is answered by a sentence rather than by structure.
- The index cannot show a captured port, so one value in each of two outputs is
  a placeholder. Every other line in those blocks is a real capture.
- A future example needing a privileged resource has a stated answer rather
  than a fresh argument, and the answer may be that it does not ship.
- Nothing here constrains the library. The simulator already accepted an
  assigned port and already reported it; this decides only how the examples use
  what exists.

## Related

- #108 -- the issue that asked for the directory, and the discussion that
  weighed the three options above
- `examples/README.md` -- where the divergence is stated for a reader
- PLAYBOOK 3.20 -- how to reproduce the job locally, and why a throwaway
  environment rather than the development one
