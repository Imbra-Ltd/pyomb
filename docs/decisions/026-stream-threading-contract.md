---
id: "026"
status: Accepted
date: 2026-08-28
category: protocol
supersedes: []
superseded_by: []
---

# ADR-026: The stream components keep the threading contract they advertise

## Context

`ModbusTcpSender` and `ModbusTcpReceiver` each build a lock and a stop event in
their constructor. The sender never acquired its lock. Neither class ever read
its stop event, so `stop()` returned having changed nothing that a later call
could observe.

The receiver acquires its lock in one place, guarding the append to its packet
list. That single use is why the sender's omission stayed invisible. The pair
looked symmetric, and a test asserting that each holds a working lock passed
for both of them.

So the classes advertised a threading contract they did not keep. The
apparatus was present, public and inert. Nothing in this library drives either
class on a thread, so no existing test could have failed on it.

Both classes are exported from the package root. A caller reading the
constructor sees a lock and a stop event and reasonably concludes that
concurrent use is supported.

## Decision

The contract is made real rather than withdrawn. Both classes are safe to
drive from more than one thread, and both state that in their class docstring.

1. The sender's lock covers the fragment settings and the send loop together,
   in one acquisition. A setter cannot land between two of the three values
   being copied into the stream, and two callers cannot interleave fragments
   on one socket.

2. The receiver's lock covers its packet list and its fragment setting. It is
   taken per append rather than held across the receive loop. Holding it there
   would deadlock against the append, because the lock is not reentrant.

3. `run_once` reads the stop event in both classes. A stopped component does
   no work, and the receiver ends its loop at the next message boundary rather
   than when the socket happens to drain.

```
  sender.run_once()              receiver.run_once()
        |                              |
        +-- stopped? --> return        +-- stopped? --> return
        |                              |
        +-- [ acquire ]                +-- [ acquire ] copy setting [ release ]
        |     copy settings            |
        |     send frame               +-- loop
        |     send frame               |     stopped? --> break
        |                              |     receive frame
        +-- [ release ]                |     [ acquire ] append [ release ]
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Guard the fragment settings only | Fixes the torn configuration and leaves the worse hazard in place. Two callers would still interleave fragments and put a malformed frame on the wire, which is the one failure a wire protocol cannot absorb. |
| Declare the pair unsafe and delete the sender's lock | Honest, and it removes a capability rather than adding one. The receiver's lock would stay, because it guards a genuinely shared list, leaving the pair asymmetric for the next reader to re-litigate. |
| Fix the lock and leave the stop event unread | Splits one defect family across two changes. Both fields are threading primitives wired to a public method and never consulted, and finding the first is what prompted the search that found the second. |
| Hold the receiver's lock across its whole receive loop | Deadlocks on the first message, because the append inside the loop takes the same non-reentrant lock. It would also block a reader for as long as the socket stays open. |

## Consequences

| Consequence | Detail |
| --- | --- |
| A setter waits for a send | The sender holds its lock across the send loop, so a setter blocks for the duration of a fragmented send, including its delays. A torn frame costs more than a late setting. |
| `stop()` changes behaviour | A caller that set the event and then called `run_once` previously got a full run. It now gets none. Nothing in this repository relied on the old behaviour. |
| The promise is now testable | A recording lock and a logging socket sharing one event log show whether the send loop ran inside the lock. Asserting that a lock object works cannot show it. |
| The classes stay symmetric | Both keep a lock, both keep a stop event, and both now use them. A reader comparing the two finds the same contract rather than an unexplained difference. |

## Related

- ADR-009 records the other standing decision about what a public component of
  this library promises its caller.
