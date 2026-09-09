"""pyomb -- Open Modbus protocol library.

Serialization and deserialization of Modbus TCP and RTU packets, fragmented
stream transport, and a scriptable server/client pair for testing Modbus
implementations.

The names re-exported here are the supported public API, alongside two
equally public submodules: pyomb.pdu for the function-code classes, and
pyomb.adu, most of whose classes are also re-exported here. The
simulators and the TLS settings are re-exported too, bound on first use.

UNSET travels with them. It is what every optional TLS setting carries until a
caller chooses one, so comparing against it tells a choice from a default.
"""

import warnings
from importlib import import_module
from typing import TYPE_CHECKING

from .adu import (
    ModbusHeader,
    ModbusRtuPacket,
    ModbusRtuRequest,
    ModbusRtuResponse,
    ModbusTcpPacket,
    ModbusTcpRequest,
    ModbusTcpResponse,
)
from .errors import (
    ModbusAcknowledgeError,
    ModbusBaseError,
    ModbusGatewayPathUnavailableError,
    ModbusGatewayTargetDeviceFailedToRespondError,
    ModbusIllegalDataAddressError,
    ModbusIllegalDataValueError,
    ModbusIllegalFunctionError,
    ModbusMemoryParityError,
    ModbusModeError,
    ModbusNetworkError,
    ModbusPacketError,
    ModbusPduParseError,
    ModbusProtocolError,
    ModbusSlaveDeviceBusyError,
    ModbusSlaveDeviceFailureError,
)
from .logger import Logger
from .pdu import ModbusError, ModbusPdu, ModbusPduParser, ModbusViolation
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

# The spelling each protocol error carried before it took the Error suffix
# PEP 8 asks of an exception. Both spellings resolve until 2.0 removes these.
_RENAMED = {
    "ModbusIllegalFunction": "ModbusIllegalFunctionError",
    "ModbusIllegalDataAddress": "ModbusIllegalDataAddressError",
    "ModbusIllegalDataValue": "ModbusIllegalDataValueError",
    "ModbusSlaveDeviceFailure": "ModbusSlaveDeviceFailureError",
    "ModbusAcknowledge": "ModbusAcknowledgeError",
    "ModbusSlaveDeviceBusy": "ModbusSlaveDeviceBusyError",
    "ModbusGatewayPathUnavailable": "ModbusGatewayPathUnavailableError",
    "ModbusGatewayTargetDeviceFailedToRespond": "ModbusGatewayTargetDeviceFailedToRespondError",
}

__version__ = "0.7.0"

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
    "ModbusRtuPacket",
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
    "ModbusPduParseError",
    "ModbusModeError",
    "ModbusIllegalFunctionError",
    "ModbusIllegalDataAddressError",
    "ModbusIllegalDataValueError",
    "ModbusSlaveDeviceFailureError",
    "ModbusAcknowledgeError",
    "ModbusSlaveDeviceBusyError",
    "ModbusMemoryParityError",
    "ModbusGatewayPathUnavailableError",
    "ModbusGatewayTargetDeviceFailedToRespondError",
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
    # A retired spelling resolves to its replacement, which is bound eagerly
    # above. Nothing is deferred here, so the lookup below would not find it.
    renamed = _RENAMED.get(name)

    if renamed is not None:
        warnings.warn(
            f"{name} is renamed to {renamed} and is removed in 2.0",
            DeprecationWarning,
            stacklevel=2,
        )

        return globals()[renamed]

    submodule = _DEFERRED.get(name)

    if submodule is None:
        raise AttributeError(name)

    return getattr(import_module("." + submodule, __name__), name)
