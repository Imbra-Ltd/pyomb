---
id: "050"
status: Accepted
date: 2026-09-07
category: protocol
supersedes: []
superseded_by: []
---

# ADR-050: The server dispatches on the request class

**Upstream:** `none`. The rule is that a branch guarding a call MUST test the
property the call actually requires, and that a lookup table a caller can
rewrite cannot stand in for a type. That is general enough to state, and the
tell here -- a checker-silencing cast per branch -- is what makes it findable,
which a template rule would have to carry to be worth anything.

## Context

`ModbusPduParser.register` is public and documented as the way to model a PDU
shape this library does not carry. The registry maps a function code to the
class that parses it, so registering a class against a code already answered
replaces the built-in one. That is a supported thing to do.

The server dispatched on the parsed PDU's function code field, then handed the
PDU to a factory that reads fields only the built-in class declares. The field
and the class agreed only because the registry said so, and the registry is
exactly what a caller had just changed.

The result was an `AttributeError`, converted to a slave-device failure, which
retires the connection. A peer got a closed socket for a request the server
had understood well enough to route.

Annotating the module made the gap visible without closing it: eleven of the
twelve branches needed a `cast` to tell the checker the class was what the
field implied. The cast was honest about the assumption. Nothing tested it.

## Decision

1. **Branch on the class** — each dispatch arm MUST test
   `isinstance(request.pdu, ModbusRequestFCn)` rather than comparing the
   function code field. The narrowing that follows is what the factory needs,
   so no branch carries a cast.

2. **A class that does not fit falls through** — a registered class that is
   not the subclass its factory reads reaches the final branch and earns an
   exception response, with the connection kept.

```text
  registry:  fc 1 -> whichever class is registered
                        |
                        v
              +-------------------+
  dispatch    | isinstance check  |
              +-------------------+
                 |            |
          fits   |            |  does not fit
                 v            v
        +-----------+   +---------------------------+
        | factory   |   | exception response 0x04,  |
        | reads its |   | connection kept           |
        | own fields|   +---------------------------+
        +-----------+
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the field dispatch and add a type check inside each factory | Twelve checks instead of twelve branches, each raising from a place with no connection to answer on. The dispatch is where the routing decision belongs |
| Refuse a registration that replaces a built-in code | Modelling a shape this library does not carry is the documented purpose of the registry, and the codes it carries are the ones a caller most wants to vary |
| Keep the casts and document the assumption | A cast states an assumption to the checker and tests nothing. The defect was reachable through the public API and had no failing test |
| Dispatch through a table keyed by class | The same twelve arms with a layer between them, and the factories take different argument counts -- FC7 takes none. A table would need a uniform signature the factories do not have |

## Consequences

- The `cast` import leaves `server_simulator.py`. All eleven casts go with it.
- A caller registering a subclass of the built-in class still gets the
  built-in behaviour, since `isinstance` accepts a subclass. That is the
  cheapest way to extend a code rather than replace it, and it now works.
- A caller registering an unrelated class for a code the server answers gets
  an exception response rather than a drop. They get no way to make the server
  answer that class -- the responder is still the built-in one.
- Function code 7 gains an `isinstance` branch against `ModbusRequestFC7`,
  where it previously compared the field and passed no argument. Its factory
  takes none, so the narrowing buys nothing there beyond consistency.
- Adding a function code now means importing its request class into the
  simulator. PLAYBOOK 2.1 step 4 says so.
- The client simulator's `send_request` branches on a code the caller passes
  rather than on a parsed PDU, so nothing there changes.
