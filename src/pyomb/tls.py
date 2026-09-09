"""Deprecated: import from pyomb.transport instead.

pyomb.tls moved to pyomb.transport.tls. Every name below still resolves
to the exact class or value its new module defines, bound on first
access rather than imported eagerly, and each access warns naming the
new path. Removed in 0.9.0.
"""

import warnings
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyomb.transport.tls import UNSET, TlsRole, TlsSettings

__all__ = ["UNSET", "TlsRole", "TlsSettings"]


def __getattr__(name: str) -> object:
    """Bind a moved name on the first access that names it.

    Args:
        name (str) : The attribute being read from this module

    Returns:
        object : The class or value the name refers to

    Raises:
        AttributeError : The name is not one this module used to define
    """
    if name not in __all__:
        raise AttributeError(name)

    warnings.warn(
        f"pyomb.tls.{name} is renamed to pyomb.transport.tls.{name} and is removed in 0.9.0",
        DeprecationWarning,
        stacklevel=2,
    )

    return getattr(import_module("pyomb.transport.tls"), name)
