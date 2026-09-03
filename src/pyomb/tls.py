"""TLS configuration for the simulators, as one inspectable object.

The settings a caller may weaken for interoperability testing travel together
rather than as loose keyword arguments, so the set can be reported as a set.
What a caller did not choose stays distinguishable from what they chose, which
is what lets relaxations() name only the weakenings that were actually asked
for.
"""

import enum
import ssl
from dataclasses import dataclass
from typing import ClassVar, Final, TypeVar


class _Unset:
    """The absence of a caller's choice.

    A distinct type rather than None, because None is a legal value for
    ciphers and means the interpreter's own suite. Sharing one value between
    "said nothing" and "asked for the default" would make a caller who
    weakened nothing indistinguishable from one who set a value back to where
    it already was.
    """

    def __repr__(self) -> str:
        """Render as the name a caller writes.

        Returns:
            str : The sentinel's public spelling
        """
        return "UNSET"


UNSET: Final = _Unset()

_T = TypeVar("_T")


def _resolved(chosen: "_T | _Unset", fallback: _T) -> _T:
    """The caller's value, or the fallback where the caller said nothing.

    Args:
        chosen (_T | _Unset) : What the caller passed, or UNSET
        fallback (_T) : The value to apply when the caller said nothing

    Returns:
        _T : The value to apply
    """
    if isinstance(chosen, _Unset):
        return fallback

    return chosen


class TlsRole(enum.Enum):
    """Which side of the connection a context is built for.

    Two settings have no single default: the protocol constant and whether
    hostname checking is on. Naming the role is how one settings object serves
    both simulators without carrying a value that is wrong for one of them.
    """

    CLIENT = "client"
    SERVER = "server"


@dataclass(frozen=True)
class _RoleDefaults:
    """The baseline a role supplies where the caller chose nothing."""

    protocol: int
    verify_hostname: bool


# A client verifies the name it dialled; a server has no name to check, and
# the ssl module refuses hostname checking on a server context at all.
_ROLE_DEFAULTS: Final = {
    TlsRole.CLIENT: _RoleDefaults(
        protocol=ssl.PROTOCOL_TLS_CLIENT,
        verify_hostname=True,
    ),
    TlsRole.SERVER: _RoleDefaults(
        protocol=ssl.PROTOCOL_TLS_SERVER,
        verify_hostname=False,
    ),
}


@dataclass(frozen=True)
class TlsSettings:
    """The TLS material and options for one simulator.

    Passing an instance to a simulator is what turns TLS on; there is no
    separate flag. Every field beyond the certificate material defaults to
    UNSET, meaning the secure baseline for the role the context is built for.

    Attributes:
        cert (str) : Path to the certificate in DER/PEM format.
        key (str) : Path to the private key in DER/PEM format.
        ca_chain (str) : Path to the CA chain in DER/PEM format.
        protocol (int) : The context protocol. Unset takes the role's own
            constant, which is the only correct value for each side.
        ciphers (str) : An OpenSSL cipher string. Unset and None both mean the
            interpreter's default suite; a string narrows or weakens it and is
            reported by relaxations().
        verify_mode (ssl.VerifyMode) : Peer certificate policy. Unset requires
            one, which is what the mutual TLS of MB-TCP-Security asks for.
        verify_hostname (bool) : Whether the peer name is checked. Unset takes
            the role's baseline.
        options (ssl.Options) : Flags OR-ed into the context. They can only add
            a restriction, so a session may be pinned above MINIMUM_VERSION and
            never below it.
    """

    cert: str
    key: str
    ca_chain: str
    protocol: "int | _Unset" = UNSET
    ciphers: "str | _Unset | None" = UNSET
    verify_mode: "ssl.VerifyMode | _Unset" = UNSET
    verify_hostname: "bool | _Unset" = UNSET
    options: "ssl.Options | _Unset" = UNSET

    # The lowest protocol version the transport will negotiate. MB-TCP-Security
    # v21 requires TLS 1.2 or better (R-32) and forbids negotiating down to TLS
    # 1.1, TLS 1.0 or SSL 3.0 (R-34), so the floor is the specification's
    # rather than a preference. Declaring it matters even where OpenSSL already
    # defaults here: that default is a property of the linked library and its
    # security level, so an older or differently configured build answers
    # differently and nothing in this library would notice.
    MINIMUM_VERSION: ClassVar[ssl.TLSVersion] = ssl.TLSVersion.TLSv1_2

    def context(self, role: TlsRole) -> ssl.SSLContext:
        """Build the SSL context for one side of the connection.

        Args:
            role (TlsRole) : The side the context is built for

        Returns:
            ssl.SSLContext : A context carrying this object's settings
        """
        defaults = _ROLE_DEFAULTS[role]

        protocol = _resolved(self.protocol, defaults.protocol)
        ciphers = _resolved(self.ciphers, None)
        verify_mode = _resolved(self.verify_mode, ssl.CERT_REQUIRED)
        verify_hostname = _resolved(self.verify_hostname, defaults.verify_hostname)
        options = _resolved(self.options, ssl.OP_ALL)

        context = ssl.SSLContext(protocol)
        context.load_cert_chain(self.cert, self.key)
        context.load_verify_locations(self.ca_chain)

        if ciphers is not None:
            context.set_ciphers(ciphers)

        # Hostname checking is cleared before verify_mode is assigned:
        # PROTOCOL_TLS_CLIENT enables it by default, and the ssl module refuses
        # CERT_NONE while it is still on. It is re-applied after.
        context.check_hostname = False
        context.verify_mode = verify_mode
        context.check_hostname = verify_hostname

        context.options |= options

        # Applied after the caller's options, which are OR-ed in and so can
        # only add a restriction. options therefore still pins a session higher
        # than the floor, and neither passing a mask that omits the protocol
        # switches nor passing none at all can drop below it.
        context.minimum_version = self.MINIMUM_VERSION

        return context

    def relaxations(self, role: TlsRole) -> "tuple[str, ...]":
        """Name every weakening this object asks for, against the baseline.

        A caller weakening one setting while believing they weakened another
        cannot tell from the arguments alone. This reports what the context
        will actually carry, so a simulator can say it out loud.

        Args:
            role (TlsRole) : The side the baseline is taken from

        Returns:
            tuple[str, ...] : One phrase per weakening, empty when there are
                none
        """
        defaults = _ROLE_DEFAULTS[role]
        weakened = []

        ciphers = _resolved(self.ciphers, None)

        if ciphers is not None:
            weakened.append(f"a custom cipher suite ({ciphers})")

        verify_mode = _resolved(self.verify_mode, ssl.CERT_REQUIRED)

        if verify_mode != ssl.CERT_REQUIRED:
            weakened.append(f"peer certificate policy {ssl.VerifyMode(verify_mode).name}")

        verify_hostname = _resolved(self.verify_hostname, defaults.verify_hostname)

        # Only a weakening where the role checks hostnames at all. A server
        # context never does, so False there is the baseline rather than
        # something the caller turned off.
        if defaults.verify_hostname and not verify_hostname:
            weakened.append("hostname checking off")

        return tuple(weakened)
