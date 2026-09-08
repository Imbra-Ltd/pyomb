"""A close that fails does not escape the teardown or strand the socket.

`disconnect()` treats `shutdown()` as able to fail and used not to treat
`close()` the same way. The close sat in a `finally` catching nothing, so one
that raised escaped and never cleared the attribute.

Whether a close raises is a platform difference -- silent on Windows,
`ENOTCONN` on Linux -- so the fault is injected from a double at the same
seam rather than waited for.

The third test keeps the fix honest. `shutdown()` sends the FIN immediately
where `close()` waits for the last reference, so deleting it would pass the
first two and change what a peer observes.
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

        # Suppressed so this reports on the clearing rather than the escape,
        # which the test above covers. Both fail unfixed, for different reasons.
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
