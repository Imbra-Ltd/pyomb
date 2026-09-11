"""Everything that reads or writes a socket or a port.

Length-driven TCP framing, fragmentation and reassembly, content-driven RTU
framing over any port a caller opens, and the TLS settings a caller weakens
explicitly rather than implicitly. Neither pdu nor adu is imported the other
way around.

The TLS names are bound on first access rather than on import, same as
at the top of pyomb itself, so a caller who only wants the streaming
classes does not pay for pyomb.transport.tls importing ssl.
"""

from importlib import import_module
from typing import TYPE_CHECKING

from pyomb.transport.rtu import (
    MAX_RTU_FRAME,
    MIN_RTU_FRAME,
    BytePort,
    ModbusRtuSplitter,
    ModbusRtuStream,
    RtuRead,
    RtuSide,
    read_rtu_frame,
)
from pyomb.transport.stream import (
    ModbusFragmenter,
    ModbusFragmenterAbc,
    ModbusReceiverAbc,
    ModbusSenderAbc,
    ModbusStreamAbc,
    ModbusTcpReceiver,
    ModbusTcpSender,
    ModbusTcpStream,
)

if TYPE_CHECKING:
    from pyomb.transport.tls import UNSET, TlsRole, TlsSettings

# Each deferred name resolves against pyomb.transport.tls, the only
# submodule here that reaches ssl.
_DEFERRED = {"TlsSettings": "tls", "TlsRole": "tls", "UNSET": "tls"}

__all__ = [
    "MAX_RTU_FRAME",
    "MIN_RTU_FRAME",
    "UNSET",
    "BytePort",
    "ModbusFragmenter",
    "ModbusFragmenterAbc",
    "ModbusReceiverAbc",
    "ModbusRtuSplitter",
    "ModbusRtuStream",
    "ModbusSenderAbc",
    "ModbusStreamAbc",
    "ModbusTcpReceiver",
    "ModbusTcpSender",
    "ModbusTcpStream",
    "RtuRead",
    "RtuSide",
    "TlsRole",
    "TlsSettings",
    "read_rtu_frame",
]


def __getattr__(name: str) -> object:
    """Bind a deferred name on the first access that names it.

    Args:
        name (str) : The attribute being read from this module

    Returns:
        object : The class or value the name refers to

    Raises:
        AttributeError : The name is not one this module exports
    """
    submodule = _DEFERRED.get(name)

    if submodule is None:
        raise AttributeError(name)

    return getattr(import_module("." + submodule, __name__), name)
