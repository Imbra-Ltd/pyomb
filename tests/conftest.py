"""The suite's tier hook, and the guard that no test outlives itself.

Two things share this file because both have to reach every tier, and a
conftest reaches the directory it sits in and everything below it. Moving
either one down a level would silently narrow it to one tier.

**The tier comes from the directory.** The hook below marks every item under
`tests/integration/` and nothing else, so no module carries a marker of its
own and a marker cannot drift from where a test sits. The manifest deselects
that marker by default, which is what makes a bare `pytest` open no socket;
`pytest -m integration` is how the heavy tier is run.

**No test may leave a server thread running behind it.** The simulator is a
thread, and only the fixture that started it knows when it is finished. A
fixture that guesses with a sleep instead of joining lets the thread run on
into the next test and, at the end of the run, into pytest's capture teardown.
The thread's next log write then lands on a closed stream and prints a logging
traceback beside unrelated output, which reads as a failure and is not one.

The guard turns that into a named failure at the point it happens. It costs
nothing on a clean run: the check is a list comprehension over the live
threads, and it waits for nothing.
"""

import pathlib
import threading

import pytest

SERVER_THREAD_NAME = "ModbusServerSimulator"

# The directory whose contents are the heavy tier, and the marker derived from
# it. The name is registered in the manifest, which is also where the default
# deselection lives -- a marker pytest does not know about is a warning rather
# than a filter.
INTEGRATION_DIRECTORY = "integration"

INTEGRATION_MARKER = "integration"


def pytest_collection_modifyitems(items):
    """Mark every collected item that lives in the integration directory.

    Args:
        items (list) : The collected items, modified in place
    """

    here = pathlib.Path(__file__).parent

    for item in items:
        path = pathlib.Path(str(item.fspath))

        # Compare against this file's own directory rather than the repository
        # root. A relative_to on a path outside the suite raises, and src/ and
        # checks/ items are collected in the same run.
        try:
            relative = path.relative_to(here)
        except ValueError:
            continue

        if relative.parts and relative.parts[0] == INTEGRATION_DIRECTORY:
            item.add_marker(INTEGRATION_MARKER)


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
