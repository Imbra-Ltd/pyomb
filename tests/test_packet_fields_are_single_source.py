"""A packet holds each value once, so a changed field reaches the wire.

Every concrete PDU class used to store its values twice: as the named
attributes a caller reads and writes, and as a combined `data` tuple built
once in `__init__`. Only `data` was packed, so writing `quantity` updated the
copy nobody serialized. The frame that went out was not the frame the caller
asked for, and nothing raised.

The classes now declare their fields in `PDU_FIELDS`, and `data` is derived
from those fields on every read. The tests below pin the three behaviours
that follow: a changed field changes the bytes, two packets sending the same
bytes compare equal, and the derived view refuses to be assigned.

Wire output is asserted against the frames in the specification-backed
per-function-code suites, which this module does not duplicate. What it adds
is the mutation path none of them exercised.
"""

import unittest

from pyomb.errors import ModbusPacketError
from pyomb.packets import (
    ModbusPdu,
    ModbusRequestFC3,
    ModbusRequestFC7,
    ModbusRequestFC15,
    ModbusResponseFC3,
)


class ChangedFieldReachesTheWire(unittest.TestCase):
    """A value written after construction is the value serialized."""

    def test_a_changed_scalar_changes_the_bytes(self):
        request = ModbusRequestFC3(start_addr=0, quantity=10)

        # 0x07D1 is one past the specification's cap for this function code.
        # The value is deliberately one a device rejects, so a frame carrying
        # the stale 10 cannot be mistaken for the intended one.
        request.quantity = 0x07D1

        self.assertEqual(request.serialize().hex(), "03000007d1")

    def test_a_changed_sequence_changes_the_bytes(self):
        response = ModbusResponseFC3(byte_count=4, values=[1, 2])

        response.values = (3, 4)

        self.assertEqual(response.serialize().hex(), "030400030004")

    def test_a_changed_field_in_a_mixed_layout_changes_the_bytes(self):
        # FC15 carries three scalars ahead of its sequence, so it pins that
        # the derived order is the wire order rather than fields then tail.
        request = ModbusRequestFC15(
            start_addr=0,
            quantity=8,
            byte_count=1,
            values=[0xFF],
        )

        request.start_addr = 1

        self.assertEqual(request.serialize().hex(), "0f0001000801ff")


class PacketsSendingTheSameBytesAreEqual(unittest.TestCase):
    """Equality follows the values, not the order they were written in."""

    def test_a_mutated_packet_equals_one_built_with_the_new_value(self):
        mutated = ModbusRequestFC3(start_addr=0, quantity=10)
        mutated.quantity = 0x07D1

        built = ModbusRequestFC3(start_addr=0, quantity=0x07D1)

        self.assertEqual(mutated, built)
        self.assertEqual(mutated.serialize(), built.serialize())

    def test_a_list_and_a_tuple_of_the_same_values_are_one_packet(self):
        from_list = ModbusResponseFC3(byte_count=4, values=[1, 2])
        from_tuple = ModbusResponseFC3(byte_count=4, values=(1, 2))

        self.assertEqual(from_list, from_tuple)

    def test_two_packets_differing_in_one_field_are_unequal(self):
        # The guard on the assertion above: equality has to still discriminate.
        self.assertNotEqual(
            ModbusRequestFC3(start_addr=0, quantity=10),
            ModbusRequestFC3(start_addr=0, quantity=11),
        )


class TheDerivedViewIsNotWritable(unittest.TestCase):
    """Assigning the derived payload is refused, and the message says why."""

    def test_assigning_data_on_a_deriving_class_raises(self):
        request = ModbusRequestFC3(start_addr=0, quantity=10)

        with self.assertRaises(ModbusPacketError) as caught:
            request.data = (1, 2)

        # The message has to name the fields to set instead, or a caller who
        # hits this has been told only that their assignment failed.
        self.assertIn("start_addr", str(caught.exception))
        self.assertIn("quantity", str(caught.exception))

    def test_a_class_carrying_no_fields_says_so(self):
        request = ModbusRequestFC7()

        with self.assertRaises(ModbusPacketError) as caught:
            request.data = 1

        self.assertIn("carries none", str(caught.exception))

    def test_a_class_carrying_no_fields_derives_an_empty_payload(self):
        self.assertEqual(ModbusRequestFC7().data, ())

    def test_the_generic_pdu_still_stores_what_it_is_given(self):
        # The generic PDU models no function code, so it has no named fields
        # to derive from and keeps the stored payload the fix removed
        # everywhere else.
        pdu = ModbusPdu(fc=1, data=(1, 2))

        self.assertEqual(pdu.data, (1, 2))

        pdu.data = (3, 4)

        self.assertEqual(pdu.data, (3, 4))
        self.assertEqual(pdu.serialize().hex(), "010304")


if __name__ == "__main__":
    unittest.main()
