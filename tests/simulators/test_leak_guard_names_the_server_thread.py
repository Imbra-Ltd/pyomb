"""The leak guard's thread name is the name the server thread actually takes.

`conftest.py` fails any test that leaves a simulator thread running, and finds
those threads by comparing `Thread.name` against a string constant. That
constant and the assignment in the server are two copies of one fact, joined
by nothing.

It makes the guard fail open. A constant naming a thread the server does not
produce matches nothing, so every test passes -- including the ones leaking
the thread the guard exists to catch.

Asserting on the name is deliberate where a test would normally assert on
behaviour. The name IS the behaviour: it is the join key the guard matches on.
"""

import unittest

from pyomb.simulators.server_simulator import ModbusServerSimulator
from tests import conftest


class TheGuardWatchesTheNameTheServerSets(unittest.TestCase):
    """Pins one fact that lives in two files."""

    def test_the_guard_constant_is_the_thread_name(self):
        """A guard watching a name nothing produces reports a clean run always."""

        # The constructor names the thread; nothing is started, so this costs
        # no socket and no thread.
        server = ModbusServerSimulator()

        self.assertEqual(
            server.name,
            conftest.SERVER_THREAD_NAME,
            "The leak guard matches live threads against SERVER_THREAD_NAME, and "
            f"the server names its thread {server.name!r}. While these differ the "
            "guard matches nothing and passes every run, leaked thread or not.",
        )


if __name__ == "__main__":
    unittest.main()
