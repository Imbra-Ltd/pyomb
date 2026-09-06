---
id: "047"
status: Accepted
date: 2026-09-06
category: tooling
supersedes: ["003"]
superseded_by: []
---

# ADR-047: The ruff freeze is retired

**Upstream:** filed as braboj/solid-ai-templates#1571 against
`templates/base/workflow/quality-gates.md`. The generic rule:
a retrofit freeze is retired by narrowing each suppressed site to what its
body can raise, and a contract test over the whole class hierarchy is what
proves the narrowing is not too tight.

## Context

The `per-file-ignores` table was a retrofit ratchet. It recorded, per file,
the rules that file broke on the day ruff replaced flake8, so an existing
file could not get worse and a new file was gated on everything.

Shrinking it was the migration. Nine entries became one over five slices,
and the last held `B904` and `BLE001` on the codec:

```bash
ruff check --isolated --select B904,BLE001 src/pyomb/packets.py --statistics
```

That reported 140 findings -- 70 of each, over the same 70 handlers. Every
one was `except Exception as e:` re-raising `ModbusPacketError` without
`from`.

Those 70 were the reason this was the last slice. The project already bans a
blind except, and a codec's whole subject is untrusted input, so what escapes
a parser fed a malformed frame was the thing under change.

Two ways to clear both rules existed, and they are not equivalent. Chaining
the cause with `raise ... from e` clears `B904` outright, and clears `BLE001`
too, because that rule reports a blind except only where the caught exception
goes unused. The freeze would empty and the 70 blind excepts would remain.

## Decision

1. **Narrow each handler to what its body can raise.** The 70 sites fall in
   three shapes, measured rather than assumed: 33 wrap a `struct` call, 32
   wrap another packet operation that already raises `ModbusPacketError`, and
   5 do both.

2. **Chain the cause.** Every re-raise carries `from e`, so the originating
   `struct.error` travels with the wrapper.

3. **Let the contract test adjudicate the residue.** A narrowing that is too
   tight lets a raw exception out through a clause nobody wrote. Four sites
   needed a third type and the test named all four:

   - three ADU serializers take `AttributeError`, because a caller's header
     or PDU is taken on trust and need not be a packet at all
   - the error PDU's serializer takes `TypeError`, because it adds the
     exception mask to the function code before it packs

4. **The table keeps its two exemptions.** `tests/**` and `checks/**` drop
   the `D` rules, because a test's name carries its intent. Neither is a
   freeze, and neither is retired here.

5. **What the superseded record decided about the gate stands.** Two parts
   of it are untouched here:

   - the full rule selection stays enabled
   - ruff stays pinned to a minor range, because a release adding rules to
     a selected family would fail the gate on untouched code

```text
       before                            after
  +----------------+              +----------------+
  | select: all    |              | select: all    |
  +----------------+              +----------------+
  | packets.py:    |              | tests/**: D    |
  |   B904 BLE001  |  -- 140 -->  | checks/**: D   |
  +----------------+   findings   +----------------+
   one src/ module                 no src/ module
   measured short                  measured short
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Add `from e` and keep `except Exception` | Clears both rules and empties the table without doing the work the table was hiding. Leaves 70 blind excepts the project bans. |
| Catch a wider tuple everywhere | Uniform and unread. It would have absorbed the four sites the contract test named, so nothing would have reported that a caller's header is taken on trust. |
| Re-freeze the two rules under a narrower entry | An entry records what was already broken, not what may be. Widening one is banned for the same reason adding a file is. |
| Leave the slice and start on the type freeze | The two are independent, and this one was one slice from done. Parking it keeps the table reading larger than the work is. |

## Consequences

- Every module under `src/` is now measured against the whole rule selection.
  The table no longer exempts source from anything.
- A `struct.error` a handler did not anticipate now escapes as itself rather
  than as a wrapped `ModbusPacketError`. The contract test is the guard, and
  it is the reason the four residual sites were found before release.
- Three ADU serializers now say in code that their header and PDU are taken
  on trust. That is a documented weakness rather than a repaired one; a type
  check at construction is a separate decision.
- The type freeze is untouched. Four override blocks over four modules remain,
  and they are the rest of the migration.
- The retired table can no longer be regenerated. Rebuilding it would need the
  findings it suppressed, which no longer exist.

## Related

- #170 -- the epic that carries both freezes, still open on the type half
- #343 -- the defect found while reading one of these 70 handlers
