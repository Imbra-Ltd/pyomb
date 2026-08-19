"""Enumerates the packet classes, so a contract test cannot miss one.

A test that lists the classes it covers stops covering the class added after
it was written, and the omission looks exactly like a passing suite. Every
hierarchy-wide contract in this suite collects its subjects from the module
instead, through the functions below.
"""

import inspect

from pyomb import packets
from pyomb.packets import ModbusPacketAbc


def packet_classes():
    """Every packet class this library declares, the abstract base included.

    Returns:
        list : The packet classes defined in pyomb.packets
    """

    found = []

    for name in dir(packets):
        candidate = getattr(packets, name)

        # A class imported into the module is somebody else's contract
        if not inspect.isclass(candidate) or candidate.__module__ != packets.__name__:
            continue

        if issubclass(candidate, ModbusPacketAbc):
            found.append(candidate)

    return found


def concrete_packet_classes():
    """The packet classes a caller can instantiate and put on the wire.

    Returns:
        list : The packet classes with no abstract method left over
    """

    return [cls for cls in packet_classes() if not getattr(cls, "__abstractmethods__", ())]
