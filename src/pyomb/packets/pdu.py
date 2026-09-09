"""Deprecated: import from pyomb.pdu instead.

pyomb.packets.pdu split into pyomb.pdu's group modules -- common, bits,
registers, diagnostics, encapsulated. Every name below still resolves to
the exact class its new module defines, bound on first access rather than
imported eagerly, and each access warns naming the module that now holds
it. Removed in 0.9.0.
"""

import warnings
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyomb.pdu import (
        ModbusError,
        ModbusPdu,
        ModbusPduParser,
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
    )

# Each retired name against the submodule of pyomb.pdu that now defines it.
_MOVED = {
    "ModbusError": "common",
    "ModbusPdu": "common",
    "ModbusPduParser": "common",
    "ModbusRequestFC1": "bits",
    "ModbusResponseFC1": "bits",
    "ModbusRequestFC2": "bits",
    "ModbusResponseFC2": "bits",
    "ModbusRequestFC5": "bits",
    "ModbusResponseFC5": "bits",
    "ModbusRequestFC15": "bits",
    "ModbusResponseFC15": "bits",
    "ModbusRequestFC3": "registers",
    "ModbusResponseFC3": "registers",
    "ModbusRequestFC4": "registers",
    "ModbusResponseFC4": "registers",
    "ModbusRequestFC6": "registers",
    "ModbusResponseFC6": "registers",
    "ModbusRequestFC16": "registers",
    "ModbusResponseFC16": "registers",
    "ModbusRequestFC22": "registers",
    "ModbusResponseFC22": "registers",
    "ModbusRequestFC23": "registers",
    "ModbusResponseFC23": "registers",
    "ModbusRequestFC7": "diagnostics",
    "ModbusResponseFC7": "diagnostics",
    "ModbusRequestFC8": "diagnostics",
    "ModbusResponseFC8": "diagnostics",
    "ModbusRequestFC43": "encapsulated",
    "ModbusResponseFC43": "encapsulated",
}

__all__ = [
    "ModbusError",
    "ModbusPdu",
    "ModbusPduParser",
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
]


def __getattr__(name: str) -> object:
    """Bind a moved name on the first access that names it.

    Args:
        name (str) : The attribute being read from this module

    Returns:
        object : The class the name refers to

    Raises:
        AttributeError : The name is not one this module used to define
    """
    submodule = _MOVED.get(name)

    if submodule is None:
        raise AttributeError(name)

    warnings.warn(
        f"pyomb.packets.pdu.{name} is renamed to pyomb.pdu.{submodule}.{name} and is removed in 0.9.0",
        DeprecationWarning,
        stacklevel=2,
    )

    return getattr(import_module(f"pyomb.pdu.{submodule}"), name)
