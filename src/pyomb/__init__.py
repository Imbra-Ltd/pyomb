"""pyomb -- Open Modbus protocol library.

Serialization and deserialization of Modbus TCP and RTU packets, fragmented
stream transport, and a scriptable server/client pair for testing Modbus
implementations.

The names re-exported here are the supported public API, alongside one
submodule that is equally public: pyomb.packets, for the function-code packet
classes. The simulators and the TLS settings they take are re-exported too,
bound on first use rather than on import.

UNSET travels with them. It is what every optional TLS setting carries until a
caller chooses one, so comparing against it tells a choice from a default.
"""

from importlib import import_module
from typing import TYPE_CHECKING

from .errors import (
    ModbusAcknowledge,
    ModbusBaseError,
    ModbusGatewayPathUnavailable,
    ModbusGatewayTargetDeviceFailedToRespond,
    ModbusIllegalDataAddress,
    ModbusIllegalDataValue,
    ModbusIllegalFunction,
    ModbusMemoryParityError,
    ModbusModeError,
    ModbusNetworkError,
    ModbusPacketError,
    ModbusProtocolError,
    ModbusSlaveDeviceBusy,
    ModbusSlaveDeviceFailure,
)
from .logger import Logger
from .packets import (
    ModbusError,
    ModbusHeader,
    ModbusPdu,
    ModbusPduParser,
    ModbusRtuRequest,
    ModbusRtuResponse,
    ModbusTcpPacket,
    ModbusTcpRequest,
    ModbusTcpResponse,
    ModbusViolation,
)
from .stream import ModbusFragmenter, ModbusTcpReceiver, ModbusTcpSender, ModbusTcpStream

# Named below but not imported: they reach ssl, and __getattr__ binds them on
# first access instead. See PLAYBOOK, deferred imports, for the measurement.
if TYPE_CHECKING:
    from .client_simulator import ModbusClientSimulator
    from .server_simulator import ModbusServerSimulator
    from .tls import UNSET, TlsRole, TlsSettings

# Each deferred name against the submodule defining it. The TLS settings join
# the simulators because pyomb.tls reaches ssl for the same reason.
_DEFERRED = {
    "ModbusClientSimulator": "client_simulator",
    "ModbusServerSimulator": "server_simulator",
    "TlsSettings": "tls",
    "TlsRole": "tls",
    "UNSET": "tls",
}

__version__ = "0.6.0"

# Grouped by the submodule each name comes from. Sorting interleaves the
# groups and strands every comment below it.
__all__ = [  # noqa: RUF022
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
