"""A receive has to return one whole frame, however the bytes arrive.

TCP carries a byte stream, so a read produces whatever has arrived: part of an
ADU, exactly one, or several concatenated. The unfragmented path used to
perform a single recv and return its result, which is a complete frame only
when the network happens to deliver one. On a local link it almost always
does, which is why this survived; across a router or a VPN it does not, and
the caller was handed a fragment. These tests deliver frames in slices and
hold the method to the MBAP length field instead of to the segment boundary.
"""

import unittest

from pyomb.errors import ModbusNetworkError, ModbusPacketError
from pyomb.stream import ModbusTcpStream

# Trans-ID 1, Prot-ID 0, Length 6, Unit-ID 0x11, PDU 03 00 00 00 02.
FRAME = bytes.fromhex("000100000006110300000002")

# Trans-ID 2, same shape, used to prove a receive stops at its own frame.
NEXT_FRAME = bytes.fromhex("000200000006110300000004")


class SegmentedSocket(object):
    """Hands out at most `segment` bytes per read, as a slow path would."""

    def __init__(self, data, segment=5):
        self.data = data
        self.segment = segment

    def recv(self, buffer_size):
        take = min(buffer_size, self.segment)
        chunk = self.data[:take]
        self.data = self.data[take:]
        return chunk


def stream_over(data, segment=5, frag_size=0):
    return ModbusTcpStream(sock=SegmentedSocket(data, segment), frag_size=frag_size)


class TestSegmentedDelivery(unittest.TestCase):
    def test_frame_split_across_reads_is_reassembled(self):
        # Previously returned the first 5 bytes and called it a message.
        self.assertEqual(stream_over(FRAME, segment=5).receive(), FRAME)

    def test_every_segment_size_reassembles(self):
        for segment in range(1, len(FRAME) + 2):
            self.assertEqual(
                stream_over(FRAME, segment=segment).receive(), FRAME, "mismatch at segment={0}".format(segment)
            )

    def test_every_fragment_size_reassembles(self):
        for frag_size in (0, 1, 3, 7, 100):
            self.assertEqual(
                stream_over(FRAME, segment=2, frag_size=frag_size).receive(),
                FRAME,
                "mismatch at frag_size={0}".format(frag_size),
            )

    def test_two_frames_in_one_segment_are_returned_one_at_a_time(self):
        # The old single-read path returned both at once, and the codec then
        # rejected the pair on the length field.
        stream = stream_over(FRAME + NEXT_FRAME, segment=64)

        self.assertEqual(stream.receive(), FRAME)
        self.assertEqual(stream.receive(), NEXT_FRAME)

    def test_close_between_frames_reports_no_message(self):
        stream = stream_over(FRAME, segment=64)
        stream.receive()

        self.assertEqual(stream.receive(), b"")

    def test_close_inside_the_header_raises(self):
        with self.assertRaises(ModbusNetworkError):
            stream_over(FRAME[:4]).receive()

    def test_close_inside_the_pdu_raises(self):
        # A truncated frame is a transport failure, not a short message.
        with self.assertRaises(ModbusNetworkError):
            stream_over(FRAME[:9]).receive()

    def test_length_field_below_the_unit_identifier_raises(self):
        undersized = bytes.fromhex("000100000000110300000002")

        with self.assertRaises(ModbusPacketError):
            stream_over(undersized, segment=64).receive()


if __name__ == "__main__":
    unittest.main()
