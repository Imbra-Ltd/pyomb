"""The sniffer works out which way each frame on a bus was travelling.

A splitter is told which direction it decodes. A sniffer watching two devices
talk is told nothing, so it reads each frame both ways and keeps whichever the
checksum accepts. Where both are accepted the frame is genuinely ambiguous,
and the bus takes turns, so the expected direction decides.

The frames below are published specification vectors, so the bytes are
anchored outside this library. The broadcast and the echo pair are
constructed, because no published example covers them as raw frames.
"""

import unittest

from pyomb.packets import ModbusRtuSniffer, RtuSide, RtuSyncState

# 11 03 00 6B 00 03 -- read three holding registers from 0x006B on slave 17.
FC3_REQUEST = b"\x11\x03\x00\x6b\x00\x03\x76\x87"

# 11 03 06 AE 41 56 52 43 40 -- the three registers coming back.
FC3_RESPONSE = b"\x11\x03\x06\xae\x41\x56\x52\x43\x40\x49\xad"

# 11 01 00 13 00 25 -- read 37 coils from 0x0013 on slave 17.
FC1_REQUEST = b"\x11\x01\x00\x13\x00\x25\x0e\x84"

# 11 01 03 CD 6B B2 -- three bytes of coil data. As long as the request above
# and just as valid, so only the turn taken separates the two.
FC1_RESPONSE = b"\x11\x01\x03\xcd\x6b\xb2\x00\x64"

# 01 83 02 -- slave 1 refuses an FC3 with ILLEGAL DATA ADDRESS. Only a server
# sets the top bit of the function code.
EXCEPTION_RESPONSE = b"\x01\x83\x02\xc0\xf1"

# 00 06 00 01 00 03 -- write a single register to the broadcast address, which
# every device recognises and none answers.
BROADCAST_REQUEST = b"\x00\x06\x00\x01\x00\x03\x99\xda"


