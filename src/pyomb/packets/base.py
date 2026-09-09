"""Deprecated: import from pyomb.pdu.common instead.

pyomb.packets.base moved to pyomb.pdu.common. Every name below still
resolves to the exact class the new module defines, bound on first access
rather than imported eagerly. Removed in 0.9.0.
"""

import warnings
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyomb.pdu.common import ModbusPacketAbc, ModbusPduParserAbc, ModbusViolation

__all__ = ["ModbusPacketAbc", "ModbusPduParserAbc", "ModbusViolation"]


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
        f"pyomb.packets.base.{name} is renamed to pyomb.pdu.common.{name} and is removed in 0.9.0",
        DeprecationWarning,
        stacklevel=2,
    )

    return getattr(import_module("pyomb.pdu.common"), name)
