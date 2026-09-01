---
id: "039"
status: Accepted
date: 2026-09-01
category: repository
supersedes: []
superseded_by: []
---

# ADR-039: The simulator API takes PEP 8 names and no aliases

**Upstream:** filed as braboj/solid-ai-templates#1405 against
`templates/base/core/quality.md`. With the domain skin off: a rename spanning
parts of one call site is deprecated whole or not at all. Aliasing the outer
name alone yields a call that resolves and then fails on its own arguments,
reporting a name the caller never wrote. The template's deprecation rule is
written per symbol and cannot see the pairing.

## Context

The two simulators expose a camelCase surface. `CLAUDE.md` 2.2 rules it out:
PEP 8 names throughout, no camelCase on any public symbol. The linter never
reported it, because `N802` and `N803` are frozen for both modules.

Bypassing the freeze measures the real surface:

```bash
ruff check --isolated --select N802,N803 src/pyomb/
```

18 findings, against the seven the issue counted. Seven are methods, and
eleven are argument sites covering seven distinct parameter names:

| Kind | Names |
| --- | --- |
| methods | `sendRequest`, `waitResponse`, `getPeers`, `setDelay`, `setConnLimit`, `setFail`, `setDataHandler` |
| parameters | `readAddress`, `readCount`, `writeAddress`, `writeCount`, `ipAddress`, `connLimit`, `inactiveTimeout` |

Instance attributes carry the same spelling and no rule reaches them at all:
`readList`, `startedEvent`, `newConnEvent`, `quitEvent`, and the three that
back a renamed parameter. A naming rule stops at the linter's rules; the
context file's does not.

### Two names for one value, and one value with three

The client takes `frag_count` and hands it to the stream as `frag_size`, five
lines apart. The server is worse: it takes `frag_count`, stores
`self.fragment_count`, and passes it as `frag_size`. The transport is the
larger surface and is already consistent, and the value is a byte count taken
as a slice width, so the transport's name is the correct one.

### An integer where the sibling parameter is a string

The server takes `ipAddress` as a 32-bit integer and converts it with
`inet_ntoa` before binding. The client's equivalent is `host`, a string. A
caller wanting one interface writes a `struct.unpack` beside a plain port
number, and the two constructors disagree about what an address is.

## Decision

```text
  one call, before                one call, after
  ----------------                ---------------
  client.sendRequest(             client.send_request(
      fc=3,                           fc=3,
      readAddress=0,                  read_address=0,
      readCount=10,                   read_count=10,
  )                               )

  a method alias alone would give:
      sendRequest -> send_request     resolves
      readAddress                     TypeError, naming send_request
                                      a method the caller never wrote
```

1. **Every public name on both simulators takes its PEP 8 spelling.** Methods,
   parameters and instance attributes alike. The attributes are in scope
   because renaming a parameter and leaving the attribute it assigns creates
   the same two-names-for-one-value defect this record removes elsewhere.

2. **`frag_count` becomes `frag_size`,** in both simulators and in the
   server's attribute. The transport's spelling wins because it is correct
   and because it is the larger surface.

3. **The server takes `host`, a string.** `""` keeps the current
   all-interfaces default, which is what `ipAddress=0` already meant, and the
   `inet_ntoa` conversion goes. The two constructors then agree on what an
   address is.

4. **No name is aliased.** All of them change at 0.6.0 and the changelog
   carries the break. A method alias is cheap and a keyword alias is not, so
   the tempting shape is to alias the methods alone. That leaves a call which
   resolves and then raises on its own keyword, naming a method the caller
   never wrote. One call cannot be half-deprecated, so the whole call breaks
   and the failure names the first thing the caller typed.

5. **`N802` and `N803` come off both freeze entries.** The findings are fixed
   rather than re-frozen, which is the direction the freeze is meant to move.
   `N806` stays: it covers three local variables, which are not public API.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Alias the seven methods, break the parameters | Consistent with aliasing wherever it is free, which is how the class rename was decided a day earlier. It produces the call above: resolved method, failed keyword, an error naming a method the caller never wrote. Cheapness is the wrong axis when the parts belong to one expression. |
| Alias everything, with `**kwargs` shims | Nothing breaks, which is the strongest argument for it. Three signatures then stop stating what they accept, the type checker loses them, and 0.7.0 inherits shims to unpick rather than entries to delete. |
| Keep `ipAddress` as an integer and rename it only | Satisfies the naming rule at the smallest diff. It keeps the defect the issue is actually about, where a caller converts a dotted quad by hand next to a plain port. |
| Accept a string or an integer for `host` | Breaks no caller at all. It puts a two-type union in the public API against the typing rule, and the forms have to be told apart at runtime for as long as the parameter exists. |
| Rename the transport's `frag_size` to `frag_count` instead | Would touch two files rather than eight. The name is wrong: the value is sliced as a width, so `count` describes nothing the code does, and the transport's spelling is used across six test modules. |
| Leave the instance attributes camelCase | Keeps the change inside the issue's stated scope. It also leaves `connection_limit` assigned to `self.connLimit`, which is the defect in rule 2 recreated by the change removing it. |

## Consequences

- Every caller of either simulator breaks at 0.6.0. There is no deprecation
  path, and the changelog is the only notice.
- Two freeze entries shrink by two rules each. Nothing else in either entry
  moves, and no rule is added anywhere.
- The server's signature loses a parameter type rather than renaming one, so
  a caller passing an integer gets a socket error rather than a name error.
  The changelog names the conversion a caller no longer performs.
- `N806` remains frozen for the server on three local variables. That is the
  freeze-retirement epic's work, not this record's.
- The client's `host` still defaults to a bytes literal while its docstring
  says string. Out of scope here and untouched.
- The record that renamed the two classes kept aliases, and this one keeps
  none. The reasoning differs rather than the policy: there the alias was a
  map entry on a resolver that already existed, here it would span a call.

## Related

- Issue #192 -- the surface this record settles
- Issue #170 -- the epic that retires the remaining freeze entries
- ADR-038 -- the record that renamed the modules and the classes
- ADR-003 -- the record that froze lint violations per file
