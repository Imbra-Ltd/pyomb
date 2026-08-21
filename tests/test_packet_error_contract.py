"""Every packet operation reports failure as ModbusPacketError.

A codec's callers sit behind a socket, so malformed input is the ordinary case
rather than the exceptional one. The library answers that with a try/except
around each serialize and deserialize that re-raises as ModbusPacketError, and
a caller guarding a decode catches that one type. Nothing pinned it: the
handlers were written per class, forty-odd times, and a class whose handler
was missing or mis-scoped would let a raw struct.error out through an except
clause the caller never wrote.

The hierarchy-wide tests collect their subjects from the module rather than
listing them, so a packet class added later is covered the day it lands. Where
a class holds a failure mode the collected input cannot reach, it gets a named
case of its own -- ModbusPdu builds its format from a length, and a caller
following the documented signature never supplies a shape that cannot be
measured.
"""

import inspect
import unittest

from packet_hierarchy import concrete_packet_classes, packet_classes

from pyomb.errors import ModbusPacketError
from pyomb.packets import ModbusPdu, ModbusPduParser, ModbusPduParserAbc

# A one-element tuple holding a value no Modbus field can hold. The tuple is
# not an integer and its element exceeds every unsigned format the
# specification uses, so struct refuses it whether the field it lands on is a
# scalar or a sequence -- which is what lets one value corrupt every packet in
# the hierarchy without a per-class table of field types.
UNREPRESENTABLE = (2**64,)


def unrepresentable_packet(cls):
    """Build a packet of cls whose every field holds a value the wire refuses.

    Args:
        cls (type) : The packet class to instantiate

    Returns:
        ModbusPacketAbc : The packet, ready to fail serialization
    """

    parameters = list(inspect.signature(cls.__init__).parameters.values())[1:]
    packet = cls(**{parameter.name: UNREPRESENTABLE for parameter in parameters})

    # The fields are overwritten after construction as well as supplied to it,
    # because a packet that fixes its own function code takes no constructor
    # parameter carrying it -- FC7 requests are the case
    for field in vars(packet):
        setattr(packet, field, UNREPRESENTABLE)

    return packet


class MalformedStreamIsRejected(unittest.TestCase):
    """Pins what a packet class does with bytes it cannot decode."""

    def setUp(self):
        self.classes = concrete_packet_classes()

    def test_the_hierarchy_is_not_empty(self):
        """A silent collection failure would pass every other test here."""

        self.assertGreater(len(self.classes), 30)
        self.assertEqual(len(self.classes), len(packet_classes()) - 1)

    def test_deserialize_rejects_an_empty_stream(self):
        """Nothing decodes from no bytes, and a peer can send exactly that."""

        for cls in self.classes:
            with self.subTest(packet=cls.__name__), self.assertRaises(ModbusPacketError):
                cls.deserialize(b"")

    def test_serialize_rejects_a_field_the_wire_cannot_carry(self):
        """An out-of-range field is a caller's error, reported in the library's type."""

        for cls in self.classes:
            with self.subTest(packet=cls.__name__):
                packet = unrepresentable_packet(cls)

                with self.assertRaises(ModbusPacketError):
                    packet.serialize()


class TheGenericPduMeasuresInsideItsGuard(unittest.TestCase):
    """ModbusPdu builds its format from a length, and taking one can fail.

    The hierarchy-wide tests above cannot reach this: they supply `data` as the
    sequence the constructor documents, which is what a caller following the
    signature does. These two pass the shape that does not carry a length.
    """

    def test_serialize_reports_a_data_field_that_carries_no_length(self):
        with self.assertRaises(ModbusPacketError):
            ModbusPdu(fc=1, data=5).serialize()

    def test_deserialize_reports_a_stream_that_carries_no_length(self):
        with self.assertRaises(ModbusPacketError):
            ModbusPdu.deserialize(None)

    def test_the_ordinary_round_trip_is_untouched(self):
        """The guard sits around the measurement, not around the packing."""

        pdu = ModbusPdu(fc=1, data=(1, 2, 3))

        self.assertEqual(ModbusPdu.deserialize(pdu.serialize()), pdu)


class SkippingCrcVerificationKeepsTheErrorHandling(unittest.TestCase):
    """The RTU packets let a caller accept a corrupt frame. Undecodable is not corrupt."""

    def setUp(self):
        self.classes = [cls for cls in concrete_packet_classes() if self.takes_a_crc_toggle(cls)]

    @staticmethod
    def takes_a_crc_toggle(cls):
        return "verify_crc" in inspect.signature(inspect.getattr_static(cls, "deserialize").__func__).parameters

    def test_the_toggle_exists_on_the_rtu_packets(self):
        """The list is collected, so an empty one would pass the test below silently."""

        self.assertEqual(sorted(cls.__name__ for cls in self.classes), ["ModbusRtuRequest", "ModbusRtuResponse"])

    def test_an_unverified_frame_that_cannot_be_decoded_is_still_refused(self):
        """Without the toggle the checksum check rejects first, so this path needs it off."""

        for cls in self.classes:
            with self.subTest(packet=cls.__name__), self.assertRaises(ModbusPacketError):
                cls.deserialize(b"", verify_crc=False)


class ParserRejectsWhatItCannotParse(unittest.TestCase):
    """Pins the parser's own guards, which sit outside the packet classes."""

    def test_parse_request_rejects_a_stream_without_a_function_code(self):
        with self.assertRaises(ModbusPacketError):
            ModbusPduParser.parse_request(b"")

    def test_parse_response_rejects_a_stream_without_a_function_code(self):
        with self.assertRaises(ModbusPacketError):
            ModbusPduParser.parse_response(b"")

    def test_registering_a_class_outside_the_pdu_hierarchy_is_refused(self):
        """The registry maps a function code to a decoder, so the value has to be one."""

        with self.assertRaises(ModbusPacketError):
            ModbusPduParser.register(str)

    def test_unregistering_a_class_outside_the_pdu_hierarchy_is_refused(self):
        with self.assertRaises(ModbusPacketError):
            ModbusPduParser.unregister(str)

    def test_a_registered_class_survives_the_guard(self):
        """The guard has to admit the hierarchy it exists to protect."""

        registry = dict(ModbusPduParser.get_registry())

        try:
            ModbusPduParser.register(ModbusPdu)
            self.assertIs(ModbusPduParser.get_registry()[ModbusPdu.PDU_ID], ModbusPdu)
        finally:
            ModbusPduParser.set_registry(registry)


class PacketsRejectAParserThatIsNotOne(unittest.TestCase):
    """Pins set_parser on each packet that carries a parser of its own."""

    def setUp(self):
        self.classes = [cls for cls in concrete_packet_classes() if hasattr(cls, "set_parser")]

    def test_every_packet_with_a_parser_slot_guards_it(self):
        self.assertGreater(len(self.classes), 0)

        for cls in self.classes:
            with self.subTest(packet=cls.__name__):
                original = cls.get_parser()

                try:
                    with self.assertRaises(ModbusPacketError):
                        cls.set_parser(str)
                finally:
                    cls.set_parser(original)

    def test_the_guard_admits_a_real_parser(self):
        for cls in self.classes:
            with self.subTest(packet=cls.__name__):
                original = cls.get_parser()

                try:
                    self.assertTrue(issubclass(original, ModbusPduParserAbc))
                    cls.set_parser(ModbusPduParser)
                    self.assertIs(cls.get_parser(), ModbusPduParser)
                finally:
                    cls.set_parser(original)


if __name__ == "__main__":
    unittest.main()