class Clock:
    """A time source the suite advances by hand rather than by sleeping."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestAnExchangeIsReadBothWays(unittest.TestCase):
    def test_a_request_and_its_answer_are_told_apart(self):
        sniffer = ModbusRtuSniffer()

        found = sniffer.push(FC3_REQUEST + FC3_RESPONSE)

        self.assertEqual([frame.side for frame in found], [RtuSide.REQUEST, RtuSide.RESPONSE])
        self.assertEqual([frame.packet.serialize() for frame in found], [FC3_REQUEST, FC3_RESPONSE])

    def test_the_answer_alone_is_still_read_as_a_response(self):
        # Nothing has been seen yet, so the state expects a request. Only the
        # response sizes to a boundary where the checksum lands.
        sniffer = ModbusRtuSniffer()

        found = sniffer.push(FC3_RESPONSE)

        self.assertEqual(len(found), 1)
        self.assertIs(found[0].side, RtuSide.RESPONSE)

    def test_bytes_arriving_in_pieces_still_yield_the_exchange(self):
        sniffer = ModbusRtuSniffer()
        found = []

        for byte in FC3_REQUEST + FC3_RESPONSE:
            found.extend(sniffer.push(bytes([byte])))

        self.assertEqual([frame.side for frame in found], [RtuSide.REQUEST, RtuSide.RESPONSE])
        self.assertEqual(sniffer.resyncs, 0)


class TestWhatTheBytesGiveAway(unittest.TestCase):
    def test_an_exception_is_a_response_whatever_was_expected(self):
        sniffer = ModbusRtuSniffer()

        found = sniffer.push(EXCEPTION_RESPONSE)

        self.assertEqual(len(found), 1)
        self.assertIs(found[0].side, RtuSide.RESPONSE)
        self.assertIs(sniffer.state, RtuSyncState.EXPECT_REQUEST)

    def test_a_broadcast_is_a_request_that_expects_no_answer(self):
        sniffer = ModbusRtuSniffer()

        found = sniffer.push(BROADCAST_REQUEST)

        self.assertEqual(len(found), 1)
        self.assertIs(found[0].side, RtuSide.REQUEST)
        self.assertIs(sniffer.state, RtuSyncState.EXPECT_REQUEST)


class TestTakingTurns(unittest.TestCase):
    def test_the_state_follows_the_exchange(self):
        sniffer = ModbusRtuSniffer()

        self.assertIs(sniffer.state, RtuSyncState.SYNCING)

        sniffer.push(FC3_REQUEST)
        self.assertIs(sniffer.state, RtuSyncState.EXPECT_RESPONSE)

        sniffer.push(FC3_RESPONSE)
        self.assertIs(sniffer.state, RtuSyncState.EXPECT_REQUEST)

    def test_an_ambiguous_pair_is_separated_by_the_turn(self):
        # Both read-coil frames are eight bytes and both check out, so the
        # checksum cannot separate them and only the turn taken can.
        sniffer = ModbusRtuSniffer()

        found = sniffer.push(FC1_REQUEST + FC1_RESPONSE)

        self.assertEqual([frame.side for frame in found], [RtuSide.REQUEST, RtuSide.RESPONSE])

    def test_an_ambiguous_frame_alone_reads_as_a_request(self):
        sniffer = ModbusRtuSniffer()

        found = sniffer.push(FC1_RESPONSE)

        self.assertEqual(len(found), 1)
        self.assertIs(found[0].side, RtuSide.REQUEST)


class TestTheTimeout(unittest.TestCase):
    def test_an_unanswered_request_expires(self):
        clock = Clock()
        sniffer = ModbusRtuSniffer(timeout=1.0, clock=clock)

        sniffer.push(FC3_REQUEST)
        self.assertIs(sniffer.state, RtuSyncState.EXPECT_RESPONSE)

        clock.advance(1.5)
        sniffer.push(b"")

        self.assertIs(sniffer.state, RtuSyncState.EXPECT_REQUEST)

    def test_an_answer_inside_the_timeout_is_not_expired(self):
        clock = Clock()
        sniffer = ModbusRtuSniffer(timeout=1.0, clock=clock)

        sniffer.push(FC3_REQUEST)
        clock.advance(0.5)

        self.assertIs(sniffer.state, RtuSyncState.EXPECT_RESPONSE)

        found = sniffer.push(FC1_RESPONSE)

        self.assertIs(found[0].side, RtuSide.RESPONSE)

    def test_expiry_changes_how_an_ambiguous_frame_reads(self):
        # The control for the test above: same bytes, same sniffer, and only
        # the clock moved between them.
        clock = Clock()
        sniffer = ModbusRtuSniffer(timeout=1.0, clock=clock)

        sniffer.push(FC3_REQUEST)
        clock.advance(1.5)

        found = sniffer.push(FC1_RESPONSE)

        self.assertIs(found[0].side, RtuSide.REQUEST)


class TestNoiseAndBookkeeping(unittest.TestCase):
    def test_leading_noise_is_discarded(self):
        sniffer = ModbusRtuSniffer()

        found = sniffer.push(b"\x00\xff\x00" + FC3_REQUEST)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].packet.serialize(), FC3_REQUEST)
        self.assertGreater(sniffer.resyncs, 0)

    def test_pending_reports_the_bytes_held_back(self):
        sniffer = ModbusRtuSniffer()

        sniffer.push(FC3_REQUEST + FC3_RESPONSE[:4])

        self.assertEqual(sniffer.pending, 4)

    def test_reset_returns_it_to_knowing_nothing(self):
        sniffer = ModbusRtuSniffer()
        sniffer.push(FC3_REQUEST + FC3_RESPONSE[:4])

        sniffer.reset()

        self.assertEqual(sniffer.pending, 0)
        self.assertEqual(sniffer.resyncs, 0)
        self.assertIs(sniffer.state, RtuSyncState.SYNCING)

    def test_the_state_is_reported(self):
        sniffer = ModbusRtuSniffer()

        self.assertIn("syncing", str(sniffer))


if __name__ == "__main__":
    unittest.main()
