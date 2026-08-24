# ADR-016: Deferred work is closed, and the closure carries the trigger

**Status:** Accepted
**Date:** 2026-08-24
**Upstream:** filed as braboj/solid-ai-templates#1052 against
`templates/base/workflow/issues.md`. With the domain skin off, the convention is
that a deferral's trigger needs a named watcher whether or not the ticket stays
open. The template's model assumes an open issue is one, and an open issue is
not a watcher for a condition that fires in a different repository.

## Context

`base-issues-defer` states that work which is valuable but intentionally
deferred belongs in an open, unmilestoned issue with explicitly named trigger
conditions, and that the empty milestone field is what carries the scheduling.

The project followed it. #68 and #70 were both written to that shape, down to
the opening line the template prescribes:

> Do not pick up before the trigger condition fires.

Each named its trigger as an observable event — an upstream tag containing
`templates/base/core/examples.md` for #68, the owner opening the PyPI
discussion for #70 — and each carried acceptance criteria so the work would be
sized when picked up. Both were unmilestoned, correctly labelled, and stable
across several sessions.

On 2026-08-24 the owner closed both, in two separate instructions during one
session. Neither closure decided the underlying question. #70 did not move the
distribution model off PyPI, and #68's trigger had been re-verified against the
remote that same session and still had not fired.

That is a divergence from a rule the project had been following deliberately,
and repeating it twice in one session makes it policy rather than an exception.
Recording it is what stops a later session resolving the template chain,
reading `base-issues-defer`, finding two closed tickets that match its shape
exactly, and having no way to tell a decision from an oversight.

The closures also cost something the template does not discuss, because the
template assumes the question never arises. An open ticket was the only thing
watching for #68's trigger, and #68 additionally held a judgement about
`docs/decisions/008-resolve-the-platform-template-layer.md`. Three of its
passages carry counts computed against an older submodule pin, and the ticket
argued a supersession ADR would be churn precisely because something tracked
the drift. Closing the tracker does not make the counts accurate.

What the template gets right is that scheduling and triage are different axes.
This record changes only where an unscheduled item lives, not whether it was
triaged.

## Decision

1. Work that is deferred on an external trigger is closed as `NOT_PLANNED`
   rather than carried open and unmilestoned.
2. The closing comment MUST carry the trigger and the reopen condition. A
   closure that records only "deferred" deletes the information the open ticket
   was holding.
3. The closing comment MUST state what loses its watcher. Where the ticket was
   the only thing tracking a drift, a stale count, or a condition in another
   repository, that consequence is named at the close rather than left implied.
4. Reopen the original issue; do not file a replacement. The acceptance
   criteria, the trigger wording and the discussion are the value, and a fresh
   ticket re-derives all three badly.
5. A triage label is NOT applied. `wontdo` means acknowledged and not going to
   be addressed, which misdescribes work that is expected back. The state
   reason plus the closing comment carry the meaning.
6. No holding milestone is created. `platform-github` forbids a named lane for
   unscheduled work, and closing the issue removes the need for one.

```text
  valuable work, trigger not yet fired
              |
              v
   +----------------------+
   |  closed NOT_PLANNED  |
   |  comment carries:    |
   |    - the trigger     |
   |    - reopen, do not  |
   |      refile          |
   |    - what lost its   |
   |      watcher         |
   +----------------------+
              |
   trigger fires, noticed by a
   person or an unrelated read
              |
              v
      reopened, same number,
      acceptance criteria intact
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep them open and unmilestoned, as `base-issues-defer` says | The conformant option, and the owner declined it twice in one session after the concern was raised once. Continuing to argue it would re-litigate a settled decision; leaving it unrecorded would leave the tree contradicting a pinned rule with no explanation. |
| Close, and record nothing | Cheapest, and it is the option this record exists to reject. Two tickets written to a template's exact shape, closed without a reason, are indistinguishable from a backlog someone gave up on. |
| Close with the `wontdo` triage label | The label is available and terminal, which is the appeal. It also states the opposite of what is true — both items are expected back — and a future reader filtering on it would conclude the project rejected PyPI outright. |
| A PLAYBOOK note instead of a record | Right shape for a recipe, wrong shape for a divergence. The PLAYBOOK says how to do a thing; it weighs no alternatives and carries no rationale, so a template bump that moves `base-issues-defer` would read against nothing. |
| Keep a `Deferred` milestone as the holding lane | Surfaces the set in one click. `platform-github` rules it out explicitly: an empty milestone field already says unscheduled, and a lane's meaning is lost the moment the milestone is closed or deleted. |

## Consequences

- An empty open-issue list now means the backlog is genuinely empty rather than
  merely unscheduled. That is a real gain in signal and the reason the owner
  asked for it.
- A trigger that fires in another repository produces no signal on this side.
  Nothing polls for it, and the detection mechanism is whoever next reads the
  affected surface. This was already true while the tickets were open — #68's
  trigger was checked by hand each session, never automatically — so the
  closure removes a reminder, not a mechanism.
- ADR-008's stale counts have no tracker. They remain harmless while nothing
  reads them as current, and the judgement that a supersession ADR would be
  churn should be re-decided rather than inherited when the submodule bump is
  picked back up.
- Reopening is cheap and lossless, which is what makes the trade acceptable.
  The number, the acceptance criteria and the trigger wording all survive.
- The project carries another recorded divergence from the pinned templates.
  Per `base-docs`, a reconciliation that touches `base-issues-defer` must state
  whether this divergence still holds, rather than reading it as a gap to
  close.

## Related

- ADR-008 — the platform template resolution whose counts #68 was tracking
- ADR-014 — the other recorded divergence from a pinned template rule, and the
  precedent for bounding a divergence rather than taking an amnesty
- ADR-015 — merged the same day and describes #68 four times as open, once as
  "the open reconciliation whose recurrence this prevents". Those readings were
  accurate when written and are not corrected in place, because a merged record
  is immutable. This record is where a reader who follows them lands: the guard
  ADR-015 installs is unaffected by the closure, since it compares the block
  against the chain the pin resolves and never consults the tracker
- #68 and #70 — the two closures this record generalises from
