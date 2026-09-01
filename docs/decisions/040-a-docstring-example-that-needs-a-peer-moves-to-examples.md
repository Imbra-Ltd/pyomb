---
id: "040"
status: Accepted
date: 2026-09-01
category: process
supersedes: []
superseded_by: []
---

# ADR-040: A docstring example that needs a peer moves to examples/

**Upstream:** filed as braboj/solid-ai-templates#1408 against
`templates/base/core/examples.md`. The convention with the domain nouns
removed, in two parts:

- An exemption from an example gate is a holding position, not an outcome.
- Where its reason is that the example needs a peer, the demonstration moves
  to the runnable-examples directory and the exemption retires with it.

## Context

Three class docstrings in the transport module each opened a socket to a
Modbus server on the local machine that nothing starts. All three raised a
connection error wherever they ran, including for the reader who copied them:

```text
pytest --doctest-modules src/pyomb/stream.py
3 failed, 0 passed
ModbusTcpReceiver   ConnectionRefusedError [WinError 10061]
ModbusTcpSender     ConnectionRefusedError [WinError 10061]
ModbusTcpStream     ConnectionRefusedError [WinError 10061]
```

Nothing reported it for as long as they existed, because nothing executed any
docstring example. When the gate that executes them was added, these three
were frozen by one deselect entry each, one docstring at a time rather than by
excluding the module, so a fourth example in the same file kept its gate.

That freeze was the correct move and it settled nothing. The examples were
still examples a reader could not run; the exemption only stopped the suite
saying so. The gate went green over the docstrings it was added to catch.

The two obvious repairs are both worse than the freeze. Making each docstring
runnable puts server startup, readiness waiting and teardown inside a
docstring, three times, and pays that cost on every doctest run. Leaving them
exempt keeps unrunnable code at the place a reader is most likely to copy
from.

The directory that already solves it is `examples/`. A peer may be started
there, CI executes every file in it against an install built the way a
consumer builds one, and one example, `fragmented_send.py`, already drove this
very transport against the project's own in-process server simulator.

## Decision

1. **The demonstration moves** — a docstring example that cannot run without a
   peer MUST move to `examples/`, where the peer can be started, rather than
   stay exempt. The docstring then names the example under a `Usage:` heading
   and MUST NOT carry a shortened copy of it.

2. **The exemption retires in the same change** — retiring it MUST remove the
   name from both places it is recorded, the `addopts` deselect list in
   `pyproject.toml` and the `DEFERRED` tuple stating why, which
   `tests/test_doctests_are_gated.py` asserts agree.

3. **The machinery stays** — the empty exemption list, its drift test and its
   agreement test remain. The next example needing a peer is a question of
   when, and the freeze-one-instance shape is what keeps a sibling example
   gated when it arrives.

4. **An exemption has one admissible reason** — an example needing a peer the
   project cannot start. An example failing for any other reason is a defect
   in the example and is fixed, never exempted.

```text
  before                              after

  docstring  >>> sock.connect(..)     docstring  Usage: see examples/x.py
      |          raises for every         |          names it, runs nothing
      |          reader who copies        |
      v                                   v
  deselect   frozen, green            examples/  peer started in-process
      |          still unrunnable         |          CI runs it per install
      v                                   v
  gate       passes over the defect   gate       passes over nothing
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Rewrite each docstring to start the server simulator | Puts thread lifecycle into three docstrings and pays three server starts on every doctest run, to demonstrate what one example file already shows |
| Leave the three deselects in place | The freeze is honest and changes nothing for the reader; an exempt example is still one nobody can run, and the gate reads as covering it |
| Delete the three examples with no replacement | Loses the transport's only documented usage, which is the part of this library least visible from the packet classes -- framing is arithmetic you can read, driving a socket is not |
| Exclude the whole module from the gate | Narrows what the gate evaluates rather than which instances fail, which the freeze rules forbid, and drops the fragmenter example that runs |

## Consequences

`ModbusTcpStream` names `examples/fragmented_send.py`, which already existed.
`ModbusTcpSender` and `ModbusTcpReceiver` name
`examples/capture_a_burst_of_packets.py`, which is added here. It holds both
ends of a connection in one process, sends three requests in a single shot,
and captures them at the far end. So it needs no simulator, and it terminates
on the sending socket closing rather than on a timeout.

`pytest --doctest-modules src/pyomb/stream.py` now reports one passing example
and no skips, where it reported three failures under no gate and three
exemptions under one.

The examples directory grows from six files to seven and its index gains the
command with its real output. Three of the seven now open sockets, which the
note on ports there records.

The floor in `tests/test_doctests_are_gated.py` was re-measured rather than
adjusted: 37 gated examples, 36 in the packet classes and one in the
fragmenter. The number is unchanged by this work, because the three removed
examples were exempt and so were never counted in it.

What this makes harder: a reader looking at the transport class no longer sees
code beside its description, and has to open a second file. That is the price
of the code being runnable, and it is the trade `base-docs` already makes when
it says a document references an example rather than duplicating it.

The empty `DEFERRED` tuple leaves one test asserting over nothing. It is kept
rather than deleted, because deleting it would have to be written back the
first time an example needs exempting. A test that passes vacuously is cheaper
than a guard that is missing when it is next needed.

## Related

- ADR-024 drew the boundary between `scripts/` and `examples/`, which is what
  makes `examples/` the destination this record sends a demonstration to.
