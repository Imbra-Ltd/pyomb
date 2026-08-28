"""The sender's lock was the class, not an instance of it.

ModbusTcpSender assigned `threading.Lock` where ModbusTcpReceiver, doing the
same job three lines apart, assigned `threading.Lock()`. Missing parentheses
bind the unconstructed lock, which cannot be acquired and cannot be entered.
It stayed invisible because the sender never takes its lock -- the receiver is
the only one of the pair that does.

Everything here exercises the attribute rather than inspecting it, and asserts
nothing about which exception an unusable one produces. Both of those turned
out to vary: `threading.Lock` is a type on Windows and the builtin function
`_thread.allocate_lock` on Linux, so `hasattr(x, 'acquire')` holds for the
defect on one and `isinstance(x, type)` holds for it on the other; and
entering it raises AttributeError on Python 3.10 where 3.13 raises TypeError.
Using the object is the only description that survives all four combinations.

Those tests describe the lock and not what takes it, which is the gap the
second half of this module closes. Every one of them passed against a sender
whose lock was created and never acquired: they assert the object works, that
the pair do not share one, and that both are the same type -- all properties of
the lock rather than of the code around it. Coverage reported the lines as
covered, because they were, by a witness that could not disagree.

So the classes below record acquisition instead. A lock that logs its entries
and exits, and a socket that logs its sends, share one list; the order of that
list is what says the send loop ran inside the lock rather than beside it.
"""

import threading
import unittest

from stub_socket import StubSocket

from pyomb.packets import ModbusHeader, ModbusPdu, ModbusTcpPacket
from pyomb.stream import ModbusTcpReceiver, ModbusTcpSender


def exercise(lock):
    """Puts a lock through everything the code does with one.

    Raises, by whatever mechanism the interpreter chooses, if handed something
    that is not a usable lock.
    """

    lock.acquire()
    lock.release()

    with lock:
        pass


def components():
    """The pair that each keep a lock, built on throwaway sockets."""

    return (ModbusTcpSender(sock=StubSocket()), ModbusTcpReceiver(sock=StubSocket()))


class RecordingLock:
    """A real lock that appends to a shared log as it is taken and released.

    Wraps a working lock rather than replacing it, so the code under test gets
    real mutual exclusion and the test gets the order of events.
    """

    def __init__(self, log):
        """Record into the caller's log.

        Args:
            log (list) : The shared event log, appended to in place
        """

        self.log = log
        self.lock = threading.Lock()

    def acquire(self, *args, **kwargs):
        """Take the underlying lock and record it.

        Returns:
            bool : Whatever the underlying lock reports
        """

        result = self.lock.acquire(*args, **kwargs)
        self.log.append("acquire")

        return result

    def release(self):
        """Record the release, then release the underlying lock."""

        self.log.append("release")
        self.lock.release()

    def __enter__(self):
        """Take the lock for a with block.

        Returns:
            RecordingLock : This lock
        """

        self.acquire()

        return self

    def __exit__(self, *exc_info):
        """Release the lock at the end of a with block.

        Returns:
            bool : False, so an exception in the block still propagates
        """

        self.release()

        return False


class LoggingSocket(StubSocket):
    """A stub socket that appends to a shared log on every send."""

    def __init__(self, log):
        """Record into the caller's log.

        Args:
            log (list) : The shared event log, appended to in place
        """

        super().__init__()
        self.log = log

    def send(self, data):
        """Record the send, then behave as the stub does.

        Args:
            data (bytes) : The bytes being written
        """

        self.log.append("send")
        super().send(data)


def a_request():
    """One well-formed request, enough to drive a send.

    Returns:
        ModbusTcpPacket : A read-coils request for three coils from address one
    """

    return ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=1, data=(0, 1, 0, 3)))


class TestStreamLocks(unittest.TestCase):
    def test_each_component_holds_a_working_lock(self):
        for component in components():
            with self.subTest(component=type(component).__name__):
                exercise(component._lock)

    def test_the_locks_are_not_shared_between_components(self):
        sender, receiver = components()

        self.assertIsNot(sender._lock, receiver._lock)

    def test_the_pair_agree_on_the_type(self):
        sender, receiver = components()

        self.assertIs(type(sender._lock), type(receiver._lock))


class TestTheSenderTakesItsLock(unittest.TestCase):
    """The sender's lock guards the settings and the send loop."""

    def test_the_send_loop_runs_inside_the_lock(self):
        log = []
        sender = ModbusTcpSender(sock=LoggingSocket(log), packets=[a_request()])
        sender._lock = RecordingLock(log)

        sender.run_once()

        self.assertIn("acquire", log, "run_once never took the lock")
        self.assertIn("send", log, "run_once never reached the socket")

        # A list has no rindex, so the last send is found from the reversed
        # copy. It is the last one that has to fall before the release.
        last_send = len(log) - 1 - log[::-1].index("send")

        self.assertLess(log.index("acquire"), log.index("send"))
        self.assertGreater(log.index("release"), last_send)

    def test_each_setter_takes_the_lock(self):
        """A setter racing the copy into the stream is what tears a config."""

        for name, value in (("set_frag_size", 7), ("set_frag_delay", 0), ("set_burst_mode", True)):
            with self.subTest(setter=name):
                log = []
                sender = ModbusTcpSender(sock=StubSocket())
                sender._lock = RecordingLock(log)

                getattr(sender, name)(value)

                self.assertEqual(log, ["acquire", "release"])


class TestTheReceiverTakesItsLock(unittest.TestCase):
    """The receiver's lock guards the list a reader may be walking."""

    def test_appending_a_packet_runs_inside_the_lock(self):
        log = []
        receiver = ModbusTcpReceiver(sock=LoggingSocket(log))
        receiver._lock = RecordingLock(log)

        receiver.run_once()

        self.assertIn("acquire", log, "run_once never took the lock")
        self.assertEqual(len(receiver.packets), 1)


class TestLockShapeIsNotVacuous(unittest.TestCase):
    """Confirms the check above would reject the defect it describes."""

    def test_the_unconstructed_lock_does_not_pass(self):
        # Deliberately broad: the claim is that this fails, not that it fails
        # in the particular way one interpreter happens to report. Entering the
        # unconstructed class raises AttributeError on 3.10 and TypeError on
        # 3.13, so naming either class writes one interpreter's answer into a
        # test that runs on both. B017 asks for the narrower assertion and is
        # wrong here for that reason.
        with self.assertRaises(Exception):  # noqa: B017
            exercise(threading.Lock)


if __name__ == "__main__":
    unittest.main()
