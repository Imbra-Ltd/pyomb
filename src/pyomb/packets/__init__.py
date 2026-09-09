"""Deprecated: import from pyomb.pdu and pyomb.adu instead.

pyomb.packets split into pyomb.pdu (the message) and pyomb.adu (the
envelope a transport puts around it). Every name below still resolves to
the exact class its new module defines, bound on first access rather
than imported eagerly, and each access warns naming the module that now
holds it. Removed in 0.9.0.
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
    from pyomb.pdu import (
        ModbusError,
        ModbusPacketAbc,
        ModbusPdu,
        ModbusPduParser,
        ModbusPduParserAbc,
        ModbusRequestFC1,
        ModbusRequestFC2,
        ModbusRequestFC3,
        ModbusRequestFC4,
        ModbusRequestFC5,
        ModbusRequestFC6,
        ModbusRequestFC7,
        ModbusRequestFC8,
        ModbusRequestFC15,
        ModbusRequestFC16,
        ModbusRequestFC22,
        ModbusRequestFC23,
        ModbusRequestFC43,
        ModbusResponseFC1,
        ModbusResponseFC2,
        ModbusResponseFC3,
        ModbusResponseFC4,
        ModbusResponseFC5,
        ModbusResponseFC6,
        ModbusResponseFC7,
        ModbusResponseFC8,
        ModbusResponseFC15,
        ModbusResponseFC16,
        ModbusResponseFC22,
        ModbusResponseFC23,
        ModbusResponseFC43,
        ModbusViolation,
    )

# Each retired name against the package and submodule that now define it.
_MOVED = {
    "ModbusError": ("pdu", "common"),
    "ModbusPacketAbc": ("pdu", "common"),
    "ModbusPdu": ("pdu", "common"),
    "ModbusPduParser": ("pdu", "common"),
    "ModbusPduParserAbc": ("pdu", "common"),
    "ModbusViolation": ("pdu", "common"),
    "ModbusRequestFC1": ("pdu", "bits"),
    "ModbusResponseFC1": ("pdu", "bits"),
    "ModbusRequestFC2": ("pdu", "bits"),
    "ModbusResponseFC2": ("pdu", "bits"),
    "ModbusRequestFC5": ("pdu", "bits"),
    "ModbusResponseFC5": ("pdu", "bits"),
    "ModbusRequestFC15": ("pdu", "bits"),
    "ModbusResponseFC15": ("pdu", "bits"),
    "ModbusRequestFC3": ("pdu", "registers"),
    "ModbusResponseFC3": ("pdu", "registers"),
    "ModbusRequestFC4": ("pdu", "registers"),
    "ModbusResponseFC4": ("pdu", "registers"),
    "ModbusRequestFC6": ("pdu", "registers"),
    "ModbusResponseFC6": ("pdu", "registers"),
    "ModbusRequestFC16": ("pdu", "registers"),
    "ModbusResponseFC16": ("pdu", "registers"),
    "ModbusRequestFC22": ("pdu", "registers"),
    "ModbusResponseFC22": ("pdu", "registers"),
    "ModbusRequestFC23": ("pdu", "registers"),
    "ModbusResponseFC23": ("pdu", "registers"),
    "ModbusRequestFC7": ("pdu", "diagnostics"),
    "ModbusResponseFC7": ("pdu", "diagnostics"),
    "ModbusRequestFC8": ("pdu", "diagnostics"),
    "ModbusResponseFC8": ("pdu", "diagnostics"),
    "ModbusRequestFC43": ("pdu", "encapsulated"),
    "ModbusResponseFC43": ("pdu", "encapsulated"),
    "ModbusHeader": ("adu", "tcp"),
    "validate_mbap_length": ("adu", "tcp"),
    "ModbusTcpPacket": ("adu", "tcp"),
    "ModbusTcpRequest": ("adu", "tcp"),
    "ModbusTcpResponse": ("adu", "tcp"),
    "CRC_FMT": ("adu", "rtu"),
    "CRC_SIZE": ("adu", "rtu"),
    "calc_crc16": ("adu", "rtu"),
    "validate_crc": ("adu", "rtu"),
    "ModbusRtuRequest": ("adu", "rtu"),
    "ModbusRtuResponse": ("adu", "rtu"),
    "ModbusRtuPacket": ("adu", "rtu"),
}

__all__ = [
    "CRC_FMT",
    "CRC_SIZE",
    "ModbusError",
    "ModbusHeader",
    "ModbusPacketAbc",
    "ModbusPdu",
    "ModbusPduParser",
    "ModbusPduParserAbc",
    "ModbusRequestFC1",
    "ModbusRequestFC2",
    "ModbusRequestFC3",
    "ModbusRequestFC4",
    "ModbusRequestFC5",
    "ModbusRequestFC6",
    "ModbusRequestFC7",
    "ModbusRequestFC8",
    "ModbusRequestFC15",
    "ModbusRequestFC16",
    "ModbusRequestFC22",
    "ModbusRequestFC23",
    "ModbusRequestFC43",
    "ModbusResponseFC1",
    "ModbusResponseFC2",
    "ModbusResponseFC3",
    "ModbusResponseFC4",
    "ModbusResponseFC5",
    "ModbusResponseFC6",
    "ModbusResponseFC7",
    "ModbusResponseFC8",
    "ModbusResponseFC15",
    "ModbusResponseFC16",
    "ModbusResponseFC22",
    "ModbusResponseFC23",
    "ModbusResponseFC43",
    "ModbusRtuPacket",
    "ModbusRtuRequest",
    "ModbusRtuResponse",
    "ModbusTcpPacket",
    "ModbusTcpRequest",
    "ModbusTcpResponse",
    "ModbusViolation",
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
    moved = _MOVED.get(name)

    if moved is None:
        raise AttributeError(name)

    package, submodule = moved
    warnings.warn(
        f"pyomb.packets.{name} is renamed to pyomb.{package}.{submodule}.{name} and is removed in 0.9.0",
        DeprecationWarning,
        stacklevel=2,
    )

    return getattr(import_module(f"pyomb.{package}.{submodule}"), name)
