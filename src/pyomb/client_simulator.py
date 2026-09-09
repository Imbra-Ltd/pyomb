"""Deprecated: import from pyomb.simulators instead.

pyomb.client_simulator moved to pyomb.simulators.client_simulator. Every
name below still resolves to the exact class or function the new module
defines, bound on first access rather than imported eagerly. Removed in
0.9.0.
"""

import warnings
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyomb.simulators.client_simulator import ModbusClientSimulator, RequestFactory, run_client

__all__ = ["ModbusClientSimulator", "RequestFactory", "run_client"]


def __getattr__(name: str) -> object:
    """Bind a moved name on the first access that names it.

    Args:
        name (str) : The attribute being read from this module

    Returns:
        object : The class or function the name refers to

    Raises:
        AttributeError : The name is not one this module used to define
    """
    if name not in __all__:
        raise AttributeError(name)

    warnings.warn(
        f"pyomb.client_simulator.{name} is renamed to pyomb.simulators.client_simulator.{name} and is removed in 0.9.0",
        DeprecationWarning,
        stacklevel=2,
    )

    return getattr(import_module("pyomb.simulators.client_simulator"), name)
