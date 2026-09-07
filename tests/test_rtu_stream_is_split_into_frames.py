"""The splitter cuts whole RTU frames out of a stream of bytes.

An RTU frame declares no length, so the boundary comes from the content: the
PDU class states how long its frame is and the checksum at that boundary
either confirms the answer or rejects it. A rejected frame costs one byte,
which is discarded before the search resumes.

The frames below are published specification vectors, so the bytes are
anchored outside this library. The two Diagnostics frames and the unknown
function code are constructed, because no published example covers a frame the
layout cannot size.
"""

import unittest

from pyomb.packets import ModbusRtuSplitter, RtuSide

# 11 03 00 6B 00 03 -- read three holding registers from 0x006B on slave 17.
FC3_REQUEST = b"\x11\x03\x00\x6b\x00\x03\x76\x87"

# 11 03 06 AE 41 56 52 43 40 -- the three registers coming back. Eleven bytes
# where the request is eight, which is why the direction has to be known.
FC3_RESPONSE = b"\x11\x03\x06\xae\x41\x56\x52\x43\x40\x49\xad"

# 11 01 00 13 00 25 -- read 37 coils from 0x0013 on slave 17.
FC1_REQUEST = b"\x11\x01\x00\x13\x00\x25\x0e\x84"

# 11 01 03 CD 6B B2 -- three bytes of coil data. Eight bytes, exactly as long
# as the request above, so length alone separates neither.
FC1_RESPONSE = b"\x11\x01\x03\xcd\x6b\xb2\x00\x64"

# 01 83 02 -- slave 1 refuses an FC3 with ILLEGAL DATA ADDRESS.
EXCEPTION_RESPONSE = b"\x01\x83\x02\xc0\xf1"

# 11 08 00 01 FF 00 -- Diagnostics, Restart Communications Option. The
# sub-function is one the table states a width for.
FC8_RESTART = b"\x11\x08\x00\x01\xff\x00\xf2\xab"

# 11 08 00 00 A5 37 -- Diagnostics, Return Query Data. The data field is
# echoed at whatever length the client sent, so nothing sizes it.
FC8_ECHO = b"\x11\x08\x00\x00\xa5\x37\xd8\x1d"

# 11 47 DE AD -- a function code this library does not model, which falls back
# to the generic PDU and states no width either.
UNKNOWN_FUNCTION = b"\x11\x47\xde\xad\x2d\x10"


class TestOneFrameAtATime(unittest.TestCase):
    def test_a_whole_frame_arrives_as_one_packet(self):
        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)

        found = splitter.push(FC3_REQUEST)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].serialize(), FC3_REQUEST)
        self.assertEqual(splitter.pending, 0)
        self.assertEqual(splitter.resyncs, 0)

    def test_a_variable_length_frame_is_sized_from_its_count(self):
        splitter = ModbusRtuSplitter(side=RtuSide.RESPONSE)

        found = splitter.push(FC3_RESPONSE)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].serialize(), FC3_RESPONSE)

    def test_an_exception_response_is_framed(self):
        splitter = ModbusRtuSplitter(side=RtuSide.RESPONSE)

        found = splitter.push(EXCEPTION_RESPONSE)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].pdu.fc, 0x83)


class TestBytesArrivingInPieces(unittest.TestCase):
    def test_nothing_is_returned_until_the_frame_completes(self):
        splitter = ModbusRtuSplitter(side=RtuSide.RESPONSE)

        for index in range(1, len(FC3_RESPONSE)):
            splitter.reset()

            self.assertEqual(splitter.push(FC3_RESPONSE[:index]), [])
            self.assertEqual(splitter.pending, index)

    def test_one_byte_at_a_time_still_yields_the_frame(self):
        splitter = ModbusRtuSplitter(side=RtuSide.RESPONSE)
        found = []

        for byte in FC3_RESPONSE:
            found.extend(splitter.push(bytes([byte])))

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].serialize(), FC3_RESPONSE)
        self.assertEqual(splitter.resyncs, 0)

    def test_back_to_back_frames_come_back_in_order(self):
        splitter = ModbusRtuSplitter(side=RtuSide.RESPONSE)

        found = splitter.push(FC3_RESPONSE + EXCEPTION_RESPONSE + FC3_RESPONSE)

        self.assertEqual([packet.serialize() for packet in found], [FC3_RESPONSE, EXCEPTION_RESPONSE, FC3_RESPONSE])
        self.assertEqual(splitter.pending, 0)


