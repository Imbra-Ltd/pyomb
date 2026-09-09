"""Enumerates the packet classes, so a contract test cannot miss one.

A test that lists the classes it covers stops covering the class added after
it was written, and the omission looks exactly like a passing suite. Every
hierarchy-wide contract in this suite collects its subjects from the module
instead, through the functions below.
"""

import inspect

from pyomb import pdu
from pyomb.packets import framing
from pyomb.pdu import ModbusPacketAbc

# Every module a packet class can currently be defined in, read from the
# canonical location rather than through the deprecated pyomb.packets.
_HOMES = (pdu, framing)


def packet_classes():
    """Every packet class this library declares, the abstract base included.

    Returns:
        list : The packet classes defined under any home in _HOMES
    """

    found = []

    for home in _HOMES:
        for name in dir(home):
            candidate = getattr(home, name)

            # Match the home's own prefix, not the home itself: the classes
            # live in its submodules and report those as their module.
            own = inspect.isclass(candidate) and candidate.__module__.startswith(home.__name__)
            if not own:
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
