"""Deprecated: import from pyomb.transport instead.

pyomb.stream moved to pyomb.transport.stream. Every name below still
resolves to the exact class its new module defines, bound on first
access rather than imported eagerly, and each access warns naming the
new path. Removed in 0.9.0.
"""

import warnings
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

__all__ = [
    "ModbusFragmenter",
    "ModbusFragmenterAbc",
    "ModbusReceiverAbc",
    "ModbusSenderAbc",
    "ModbusStreamAbc",
    "ModbusTcpReceiver",
    "ModbusTcpSender",
    "ModbusTcpStream",
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
    if name not in __all__:
        raise AttributeError(name)

    warnings.warn(
        f"pyomb.stream.{name} is renamed to pyomb.transport.stream.{name} and is removed in 0.9.0",
        DeprecationWarning,
        stacklevel=2,
    )

    return getattr(import_module("pyomb.transport.stream"), name)
