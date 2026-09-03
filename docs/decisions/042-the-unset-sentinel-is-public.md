---
id: "042"
status: Accepted
date: 2026-09-03
category: protocol
supersedes: []
superseded_by: []
---

# ADR-042: The unset sentinel is public, and it is an enum so the guard narrows

**Upstream:** filed as braboj/solid-ai-templates#1435 against
`templates/stack/python-lib.md`. With the domain skin off: a sentinel a caller
is expected to compare against is part of the public API. It is a single-member
enum, because a type checker narrows a union on identity against an enum member
and not against an instance of an ordinary class.

## Context

The TLS settings object defaults every option beyond the certificate material
to a sentinel meaning the caller chose nothing. That distinction is what lets
one object serve both sides of a connection, because two of the fields have no
value that is correct for both.

The sentinel was private. The export list named the settings class and the role
enum, and `pyomb.UNSET` raised `AttributeError`. The class docstring said the
fields default to UNSET, so the surface documented a name it did not provide.

### What the weakening report does not answer

`relaxations(role)` names every weakening an object asks for. It answers for
the object as a whole, which is the common case and the reason the settings
were grouped.

It does not answer whether one named field carries a choice. A caller handed an
object they did not build -- from a fixture, a helper, another part of a suite
-- has no supported way to ask. Reaching into `pyomb.tls` is not one: the
package docstring names `pyomb.packets` as the only public submodule.

### Exporting the name is not sufficient

A guard on identity has to narrow, or the caller holds the union afterwards and
must cast. Measured with mypy 2.3 in strict mode, against a plain class and
against a single-member enum:

```text
  def via_class(value: "int | _UnsetClass") -> int:
      if value is UNSET_CLASS:
          return 0
      return value + 1     error: Unsupported operand types for +
                                  ("_UnsetClass" and "int")

  def via_enum(value: "int | _UnsetEnum") -> int:
      if value is UNSET_ENUM:
          return 0
      return value + 1     no error
```

The class form gives a caller a check they can write and cannot act on.

## Decision

1. **`UNSET` is public.** It joins the export list and the deferred-name map,
   so it is bound on first access like the settings class beside it and costs a
   codec-only caller no `ssl` import.

2. **The sentinel is a single-member enum rather than a plain class.** The
   measurement above is the reason. `settings.protocol is UNSET` now narrows
   the field to its value type, which is what makes the check usable rather
   than merely observable.

3. **Both spellings render as the name a caller writes.** An enum supplies its
   own `__str__` where a plain class falls back to `__repr__`, so the override
   covers both. Without that, any message formatting the value leaks the
   private type name.

```text
  before                          after
  ------                          -----
  pyomb.UNSET -> AttributeError   pyomb.UNSET -> UNSET
  reach into pyomb.tls            settings.protocol is UNSET
  guard does not narrow           guard narrows to int
  f"{UNSET}" -> UNSET             f"{UNSET}" -> UNSET
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep the sentinel private and add a method reporting which fields carry a choice | Smaller surface, and no singleton whose only use is identity comparison. It is stringly-typed, so a misspelled field name is caught at runtime or not at all, and it gives no narrowing whatever -- the caller still cannot use the value the guard just proved was there |
| Export the sentinel and leave it a plain class | The smallest diff, and it satisfies a literal reading of the requirement. The measurement above shows the guard then fails to narrow, so every call site pays a cast the API cannot explain |
| Export the sentinel's type as well | Lets a caller annotate a variable holding either. Nothing in the public surface returns the bare type, and a name with no use is a name to support forever |
| Leave it private and document reaching into the submodule | No code change. It contradicts the package docstring, which names one public submodule and not this one, and a documented private reach is a public API with worse discoverability |

## Consequences

- `UNSET` is public API from 0.7.0 and cannot be withdrawn without a break.
  That is the standing cost of the choice, and it is what the first alternative
  above was weighed against.
- The sentinel's type stays private, so a caller can compare against the value
  and cannot annotate against the type. Exporting it later is additive.
- The field annotations move from the old class to the enum. They are string
  annotations, so nothing outside the module reads them at runtime.
- `_resolved` drops its `isinstance` check for an identity comparison, which
  is what the narrowing rests on and is also the cheaper test.
- The suite gains a test that both spellings render as UNSET. That guards a
  regression the switch introduced rather than one that shipped, which is why
  it pins behaviour the previous implementation had for free.
- Nothing changes for a caller who does not inspect settings. The sentinel was
  already the default for every optional field.

## Related

- Issue #296 -- the gap this record settles
- ADR-041 -- the record that introduced the settings object and the sentinel
