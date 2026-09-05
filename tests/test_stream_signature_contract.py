"""One signature per stream operation, across each of the four hierarchies.

`ModbusSenderAbc` declared `run_once` with a `burst` parameter its only
implementation does not take. Burst is a property of the sender rather than of
one run -- it sets TCP_NODELAY on the socket the sender owns -- and
`ModbusTcpSender` carries it as state, set through the constructor or
`set_burst_mode`. So the abstract operation promised a per-call choice nothing
honours, and a caller holding a `ModbusSenderAbc` had no implementation that
would accept it. mypy reported it as the last `override` finding in the tree.

`ModbusStreamAbc.send` carried the milder form of the same defect: it named its
parameter `packet` where its own subtype named it `message`, so the keyword the
supertype promised was one the subtype refused.

ADR-009 settled this shape in the packet hierarchy. This module is that test
for the stream hierarchies, and it is what keeps the `override` code out of the
mypy freeze in `pyproject.toml` now that the freeze no longer carries it.
"""

import inspect
import unittest

from pyomb import stream
from tests.helpers.signatures import caller_parameters

VARIADIC = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def declared_classes():
    """Every class stream.py declares, imports excluded.

    Returns:
        list : The classes defined in pyomb.stream
    """

    found = []

    for name in dir(stream):
        candidate = getattr(stream, name)

        # A class imported into the module is somebody else's contract
        if inspect.isclass(candidate) and candidate.__module__ == stream.__name__:
            found.append(candidate)

    return found


def abstract_bases():
    """The stream abstract bases, each paired with the operations it declares.

    Returns:
        list : Tuples of (class, sorted operation names)
    """

    bases = [cls for cls in declared_classes() if getattr(cls, "__abstractmethods__", ())]

    return [(cls, sorted(cls.__abstractmethods__)) for cls in bases]


def implementations(base):
    """The instantiable subclasses of one abstract base.

    Args:
        base (type) : The abstract base to search for

    Returns:
        list : The classes implementing every operation base declares
    """

    return [
        cls
        for cls in declared_classes()
        if cls is not base and issubclass(cls, base) and not getattr(cls, "__abstractmethods__", ())
    ]


class StreamSignatureContract(unittest.TestCase):
    """Pins the signature every stream operation is called through."""

    def setUp(self):
        self.bases = abstract_bases()

    def test_the_hierarchies_are_all_present(self):
        """A silent collection failure would pass every other test here."""

        found = sorted(base.__name__ for base, _ in self.bases)

        self.assertEqual(
            found,
            ["ModbusFragmenterAbc", "ModbusReceiverAbc", "ModbusSenderAbc", "ModbusStreamAbc"],
        )

    def test_every_abstract_base_has_an_implementation(self):
        """An unimplemented base makes the comparison below vacuous."""

        for base, _ in self.bases:
            with self.subTest(base=base.__name__):
                self.assertTrue(implementations(base), f"{base.__name__} has no implementation to compare against")

    def test_an_implementation_accepts_exactly_what_its_base_promises(self):
        """Parameter names included: a caller may pass any of them by keyword."""

        for base, operations in self.bases:
            for implementation in implementations(base):
                for operation in operations:
                    with self.subTest(base=base.__name__, implementation=implementation.__name__, operation=operation):
                        promised = [str(p) for p in caller_parameters(base, operation)]
                        accepted = [str(p) for p in caller_parameters(implementation, operation)]

                        message = (
                            f"{base.__name__}.{operation} promises {promised}, "
                            f"{implementation.__name__}.{operation} accepts {accepted}"
                        )
                        self.assertEqual(promised, accepted, message)

    def test_no_stream_operation_absorbs_arbitrary_arguments(self):
        """A variadic accepts every call and so constrains no subclass."""

        for base, operations in self.bases:
            for cls in [base, *implementations(base)]:
                for operation in operations:
                    with self.subTest(cls=cls.__name__, operation=operation):
                        for parameter in caller_parameters(cls, operation):
                            self.assertNotIn(
                                parameter.kind,
                                VARIADIC,
                                f"{cls.__name__}.{operation} declares {parameter.name}, "
                                "which no subclass has to honour",
                            )

    def test_run_once_takes_nothing_in_either_direction(self):
        """The settled signature, named so a reader sees it without inference."""

        for cls in (stream.ModbusSenderAbc, stream.ModbusTcpSender, stream.ModbusReceiverAbc, stream.ModbusTcpReceiver):
            with self.subTest(cls=cls.__name__):
                self.assertEqual(caller_parameters(cls, "run_once"), [])


if __name__ == "__main__":
    unittest.main()
