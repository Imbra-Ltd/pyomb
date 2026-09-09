"""Deprecated: import from pyomb.adu instead.

pyomb.packets.framing split into pyomb.adu's tcp and rtu modules. Every
name below still resolves to the exact class its new module defines,
bound on first access rather than imported eagerly, and each access
warns naming the module that now holds it. Removed in 0.9.0.
"""

import warnings
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyomb.adu import (
        CRC_FMT,
        CRC_SIZE,
        ModbusHeader,
        ModbusRtuPacket,
        ModbusRtuRequest,
        ModbusRtuResponse,
        ModbusTcpPacket,
        ModbusTcpRequest,
        ModbusTcpResponse,
        calc_crc16,
        validate_crc,
        validate_mbap_length,
    )

# Each retired name against the submodule of pyomb.adu that now defines it.
_MOVED = {
    "ModbusHeader": "tcp",
    "validate_mbap_length": "tcp",
    "ModbusTcpPacket": "tcp",
    "ModbusTcpRequest": "tcp",
    "ModbusTcpResponse": "tcp",
    "CRC_FMT": "rtu",
    "CRC_SIZE": "rtu",
    "calc_crc16": "rtu",
    "validate_crc": "rtu",
    "ModbusRtuRequest": "rtu",
    "ModbusRtuResponse": "rtu",
    "ModbusRtuPacket": "rtu",
}

__all__ = [
    "CRC_FMT",
    "CRC_SIZE",
    "ModbusHeader",
    "ModbusRtuPacket",
    "ModbusRtuRequest",
    "ModbusRtuResponse",
    "ModbusTcpPacket",
    "ModbusTcpRequest",
    "ModbusTcpResponse",
    "calc_crc16",
    "validate_crc",
    "validate_mbap_length",
]


def __getattr__(name: str) -> object:
    """Bind a moved name on the first access that names it.

    Args:
        name (str) : The attribute being read from this module

    Returns:
        object : The class or function the name refers to

    Raises:
        AttributeError : The name is not one this module used to define
    """
    submodule = _MOVED.get(name)

    if submodule is None:
        raise AttributeError(name)

    warnings.warn(
        f"pyomb.packets.framing.{name} is renamed to pyomb.adu.{submodule}.{name} and is removed in 0.9.0",
        DeprecationWarning,
        stacklevel=2,
    )

    return getattr(import_module(f"pyomb.adu.{submodule}"), name)
