"""The suite's tier hook, and the guard that no test outlives itself.

Both live here because both have to reach every tier, and a conftest reaches
its own directory and everything below it. Moving either down a level would
silently narrow it to one tier.

**The tier comes from the directory.** The hook marks every item under
`tests/integration/` and nothing else, so a marker cannot drift from where a
test sits.

**No test may leave a server thread running.** The guard names the test that
does, where the thread would otherwise print a logging traceback beside
unrelated output. PLAYBOOK 3.1 carries why a sleep is not the wait.
"""

import pathlib
import threading

import pytest

SERVER_THREAD_NAME = "ModbusServerSimulator"

# The directory whose contents are the heavy tier, and the marker derived from
# it. A marker the manifest does not register is a warning, not a filter.
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

        # Compare against this file's own directory: relative_to raises on a
        # path outside the suite, and src/ and checks/ are collected too.
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
