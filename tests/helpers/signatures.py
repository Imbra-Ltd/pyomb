"""Reads the parameters a caller supplies, whatever kind of method declares it.

A contract test compares what a supertype promises a caller against what a
subtype accepts, so it needs the declared parameters minus whatever the
descriptor supplies implicitly. That differs by kind: an instance method binds
self, a classmethod binds cls, and a staticmethod binds nothing. The stream
fragmenter implements both of its abstract operations as staticmethods, so
dropping the first parameter unconditionally would read its message parameter
as the implicit one and report a mismatch that is not there.
"""

import inspect


def caller_parameters(cls, name):
    """The parameters a caller supplies, with any implicit first one dropped.

    Args:
        cls (type)  : The class declaring the method
        name (str)  : The method name to inspect

    Returns:
        list : The inspect.Parameter objects a caller supplies
    """

    # getattr_static reads the class dictionary without triggering the
    # descriptor, which is what leaves the three kinds distinguishable here
    declared = inspect.getattr_static(cls, name)

    if isinstance(declared, staticmethod):
        return list(inspect.signature(declared.__func__).parameters.values())

    function = declared.__func__ if isinstance(declared, classmethod) else declared

    return list(inspect.signature(function).parameters.values())[1:]
