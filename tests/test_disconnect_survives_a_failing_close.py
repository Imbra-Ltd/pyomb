"""A close that fails does not escape the teardown or strand the socket.

`disconnect()` treats `shutdown()` as able to fail -- a peer that has gone away
is the ordinary case on that path, not a fault -- and used not to treat
`close()` the same way. The close sat in a `finally` with nothing catching it,
so a close that raised escaped the method and the line clearing the attribute
never ran. The client was then left holding a socket it had already given up
on, which is the opposite of what a teardown is for.

Whether a close raises is a platform difference. On Windows a close on a reset
socket is silent, and on Linux the same call can raise `ENOTCONN`. Development
here is Windows and CI is Linux, so waiting for a platform to supply the fault
means the defect reproduces only where nobody is looking. The fault is injected
instead, from a double at the same seam the real call sits on.

The third test is the one that keeps the fix honest. `shutdown()` is not made
redundant by the `close()` that follows it: it sends the FIN immediately and
unconditionally, where `close()` only does so when no other reference to the
socket remains. Deleting it would make the first two tests pass and change what
a peer observes, so it is pinned.
"""

import contextlib
import unittest

from pyomb.client_simulator import ModbusClientSimulator


class ClosingRaises:
    """A socket whose close fails the way a reset peer's does on Linux.

    Substituted for the client's own socket rather than for the socket module,
    because the seam the method under test reads is the attribute.
    """

    def __init__(self):
        """Start with nothing recorded."""

        self.shutdown_calls = 0
        self.close_calls = 0

    def shutdown(self, how):
        """Record the call and return, the way a healthy socket does.

        Args:
            how (int) : Which half of the connection to shut down
        """

        self.shutdown_calls += 1

    def close(self):
        """Record the call, then fail.

        Raises:
            OSError : Always, standing in for ENOTCONN on a reset socket
        """

        self.close_calls += 1

        raise OSError(107, "Transport endpoint is not connected")


def client_whose_close_fails():
    """A connected-looking client whose socket refuses to close.

    Returns:
        tuple[ModbusClientSimulator, ClosingRaises] : The client and its socket double
    """

    client = ModbusClientSimulator(host=b"127.0.0.1", port=502)

    # The constructor opens a real socket. Close it before the double takes its
    # place, so the test leaves no descriptor behind.
    client.sock.close()

    double = ClosingRaises()
    client.sock = double

    return client, double


class TeardownSurvivesAFailingClose(unittest.TestCase):
    """The teardown completes on the path where the close itself fails."""

    def test_a_failing_close_does_not_escape(self):
        client, _ = client_whose_close_fails()

        client.disconnect()

    def test_the_socket_is_cleared_when_the_close_fails(self):
        """The attribute is cleared on every path, including the failing one."""

        client, _ = client_whose_close_fails()

        # Suppressed so this test reports on the clearing rather than on the
        # escape, which is what the test above is for. Against the unfixed
        # code both fail, and they fail for different reasons.
        with contextlib.suppress(OSError):
            client.disconnect()

        self.assertIsNone(client.sock)

    def test_the_shutdown_is_still_attempted(self):
        """Deleting shutdown would pass the tests above and change the wire."""

        client, double = client_whose_close_fails()

        with contextlib.suppress(OSError):
            client.disconnect()

        self.assertEqual(double.shutdown_calls, 1)
        self.assertEqual(double.close_calls, 1)


if __name__ == "__main__":
    unittest.main()
