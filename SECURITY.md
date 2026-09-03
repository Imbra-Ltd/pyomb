# Security policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's private vulnerability
reporting: open the **Security** tab and choose **Report a vulnerability**.
That opens a channel visible only to the maintainers.

Please do not open a public issue for a security problem.

Include what you need to demonstrate the issue — affected version or commit,
reproduction steps, and impact. A proof of concept helps but is not required.

Expect an acknowledgement within five working days.

## Supported versions

The project is pre-1.0 and only the latest commit on `main` is supported.
There are no maintained release branches, and fixes are not backported.

## Scope

This library implements Modbus TCP, Modbus RTU, and the TLS transport
described by MB-TCP-Security. In scope: packet parsing of untrusted input,
the TLS configuration of the client and server, and anything that lets a peer
influence execution beyond the protocol.

Out of scope: the deliberately permissive settings the simulator exposes for
interoperability testing, when they are selected explicitly. Weak cipher
suites and disabled hostname verification are available as arguments so that
implementations can be tested against them. They are not the defaults, and a
report that they *are* the defaults is in scope.

## Using this library securely

The client and server default to the interpreter's secure cipher suite,
require peer certificates, and verify hostnames on the client side. Those
settings live on the `TlsSettings` object a simulator takes, and each one you
set to weaken the defaults is logged at construction and listed by that
object's `relaxations` method. Confine a weakened session to a test network.

Both endpoints are simulators intended for testing Modbus implementations.
They are not hardened for production control networks and should not be
exposed to untrusted ones.

## Certificate material

Never commit private keys. `.gitignore` covers the common key extensions, and
CI scans the whole history for secrets, but neither is a substitute for
generating test certificates locally and keeping them out of version control.
