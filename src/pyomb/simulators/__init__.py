"""The client and server simulators.

Built on pdu, adu and transport; nothing depends on either simulator.
Bound lazily, so a caller who never asks for a simulator does not pay
for the socket and ssl imports either one pulls in.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyomb.simulators.client_simulator import ModbusClientSimulator, RequestFactory, run_client
    from pyomb.simulators.server_simulator import ModbusServerSimulator, ResponseFactory, run_server

_DEFERRED = {
    "ModbusClientSimulator": "client_simulator",
    "RequestFactory": "client_simulator",
    "run_client": "client_simulator",
    "ModbusServerSimulator": "server_simulator",
    "ResponseFactory": "server_simulator",
    "run_server": "server_simulator",
}

__all__ = [
    "ModbusClientSimulator",
    "ModbusServerSimulator",
    "RequestFactory",
    "ResponseFactory",
    "run_client",
    "run_server",
]


def __getattr__(name: str) -> object:
    """Bind a deferred name on the first access that names it.

    Args:
        name (str) : The attribute being read from this module

    Returns:
        object : The class or function the name refers to

    Raises:
        AttributeError : The name is not one this module exports
    """
    submodule = _DEFERRED.get(name)

    if submodule is None:
        raise AttributeError(name)

    return getattr(import_module("." + submodule, __name__), name)