class TestTheChecksumAdjudicates(unittest.TestCase):
    def test_a_frame_read_on_the_wrong_side_is_rejected(self):
        # Sized as a request the reader stops at offset 8 and compares its
        # checksum against register data, which cannot match.
        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)

        self.assertEqual(splitter.push(FC3_RESPONSE), [])
        self.assertGreater(splitter.resyncs, 0)

    def test_the_stream_recovers_on_the_next_frame(self):
        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)

        found = splitter.push(FC3_RESPONSE + FC3_REQUEST)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].serialize(), FC3_REQUEST)

    def test_leading_noise_is_discarded(self):
        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)

        found = splitter.push(b"\x00\xff\x00" + FC3_REQUEST)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].serialize(), FC3_REQUEST)
        self.assertGreater(splitter.resyncs, 0)

    def test_a_corrupt_frame_does_not_come_back(self):
        corrupt = bytearray(FC3_REQUEST)
        corrupt[-1] ^= 0xFF

        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)

        self.assertEqual(splitter.push(bytes(corrupt)), [])


class TestLengthCannotSeparateTheDirections(unittest.TestCase):
    def test_both_read_coil_frames_are_the_same_length(self):
        # The reason the splitter is told its side rather than measuring: a
        # read request and a three-byte read response are both eight bytes.
        self.assertEqual(len(FC1_REQUEST), len(FC1_RESPONSE))

    def test_each_side_frames_its_own(self):
        for side, frame in ((RtuSide.REQUEST, FC1_REQUEST), (RtuSide.RESPONSE, FC1_RESPONSE)):
            with self.subTest(side=side):
                splitter = ModbusRtuSplitter(side=side)
                found = splitter.push(frame)

                self.assertEqual(len(found), 1)
                self.assertEqual(found[0].serialize(), frame)


class TestFramesTheLayoutCannotSize(unittest.TestCase):
    def test_a_diagnostics_frame_the_table_sizes_is_framed(self):
        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)

        found = splitter.push(FC8_RESTART)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].serialize(), FC8_RESTART)

    def test_return_query_data_does_not_stall_the_stream(self):
        # Return Query Data echoes the client's bytes, so no byte of the
        # prefix says where the frame ends. It is lost; the next one is not.
        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)

        found = splitter.push(FC8_ECHO + FC3_REQUEST)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].serialize(), FC3_REQUEST)
        self.assertGreater(splitter.resyncs, 0)

    def test_an_unknown_function_code_does_not_stall_the_stream(self):
        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)

        found = splitter.push(UNKNOWN_FUNCTION + FC3_REQUEST)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].serialize(), FC3_REQUEST)


class TestBookkeeping(unittest.TestCase):
    def test_pending_reports_the_bytes_held_back(self):
        splitter = ModbusRtuSplitter(side=RtuSide.RESPONSE)

        splitter.push(FC3_RESPONSE + FC3_RESPONSE[:4])

        self.assertEqual(splitter.pending, 4)

    def test_reset_drops_the_buffer_and_the_count(self):
        splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)
        splitter.push(b"\x00\xff\x00" + FC3_REQUEST[:3])

        splitter.reset()

        self.assertEqual(splitter.pending, 0)
        self.assertEqual(splitter.resyncs, 0)

    def test_the_side_is_reported(self):
        splitter = ModbusRtuSplitter(side=RtuSide.RESPONSE)

        self.assertIn("response", str(splitter))


if __name__ == "__main__":
    unittest.main()
