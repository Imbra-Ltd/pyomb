"""No test may leave a server thread running behind it.

The simulator is a thread, and only the fixture that started it knows when it
is finished. A fixture that guesses with a sleep instead of joining lets the
thread run on into the next test and, at the end of the run, into pytest's
capture teardown. The thread's next log write then lands on a closed stream and
prints a logging traceback beside unrelated output, which reads as a failure
and is not one.

The guard below turns that into a named failure at the point it happens. It
costs nothing on a clean run: the check is a list comprehension over the live
threads, and it waits for nothing.
"""

import threading

import pytest

SERVER_THREAD_NAME = "ModbusServerSimulator"


@pytest.fixture(autouse=True)
def no_server_thread_outlives_the_test():
    yield

    survivors = [thread for thread in threading.enumerate() if thread.name == SERVER_THREAD_NAME]

    if survivors:
        pytest.fail(
            f"{len(survivors)} {SERVER_THREAD_NAME} thread(s) still running after "
            "the test. Call stop() and then join() it with a timeout in tearDown "
            "-- a sleep is a guess, not a wait."
        )
