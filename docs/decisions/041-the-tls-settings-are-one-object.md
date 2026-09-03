---
id: "041"
status: Accepted
date: 2026-09-03
category: protocol
supersedes: []
superseded_by: []
---

# ADR-041: The TLS settings are one object, and unset is not a value

**Upstream:** filed as braboj/solid-ai-templates#1421 against
`templates/base/core/config.md`. With the domain skin off: a sentinel earns its
place where a setting has no single default, not merely where the default is
also a legal value. The template argues for unset-means-default from the second
condition alone, which reads as ceremony until a field turns up whose correct
default depends on which consumer is asking.

## Context

Both simulators took the TLS configuration as eight loose keyword arguments
beside the host, the port and the fragment size. `SECURITY.md` documents three
of them as the weakening surface, and `CLAUDE.md` 2.4 makes the defaults
load-bearing while permitting an explicit relaxation.

Nothing grouped them, so nothing could answer what a call had weakened. A
caller who wrote one argument believing they wrote another got a session that
was weaker than they thought, and the only record was the argument list itself.

### Two settings have no single correct default

`protocol` and `verify_hostname` differ by side. A client wants
`PROTOCOL_TLS_CLIENT` and hostname checking on; a server wants
`PROTOCOL_TLS_SERVER` and hostname checking off, because a server has no name
to check and the `ssl` module refuses it outright. One object serving both
sides cannot store a resolved value for either field without being wrong for
one of them.

```text
  eight loose arguments             one object
  ---------------------             ----------
  secure=True,                      tls=TlsSettings(
  cert=..., key=..., ca_chain=...,      cert=..., key=..., ca_chain=...,
  ciphers=None,                         verify_hostname=False,
  verify_mode=CERT_REQUIRED,        )
  verify_hostname=False,
  ssl_options=OP_ALL,               relaxations(CLIENT) -> one entry
                                    relaxations(SERVER) -> none
  weakened: unanswerable
```

### The cipher format

The four header TODOs this issue inherited asked for a friendlier format than
the OpenSSL cipher string. A mapping from friendly names to suites is a table
this project would own, against a suite list OpenSSL owns and changes between
versions and security levels.

## Decision

1. **`TlsSettings` is a frozen record holding the certificate material and
   every TLS option.** Both simulators take it as `tls`, and `context(role)`
   builds the side's context from it. The two simulators previously carried the
   same twenty lines of context construction; they now carry none.

2. **Passing an instance is what turns TLS on.** `secure` is gone. It was a
   boolean flag beside the material it guarded, so `secure=False` with
   certificates silently ignored them and `secure=True` without raised from
   inside `load_cert_chain` naming neither.

3. **Unset is a sentinel distinct from every legal value.** `UNSET` is its own
   type rather than `None`, because `None` is legal for `ciphers` and means the
   interpreter's own suite. Unset means the baseline for the role the context
   is built for, which is the only thing that can be right for both sides.

4. **`relaxations(role)` names every weakening the object asks for**, and both
   simulators log the list at construction. The report is role-aware:
   `verify_hostname=False` is a weakening on a client and the baseline on a
   server, so reporting it on both would bury the real one under a permanent
   one.

5. **The cipher string stays OpenSSL format.** It is passed through verbatim.
   The caller's usual source is the peer's own configuration, which is already
   such a string, and a friendlier layer would be a second copy of a list this
   project does not own.

6. **The floor keeps its position after the caller's options,** and moves onto
   `TlsSettings` as `MINIMUM_VERSION`. It was a constant on each simulator,
   which is two homes for one specification requirement.

7. **Nothing is aliased.** Every call constructing a secure simulator breaks at
   0.6.0, in the same release as the module rename and the PEP 8 pass, and the
   changelog is the notice.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Keep `secure` and add the object beside it | Smallest break, and the two would then disagree. A caller passing settings with `secure=False` gets plaintext and no error, which is the defect being removed rather than a state worth representing |
| Use `None` as the sentinel | One less type. It collides on `ciphers`, where `None` is a real value, so the one field whose default is also legal is the field the scheme cannot express |
| Resolve the role at construction, with two classes | `TlsClientSettings` and `TlsServerSettings` need no sentinel for the two role-varying fields. It doubles the type for one difference, and a caller testing both sides of one configuration then writes it twice and keeps the copies in step |
| Two methods rather than a role enum | Avoids the parameter. `context()` and `relaxations()` would become four methods, and the role would still be a concept the caller has to know without a name to look up |
| Map friendly cipher names onto suites | What the TODOs asked for. The mapping ages against OpenSSL releases and security levels, it hides which suites a name selected at the moment a test is being explained, and the caller usually already holds the peer's own string |
| Leave the floor on the simulators | No move to justify. It is a property of the TLS configuration and both copies had to be edited together, which is the shape that eventually diverges |

## Consequences

- Every caller constructing a secure simulator breaks. The eight arguments
  become one, and no alias is offered.
- `DEFAULT_CIPHERS` and `MINIMUM_TLS_VERSION` are gone from both simulators.
  Reading either name now is an `AttributeError` rather than a stale value.
- The context construction has one home, so the hostname-before-verify-mode
  ordering that the `ssl` module requires is written once instead of twice.
- `pyomb.tls` is deferred from the package root beside the simulators, because
  it imports `ssl` and binding it eagerly would restore the cost the deferral
  exists to avoid.
- A weakening is now logged rather than merely permitted. A caller who wanted
  the weakening sees one line per relaxation and no error.
- The new module carries no entry in either freeze table, so it is held to the
  full rule set and to `mypy --strict` from its first commit.
- The ordering in decision 6 is pinned by a test that asserts the order of two
  writes rather than a resulting value. No value distinguishes the orderings,
  which is why the assertion reaches for the sequence instead.

## Related

- Issue #194 -- the surface this record settles
- ADR-039 -- the record that broke the same public API without aliases
- ADR-038 -- the record that renamed the modules and the classes
