"""The payload takes finished bytes, and the format-string route is retired.

There were two ways to build a frame the library models no class for, and
they produced the same bytes. The documented one passed a format string to
`pack()`; the undocumented one put the finished bytes in `data`. The
documented route was the weaker of the two, in a library whose purpose is
putting arbitrary bytes on the wire: a format string describes only layouts
`struct` knows how to write, where bytes carry any sequence at all.

Bytes are now the supported route. `pack` and `unpack` still exist, warn,
and delegate to the internal helpers the packet classes use among
themselves; they go in 0.6.0.

The tests below pin that the two routes agree on the wire, that a packet
built from bytes survives a round trip, and that the retired route still
works while it warns.
"""

import struct
import unittest
import warnings

from pyomb.packets import ModbusPdu

# A layout mixing 16-bit and 8-bit fields. The format string route could
# describe this one; the point of the pair below is that bytes describe it
# too, and go on describing layouts struct has no code for.
MIXED_WIDTH = struct.pack(">HBHB", 1, 2, 3, 4)

EXPECTED_FRAME = b"\x01\x00\x01\x02\x00\x03\x04"


class BytesAreTheSupportedRoute(unittest.TestCase):
    """A payload given as bytes reaches the wire unchanged."""

    def test_bytes_produce_the_frame_the_format_string_produced(self):
        pdu = ModbusPdu(fc=1, data=MIXED_WIDTH)

        self.assertEqual(pdu.serialize(), EXPECTED_FRAME)

    def test_the_two_routes_agree_on_the_wire(self):
        # The retired route is the reference here, which is the one case
        # where asserting this library against itself is the right test:
        # the claim is that the replacement is byte-compatible, not that
        # either is correct. The frame itself is pinned above.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            legacy = ModbusPdu(fc=1, data=(1, 2, 3, 4)).pack(">BHBHB")

        self.assertEqual(ModbusPdu(fc=1, data=MIXED_WIDTH).serialize(), legacy)

    def test_a_bytearray_is_accepted_too(self):
        pdu = ModbusPdu(fc=1, data=bytearray(MIXED_WIDTH))

        self.assertEqual(pdu.serialize(), EXPECTED_FRAME)

    def test_a_packet_built_from_bytes_survives_a_round_trip(self):
        built = ModbusPdu(fc=1, data=MIXED_WIDTH)

        read_back = ModbusPdu.deserialize(built.serialize())

        # Equality was the half that did not hold: both packets carried the
        # same frame while one held bytes and the other a tuple.
        self.assertEqual(built, read_back)
        self.assertEqual(built.serialize(), read_back.serialize())

    def test_bytes_are_held_as_their_byte_values(self):
        pdu = ModbusPdu(fc=1, data=b"\x12\x34")

        self.assertEqual(pdu.data, (0x12, 0x34))


class TheFormatStringRouteIsDeprecated(unittest.TestCase):
    """It still works, and it says it is going."""

    def test_pack_warns_and_still_packs(self):
        pdu = ModbusPdu(fc=1, data=(1, 2, 3, 4))

        with self.assertWarns(DeprecationWarning) as caught:
            packed = pdu.pack(">BHBHB")

        self.assertEqual(packed, EXPECTED_FRAME)
        self.assertIn("0.6.0", str(caught.warning))

    def test_unpack_warns_and_still_unpacks(self):
        with self.assertWarns(DeprecationWarning) as caught:
            pdu = ModbusPdu.unpack(EXPECTED_FRAME, ">BHBHB")

        self.assertEqual(pdu.fc, 1)
        self.assertEqual(pdu.data, (1, 2, 3, 4))
        self.assertIn("0.6.0", str(caught.warning))

    def test_the_packet_classes_do_not_use_the_deprecated_route(self):
        # The classes call the internal helpers, so an ordinary serialize
        # must not warn. Without this, every packet the library builds would
        # emit a deprecation warning naming a route its caller never took.
        from pyomb.packets import ModbusRequestFC3

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ModbusRequestFC3(start_addr=0, quantity=10).serialize()

        self.assertEqual([w for w in caught if w.category is DeprecationWarning], [])


if __name__ == "__main__":
    unittest.main()
