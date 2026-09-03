---
id: "043"
status: Accepted
date: 2026-09-03
category: protocol
supersedes: []
superseded_by: []
---

# ADR-043: The transport takes a logger and stays silent without one

**Upstream:** filed as braboj/solid-ai-templates#1445 against
`templates/base/language/python.md`. With the domain skin off: a library
module attaches a null handler to its own logger and installs no writing
handler, so importing it writes nothing. The application tier of the same
package is what constructs a writing handler, and copying that default down
into the library core is the defect.

## Context

`stream.py` logged nothing. Every failure there was raised as a `ModbusError`
carrying a formatted message, with the original exception discarded. A short
read, a checksum mismatch and a peer that went away mid-frame all reached the
caller as one sentence and no traceback.

The simulators already take a logger, defaulting to `Logger(name=...)` from
this package. That logger attaches a console handler when it is constructed.

### The two tiers want opposite defaults

Copying the simulators' default into the transport would make importing the
codec and constructing a stream write to the host's stdout on the first failed
send. The simulators are scriptable applications and own their console; the
transport is library core, imported by every consumer of the codec.

```text
  tier          default logger              who decides the destination
  ----          --------------              ---------------------------
  simulators    Logger(...) -> stdout       the simulator, which is an app
  transport     getLogger(__name__)         the host, by configuring logging
                + NullHandler               or by injecting its own
```

Without the null handler the default is not silence. `logging.lastResort`
writes WARNING and above to stderr wherever no handler is found, so a library
that logs a warning is heard whether or not anyone asked.

## Decision

1. **The three I/O classes take a logger.** `ModbusTcpStream`,
   `ModbusTcpSender` and `ModbusTcpReceiver` accept `log`, keyword and
   defaulted, so a caller keeps control of where output goes. The parameter is
   additive and breaks nothing.

2. **The module logger is silent.** `logging.getLogger(__name__)` carries a
   `NullHandler`, attached to this module's logger and never to the root. It
   is the fallback rather than the only route.

3. **The fragmenter takes no logger.** It is pure computation with no socket,
   its methods are static, and giving it one would change a public call shape
   that a docstring example uses. Its caller gets the error, so nothing is
   silent.

4. **Levels are assigned by what a reader can act on.** A fragment boundary is
   debug; a failed send or receive is a warning. Nothing carries frame bytes:
   a byte count is diagnostic, and the payload is a peer's data.

5. **Every raise inside an except carries its cause.** Five sites gain
   `from e`, which retires the `B904` entry from this module's freeze.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Match the simulators and default to `Logger(...)` | Consistent with the sibling tier, and one line shorter. It writes to the host's stdout on the first failed send, from a library the host imported for its codec |
| Construct no logger and take one or stay silent | No module logger at all, so no null handler to explain. Every call site then guards on whether a logger was given, and the guard is the thing that gets forgotten on the path that matters |
| Log and stop raising | Turns the transport into something that reports rather than fails. A caller that ignores logs would then read a truncated frame as a whole one |
| Narrow the blind excepts in the same change | The `BLE001` entry would shrink too. Deciding which exception each site should catch is a separate reading of five paths, and bundling it hides the logging change inside a behavioural one |
| Give the fragmenter a logger by adding a constructor | Symmetry across the module. Its methods are static and a docstring example calls one that way, so the symmetry costs a public call shape for a class that performs no I/O |

## Consequences

- `log` is public API on three classes from 0.7.0. It is keyword and
  defaulted, so no existing call changes.
- A caller who configures logging sees transport warnings for the first time.
  That is the point, and it is a behaviour change for anyone who had a root
  handler installed and no transport output.
- `B904` leaves the `stream.py` freeze entry. `BLE001` stays, and the five
  blind excepts remain blind.
- The silence of the default cannot be asserted in-process: a test runner
  installs a root handler, which stops `lastResort` firing, so the assertion
  passes whether or not the null handler is there. The test runs a fresh
  interpreter, and the control that proves it discriminates is removing the
  null handler and watching that test alone fail.
- Two loggers now exist in one package with opposite defaults. A reader who
  meets the simulator pattern first will find the transport's surprising,
  which is why the split is recorded here rather than left in a comment.

## Related

- Issue #195 -- the gap this record settles, whose premise it corrects
- ADR-026 -- the record covering this module's threading contract
