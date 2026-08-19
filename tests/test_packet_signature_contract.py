"""One signature per packet operation, across the whole hierarchy.

Every packet class implemented serialize and deserialize with a signature of
its own choosing. The abstract base declared both as instance methods taking
**kwargs, ModbusPdu redeclared them with a format parameter, and each concrete
PDU dropped whatever it did not use -- so a caller holding a ModbusPacketAbc
could not call either operation without knowing the concrete class it really
had. The type checker reported 122 of these in packets.py alone.

The uniform contract is serialize(self) and a classmethod deserialize(stream).
Where a PDU shape genuinely needs a caller-supplied format, ModbusPdu.pack and
ModbusPdu.unpack carry it under their own names; see ADR-009. A subclass may
still add optional keyword parameters to deserialize -- the RTU packets take a
CRC verification toggle -- because appending an optional parameter keeps every
call the supertype accepts working.
"""

import inspect
import unittest

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


def caller_parameters(cls, name):
    """The parameters a caller supplies, with the implicit self or cls dropped.

    Args:
        cls (type)  : The class declaring the method
        name (str)  : The method name to inspect

    Returns:
        list : The inspect.Parameter objects a caller supplies
    """

    # getattr_static reads the class dictionary without triggering the
    # descriptor, which is what leaves a classmethod distinguishable from an
    # instance method here
    declared = inspect.getattr_static(cls, name)
    function = declared.__func__ if isinstance(declared, classmethod) else declared

    return list(inspect.signature(function).parameters.values())[1:]


class PacketSignatureContract(unittest.TestCase):
    """Pins the signature every packet operation is called through."""

    def setUp(self):
        self.classes = packet_classes()

    def test_the_hierarchy_is_not_empty(self):
        """A silent collection failure would pass every other test here."""

        self.assertIn(ModbusPacketAbc, self.classes)
        self.assertGreater(len(self.classes), 30)

    def test_serialize_is_an_instance_method_taking_nothing(self):
        """A packet knows its own layout, so a caller has nothing to add."""

        for cls in self.classes:
            with self.subTest(packet=cls.__name__):
                declared = inspect.getattr_static(cls, "serialize")
                self.assertNotIsInstance(declared, (classmethod, staticmethod))

                supplied = [p.name for p in caller_parameters(cls, "serialize")]
                message = f"{cls.__name__}.serialize takes {supplied}; a per-call format belongs to pack()"
                self.assertEqual(supplied, [], message)

    def test_deserialize_is_a_classmethod_taking_a_stream(self):
        """Deserializing builds an instance, so it cannot need one first."""

        for cls in self.classes:
            with self.subTest(packet=cls.__name__):
                declared = inspect.getattr_static(cls, "deserialize")
                self.assertIsInstance(declared, classmethod, f"{cls.__name__}.deserialize is not a classmethod")

                supplied = caller_parameters(cls, "deserialize")
                self.assertEqual(supplied[0].name, "stream")
                self.assertIs(supplied[0].default, inspect.Parameter.empty)

    def test_a_subclass_only_ever_appends_an_optional_parameter(self):
        """Anything else narrows what a supertype's caller may already do."""

        for cls in self.classes:
            for name in ("serialize", "deserialize"):
                with self.subTest(packet=cls.__name__, operation=name):
                    for parameter in caller_parameters(cls, name)[1:]:
                        self.assertIsNot(
                            parameter.default,
                            inspect.Parameter.empty,
                            f"{cls.__name__}.{name} requires {parameter.name}, which a supertype's callers never pass",
                        )

    def test_no_operation_absorbs_arbitrary_arguments(self):
        """The **kwargs on the base is what let every subclass diverge."""

        variadic = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)

        for cls in self.classes:
            for name in ("serialize", "deserialize"):
                with self.subTest(packet=cls.__name__, operation=name):
                    for parameter in caller_parameters(cls, name):
                        self.assertNotIn(
                            parameter.kind,
                            variadic,
                            f"{cls.__name__}.{name} declares {parameter.name}, which no subclass has to honour",
                        )


if __name__ == "__main__":
    unittest.main()
