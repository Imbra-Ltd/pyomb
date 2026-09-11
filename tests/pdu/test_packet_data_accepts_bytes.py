"""The payload takes finished bytes; the retired format-string route is gone.

There were two ways to build a frame the library models no class for, and they
produced the same bytes: a format string passed to `pack()`, or the finished
bytes in `data`. The documented route was the weaker of the two in a library
whose purpose is putting arbitrary bytes on the wire, since a format string
describes only the layouts `struct` knows how to write.

Bytes are the only supported route now; `pack` and `unpack` no longer exist,
per ADR-036. The tests below pin that a packet built from bytes survives a
round trip and that the retired route is actually gone.
"""

import struct
import unittest

from pyomb.pdu import ModbusPdu

# A layout mixing 16-bit and 8-bit fields, which the format string could
# describe. Bytes describe it too, and go on past what struct has code for.
MIXED_WIDTH = struct.pack(">HBHB", 1, 2, 3, 4)

EXPECTED_FRAME = b"\x01\x00\x01\x02\x00\x03\x04"


class BytesAreTheSupportedRoute(unittest.TestCase):
    """A payload given as bytes reaches the wire unchanged."""

    def test_bytes_produce_the_frame_the_format_string_produced(self):
        pdu = ModbusPdu(fc=1, data=MIXED_WIDTH)

        self.assertEqual(pdu.serialize(), EXPECTED_FRAME)

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


class TheFormatStringRouteIsGone(unittest.TestCase):
    """ADR-036 promised removal at 0.6.0; neither name resolves any more."""

    def test_pack_no_longer_resolves(self):
        pdu = ModbusPdu(fc=1, data=(1, 2, 3, 4))

        with self.assertRaises(AttributeError):
            pdu.pack(">BHBHB")

    def test_unpack_no_longer_resolves(self):
        with self.assertRaises(AttributeError):
            ModbusPdu.unpack(EXPECTED_FRAME, ">BHBHB")


if __name__ == "__main__":
    unittest.main()
