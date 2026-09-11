"""The RTU stream reads whole frames off a port it was handed, one verdict at a time.

The port double records every read size, which is the property under test: a
stream that asks for more than the frame needs stalls on a port with a long
timeout, and one that asks for less loops for nothing. The vectors are the
published ones the splitter test uses. The frames the layout cannot size are
constructed, and their checksums are computed here so they are valid frames.
"""

import struct
import unittest

from pyomb.adu.rtu import calc_crc16
from pyomb.errors import ModbusNetworkError, ModbusPacketError, ModbusTimeoutError
from pyomb.transport import MAX_RTU_FRAME, ModbusRtuStream, RtuSide
from tests.helpers.stub_port import FakePort, ShortWritingPort

# 11 03 00 6B 00 03 -- read three holding registers from 0x006B on slave 17.
FC3_REQUEST = b"\x11\x03\x00\x6b\x00\x03\x76\x87"

# 11 03 06 AE 41 56 52 43 40 -- the three registers coming back.
FC3_RESPONSE = b"\x11\x03\x06\xae\x41\x56\x52\x43\x40\x49\xad"

# 01 83 02 -- slave 1 refuses an FC3 with ILLEGAL DATA ADDRESS.
EXCEPTION_RESPONSE = b"\x01\x83\x02\xc0\xf1"


def framed(payload):
    """The payload with its checksum appended, low byte first."""
    return payload + struct.pack("<H", calc_crc16(payload))


# 11 2B 0E 01 01 00 00 01 00 05 "Imbra" -- Read Device Identification with one
# object. Objects are length-prefixed one after another, so no prefix sizes it.
FC43_RESPONSE = framed(b"\x11\x2b\x0e\x01\x01\x00\x00\x01\x00\x05Imbra")

# 11 47 DE AD -- a function code this library does not model.
UNKNOWN_FUNCTION = framed(b"\x11\x47\xde\xad")


class TestReadsAreExact(unittest.TestCase):
    def test_a_fixed_size_request_takes_the_head_then_the_rest(self):
        port = FakePort(FC3_REQUEST)
        stream = ModbusRtuStream(port=port, side=RtuSide.REQUEST)

        self.assertEqual(stream.receive(), FC3_REQUEST)
        self.assertEqual(port.reads, [4, 4])

    def test_a_counted_response_reads_the_head_then_what_the_count_says(self):
        port = FakePort(FC3_RESPONSE)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertEqual(stream.receive(), FC3_RESPONSE)
        self.assertEqual(port.reads, [4, 7])

    def test_an_exception_response_takes_one_more_byte(self):
        port = FakePort(EXCEPTION_RESPONSE)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertEqual(stream.receive(), EXCEPTION_RESPONSE)
        self.assertEqual(port.reads, [4, 1])

    def test_the_port_is_never_asked_for_more_than_the_frame_holds(self):
        # The latency trap: one read past the frame's end waits out the whole
        # timeout on a real port, so the sizes asked for add up to the frame.
        for side, frame in (
            (RtuSide.REQUEST, FC3_REQUEST),
            (RtuSide.RESPONSE, FC3_RESPONSE),
            (RtuSide.RESPONSE, EXCEPTION_RESPONSE),
        ):
            with self.subTest(frame=frame.hex()):
                port = FakePort(frame)

                ModbusRtuStream(port=port, side=side).receive()

                self.assertEqual(sum(port.reads), len(frame))

    def test_a_slow_port_is_read_until_the_frame_completes(self):
        port = FakePort(FC3_RESPONSE, per_read=1)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertEqual(stream.receive(), FC3_RESPONSE)
        self.assertEqual(len(port.reads), len(FC3_RESPONSE))

    def test_back_to_back_frames_come_off_one_receive_each(self):
        port = FakePort(FC3_RESPONSE + EXCEPTION_RESPONSE)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertEqual(stream.receive(), FC3_RESPONSE)
        self.assertEqual(stream.receive(), EXCEPTION_RESPONSE)
        self.assertEqual(stream.resyncs, 0)


