---
id: "046"
status: Accepted
date: 2026-09-06
category: repository
supersedes: []
superseded_by: []
---

# ADR-046: The protocol errors take the Error suffix, behind aliases

## Context

Eight exported exception classes carry no `Error` suffix:
`ModbusIllegalFunction`, `ModbusIllegalDataAddress`, `ModbusIllegalDataValue`,
`ModbusSlaveDeviceFailure`, `ModbusAcknowledge`, `ModbusSlaveDeviceBusy`,
`ModbusGatewayPathUnavailable` and
`ModbusGatewayTargetDeviceFailedToRespond`.

PEP 8 asks an exception for that suffix, and the linter encodes it as `N818`.
Nothing reported the eight, because `N818` sat in the per-file freeze for
`errors.py`. Retiring that freeze is what surfaced them.

Each name is the Modbus specification's own wording for an exception code:
PI-MBUS-300 calls code 0x01 Illegal Function and code 0x03 Illegal Data
Value. Renaming diverges the vocabulary from the specification; keeping the
names diverges the API from PEP 8. Both are real costs.

The tie-break is what a caller writes. A caller writes `except` and reads a
traceback, so the name is read in Python's grammar rather than the
specification's, and a reader who wants the code finds it in the class
docstring and in the message the exception renders.

## Decision

1. All eight take the `Error` suffix. The message text is untouched, so the
   specification's wording still reaches anyone reading a traceback.

2. The old spellings keep resolving, through the rename table the package
   `__getattr__` already had a resolver for. Reading one emits a
   `DeprecationWarning` naming both spellings and the removal version.

3. The aliases are removed in 2.0, which the warning states.

4. The old spellings are absent from `__all__`. The package advertises the new
   names only; the old ones resolve for a caller who asks by them.

```
    from pyomb import ModbusIllegalDataValue
                              |
                              v
        name missing from the module namespace
                              |
                              v
                    __getattr__(name)
                              |
              +---------------+---------------+
              |                               |
        in _RENAMED                     in _DEFERRED
              |                               |
    warn, return the class            import the submodule
    the new name is bound to          and read the name off it
```

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| Rename with no alias | The precedent for a clean break is a rename of classes introduced one release earlier. These eight have been exported since the package had a public API, so the population that breaks is different in kind |
| Keep the names, suppress `N818` per class | Eight standing suppressions, each stating that the specification's vocabulary outranks PEP 8 -- a defensible claim, but one that has to be re-read eight times and re-argued whenever a ninth exception is added |
| Drop `N818` from `select` | Narrows the gate rather than freezing instances, so every exception class written later is ungated too |

## Consequences

- Every caller catching one of the eight by its old name keeps working, and
  hears about the rename once per name per process
- `test_package_exports.py` gains a class pinning both halves of the alias:
  that the old spelling is the same class object as the new one, and that
  reading it warns. Nothing else would fail if the alias branch were deleted,
  because the old names are not in `__all__` for the export walk to reach
- Removing the aliases in 2.0 is deleting eight map entries and the branch
  that reads them, in a change that is already touching this file
- `errors.py` leaves the ruff freeze entirely, which is the point of the work
  that surfaced this

## Related

- The exception hierarchy diagram in `docs/PLAYBOOK.md`, which carries the
  renamed classes
