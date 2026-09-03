# encoding: utf-8

"""pyomb -- Open Modbus protocol library.

Serialization and deserialization of Modbus TCP and RTU packets, fragmented
stream transport, and a scriptable server/client pair for testing Modbus
implementations.

The names re-exported here are the supported public API, alongside one
submodule that is equally public: pyomb.packets for the function-code packet
classes (ModbusRequestFC1, ModbusResponseFC3, ...). The two simulators and
the TLS settings they take are re-exported as well, bound on first use rather
than on import. UNSET travels with them: it is the value every optional TLS
setting carries until a caller chooses one, and comparing against it is how a
caller tells a choice from a default.
"""

from importlib import import_module
from typing import TYPE_CHECKING

from .errors import ModbusAcknowledge
from .errors import ModbusBaseError
from .errors import ModbusGatewayPathUnavailable
from .errors import ModbusGatewayTargetDeviceFailedToRespond
from .errors import ModbusIllegalDataAddress
from .errors import ModbusIllegalDataValue
from .errors import ModbusIllegalFunction
from .errors import ModbusMemoryParityError
from .errors import ModbusModeError
from .errors import ModbusNetworkError
from .errors import ModbusPacketError
from .errors import ModbusProtocolError
from .errors import ModbusSlaveDeviceBusy
from .errors import ModbusSlaveDeviceFailure
from .logger import Logger
from .packets import ModbusError
from .packets import ModbusHeader
from .packets import ModbusPdu
from .packets import ModbusPduParser
from .packets import ModbusRtuRequest
from .packets import ModbusRtuResponse
from .packets import ModbusTcpPacket
from .packets import ModbusTcpRequest
from .packets import ModbusTcpResponse
from .packets import ModbusViolation
from .stream import ModbusFragmenter
from .stream import ModbusTcpReceiver
from .stream import ModbusTcpSender
from .stream import ModbusTcpStream

# The simulators are named below but not imported here, because importing them
# costs every caller the ssl import: roughly 13ms against this package's own
# 35ms on CPython 3.13, so a caller who only needs the codec would pay a 38%
# penalty for a transport it never opens. __getattr__ binds them on the first
# access that names one, which puts them in the public API without moving that
# cost onto import. Note that socket, threading and select are NOT part of the
# saving: stream.py is re-exported above and imports all three, so they are
# already paid before this comment applies. Re-measure with
# `python -X importtime -c "import pyomb"` before treating the numbers as
# current.
if TYPE_CHECKING:
    from .client_simulator import ModbusClientSimulator
    from .server_simulator import ModbusServerSimulator
    from .tls import UNSET
    from .tls import TlsRole
    from .tls import TlsSettings

# Each deferred name against the submodule that defines it. The TLS settings
# join the simulators here for the same reason: pyomb.tls imports ssl, so
# binding it eagerly would put back the cost the deferral removes, and it is
# the only thing a caller needs before constructing a secure simulator.
_DEFERRED = {
    "ModbusClientSimulator": "client_simulator",
    "ModbusServerSimulator": "server_simulator",
    "TlsSettings": "tls",
    "TlsRole": "tls",
    "UNSET": "tls",
}

__version__ = "0.6.0"

__all__ = [
    "__version__",
    # Packets
    "ModbusHeader",
    "ModbusPdu",
    "ModbusPduParser",
    "ModbusError",
    "ModbusTcpPacket",
    "ModbusTcpRequest",
    "ModbusTcpResponse",
    "ModbusRtuRequest",
    "ModbusRtuResponse",
    "ModbusViolation",
    # Stream
    "ModbusTcpStream",
    "ModbusTcpSender",
    "ModbusTcpReceiver",
    "ModbusFragmenter",
    # Errors
    "ModbusBaseError",
    "ModbusProtocolError",
    "ModbusNetworkError",
    "ModbusPacketError",
    "ModbusModeError",
    "ModbusIllegalFunction",
    "ModbusIllegalDataAddress",
    "ModbusIllegalDataValue",
    "ModbusSlaveDeviceFailure",
    "ModbusAcknowledge",
    "ModbusSlaveDeviceBusy",
    "ModbusMemoryParityError",
    "ModbusGatewayPathUnavailable",
    "ModbusGatewayTargetDeviceFailedToRespond",
    # Logging
    "Logger",
    # Simulators
    "ModbusClientSimulator",
    "ModbusServerSimulator",
    # TLS
    "TlsSettings",
    "TlsRole",
    "UNSET",
]


def __getattr__(name: str) -> object:
    """Bind a deferred name on the first access that names it.

    Args:
        name (str) : The attribute being read from this module

    Returns:
        object : The class the name refers to

    Raises:
        AttributeError : The name is not one this module exports
    """
    submodule = _DEFERRED.get(name)

    if submodule is None:
        raise AttributeError(name)

    return getattr(import_module("." + submodule, __name__), name)