class TestSilence(unittest.TestCase):
    def test_nothing_at_all_is_a_timeout(self):
        stream = ModbusRtuStream(port=FakePort(b""), side=RtuSide.RESPONSE)

        self.assertRaises(ModbusTimeoutError, stream.receive)

    def test_a_port_that_raises_on_its_timeout_reports_the_same_silence(self):
        stream = ModbusRtuStream(port=FakePort(b"", failure=TimeoutError()), side=RtuSide.RESPONSE)

        self.assertRaises(ModbusTimeoutError, stream.receive)

    def test_a_stray_byte_ahead_of_the_reply_is_discarded(self):
        port = FakePort(b"\x00" + FC3_RESPONSE)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertEqual(stream.receive(), FC3_RESPONSE)
        self.assertEqual(stream.resyncs, 1)

    def test_the_echo_of_a_request_ahead_of_the_reply_is_skipped(self):
        # A transceiver echoing with the stream not told so: the echo fails its
        # checksum as a response and is scanned past until the reply lines up.
        port = FakePort(FC3_REQUEST + FC3_RESPONSE)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertEqual(stream.receive(), FC3_RESPONSE)
        self.assertEqual(stream.resyncs, len(FC3_REQUEST))

    def test_a_truncated_frame_is_reported_with_what_arrived(self):
        stream = ModbusRtuStream(port=FakePort(FC3_RESPONSE[:7]), side=RtuSide.RESPONSE)

        with self.assertRaises(ModbusPacketError) as caught:
            stream.receive()

        self.assertIn("7 byte(s)", str(caught.exception))
        self.assertIn("framed to nothing", str(caught.exception))

    def test_what_framed_to_nothing_is_dropped_before_the_next_frame(self):
        port = FakePort(FC3_RESPONSE[:7])
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertRaises(ModbusPacketError, stream.receive)

        port.inbox.extend(FC3_RESPONSE)

        self.assertEqual(stream.receive(), FC3_RESPONSE)


class TestFramesTheRegistryCannotSize(unittest.TestCase):
    def test_a_device_identification_reply_is_read_by_silence(self):
        port = FakePort(FC43_RESPONSE)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertEqual(stream.receive(), FC43_RESPONSE)

    def test_an_unknown_function_code_is_read_by_silence(self):
        stream = ModbusRtuStream(port=FakePort(UNKNOWN_FUNCTION), side=RtuSide.REQUEST)

        self.assertEqual(stream.receive(), UNKNOWN_FUNCTION)

    def test_the_silence_read_stays_within_the_largest_frame(self):
        port = FakePort(FC43_RESPONSE)

        ModbusRtuStream(port=port, side=RtuSide.RESPONSE).receive()

        self.assertLessEqual(max(port.reads), MAX_RTU_FRAME)

    def test_a_corrupt_unsizable_frame_is_reported(self):
        corrupt = bytearray(FC43_RESPONSE)
        corrupt[-1] ^= 0xFF
        stream = ModbusRtuStream(port=FakePort(bytes(corrupt)), side=RtuSide.RESPONSE)

        self.assertRaises(ModbusPacketError, stream.receive)

    def test_a_sizable_frame_behind_an_unsizable_one_is_still_found(self):
        # The whole buffer fails its checksum, so what was held is scanned.
        port = FakePort(UNKNOWN_FUNCTION[:-1] + FC3_RESPONSE)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE)

        self.assertEqual(stream.receive(), FC3_RESPONSE)
        self.assertGreater(stream.resyncs, 0)


class TestSend(unittest.TestCase):
    def test_a_frame_is_written_whole(self):
        port = FakePort()

        ModbusRtuStream(port=port, side=RtuSide.RESPONSE).send(FC3_REQUEST)

        self.assertEqual(port.writes, [FC3_REQUEST])
        self.assertEqual(port.reads, [])

    def test_a_short_write_is_a_network_error(self):
        stream = ModbusRtuStream(port=ShortWritingPort(), side=RtuSide.RESPONSE)

        self.assertRaises(ModbusNetworkError, stream.send, FC3_REQUEST)

    def test_a_failing_port_is_a_network_error(self):
        stream = ModbusRtuStream(port=FakePort(failure=OSError("unplugged")), side=RtuSide.RESPONSE)

        with self.assertRaises(ModbusNetworkError) as caught:
            stream.receive()

        self.assertNotIsInstance(caught.exception, ModbusTimeoutError)
        self.assertIn("unplugged", str(caught.exception))


class TestEcho(unittest.TestCase):
    def test_the_echo_is_read_back_and_the_reply_comes_next(self):
        port = FakePort(FC3_RESPONSE, echo=True)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE, echo=True)

        stream.send(FC3_REQUEST)

        self.assertEqual(port.reads, [len(FC3_REQUEST)])
        self.assertEqual(stream.receive(), FC3_RESPONSE)

    def test_a_short_echo_is_read_until_complete(self):
        port = FakePort(FC3_RESPONSE, echo=True, per_read=3)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE, echo=True)

        stream.send(FC3_REQUEST)

        self.assertEqual(stream.receive(), FC3_RESPONSE)

    def test_a_mismatched_echo_is_a_collision_and_the_line_is_drained(self):
        clashed = bytes(FC3_REQUEST[:-2]) + b"\xff\xff"
        port = FakePort(clashed + FC3_RESPONSE)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE, echo=True)

        with self.assertRaises(ModbusNetworkError) as caught:
            stream.send(FC3_REQUEST)

        self.assertIn("collision", str(caught.exception))
        self.assertEqual(bytes(port.inbox), b"")

    def test_with_echo_off_nothing_is_read_back(self):
        port = FakePort(FC3_RESPONSE, echo=True)
        stream = ModbusRtuStream(port=port, side=RtuSide.RESPONSE, echo=False)

        stream.send(FC3_REQUEST)

        self.assertEqual(port.reads, [])


if __name__ == "__main__":
    unittest.main()
