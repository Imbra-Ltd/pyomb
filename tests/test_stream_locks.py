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
"""

import threading
import unittest

from stub_socket import StubSocket

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
