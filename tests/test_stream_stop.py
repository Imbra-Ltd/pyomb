"""Stopping a sender or a receiver stops it.

Both classes build a `threading.Event` in their constructor and set it in
`stop()`. Neither ever read it. The event was written and never consulted, so
`stop()` returned having changed nothing a later call could observe, and
`run_once()` went on sending or receiving exactly as before.

That is the same shape as the sender's unacquired lock, one field over: a
threading primitive created, wired to a public method, and never consulted.
Finding the first is what prompted the search that found the second -- a
`grep` for `is_set` and `wait(` across the module returned nothing at all.

The tests here are behavioural. They do not assert that the event is read,
which would pin the mechanism; they assert that a stopped component does no
work, which is the promise `stop()` makes to a caller.
"""

import unittest

from pyomb.packets import ModbusHeader, ModbusPdu, ModbusTcpPacket
from pyomb.stream import ModbusTcpReceiver, ModbusTcpSender
from tests.helpers.stub_socket import StubSocket


def a_request():
    """One well-formed request, enough to drive a send.

    Returns:
        ModbusTcpPacket : A read-coils request for three coils from address one
    """

    return ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=1, data=(0, 1, 0, 3)))


class StoppingTheSender(unittest.TestCase):
    """A stopped sender writes nothing to the socket."""

    def test_a_stopped_sender_sends_nothing(self):
        sock = StubSocket()
        sender = ModbusTcpSender(sock=sock, packets=[a_request()])

        sender.stop()
        sender.run_once()

        self.assertEqual(sock.sent_data, [])

    def test_a_sender_that_was_not_stopped_still_sends(self):
        """The guard is the stop, not a sender that never sends at all."""

        sock = StubSocket()
        sender = ModbusTcpSender(sock=sock, packets=[a_request()])

        sender.run_once()

        self.assertNotEqual(sock.sent_data, [])


class StoppingTheReceiver(unittest.TestCase):
    """A stopped receiver collects nothing from the socket."""

    def test_a_stopped_receiver_collects_nothing(self):
        receiver = ModbusTcpReceiver(sock=StubSocket())

        receiver.stop()

        self.assertEqual(receiver.run_once(), [])

    def test_a_receiver_that_was_not_stopped_still_collects(self):
        """The same guard on the other half of the pair."""

        receiver = ModbusTcpReceiver(sock=StubSocket())

        self.assertNotEqual(receiver.run_once(), [])


if __name__ == "__main__":
    unittest.main()
