"""The client's host parameter is a string everywhere it is stated.

The constructor documented `host (str)` and defaulted it to `b"localhost"`,
and `connect` documented the same value as bytes. Both forms reach the
socket layer and connect, so nothing failed -- what was wrong is that the
parameter had two answers to "what type is this" and a reader had to run
something to find out which one the library meant.

Two of the checks below are drift guards: the declared type and the real
default are the same fact written twice, and so are the two simulators'
descriptions of the parameter they share. Each introspects the live module
rather than restating the answer, so changing one copy and not the other
fails here rather than drifting.

The last check goes the other way. Settling on a string is only safe if the
bytes form keeps working, because callers in this suite pass it, so one test
connects with bytes and asserts the socket came up.
"""

import ast
import inspect
import pathlib
import re
import socket
import unittest

from pyomb.client_simulator import ModbusClientSimulator, run_client
from pyomb.server_simulator import ModbusServerSimulator

# The `host (str)` line of a Google-style Args block, capturing the declared
# type. The character class is spelled out rather than written as a shorthand
# escape, which can be lost on the way into a file while still compiling.
# Both simulators are matched by it: one aligns the colon into a column and
# the other does not, and neither part is inside the group.
DECLARED = re.compile(r"^[ ]*host \(([A-Za-z]+)\)", re.M)


def declared_host_type(subject):
    """Return the type the subject's docstring declares for `host`.

    Args:
        subject (object): A class or function carrying a Google-style
            Args block.

    Returns:
        str: The declared type name.

    Raises:
        AssertionError: If the docstring states no host parameter, which
            means the pattern drifted rather than the type being absent.
    """
    text = inspect.getdoc(subject) or ""
    found = DECLARED.search(text)

    name = getattr(subject, "__name__", subject)

    assert found is not None, (
        f"{name} does not document a host parameter in the form this check "
        "reads; the docstring convention moved and the comparison below "
        "reached nothing"
    )

    return found.group(1)


class TestTheDeclaredTypeMatchesTheDefault(unittest.TestCase):
    def test_constructor_default_is_the_type_the_docstring_declares(self):
        default = inspect.signature(ModbusClientSimulator).parameters["host"].default

        self.assertEqual(declared_host_type(ModbusClientSimulator), type(default).__name__)

    def test_connect_declares_the_same_type_as_the_constructor(self):
        self.assertEqual(
            declared_host_type(ModbusClientSimulator.connect),
            declared_host_type(ModbusClientSimulator),
        )

    def test_both_simulators_describe_host_the_same_way(self):
        self.assertEqual(
            declared_host_type(ModbusClientSimulator),
            declared_host_type(ModbusServerSimulator),
        )


class TestTheEntryPointDemonstratesTheDocumentedType(unittest.TestCase):
    """`run_client` is what a reader running the module as a script sees.

    It builds its client inline rather than taking a default, so no signature
    carries the value and the source is where it is stated. Reading it as a
    tree rather than as text keeps the check on the argument itself instead
    of on any line that happens to spell the same characters.
    """

    def host_argument_of_run_client(self):
        source = pathlib.Path(inspect.getfile(run_client)).read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name != "run_client":
                continue

            for call in ast.walk(node):
                if not isinstance(call, ast.Call):
                    continue

                for keyword in call.keywords:
                    if keyword.arg == "host":
                        return keyword.value

        return None

    def test_run_client_passes_the_documented_type(self):
        argument = self.host_argument_of_run_client()

        self.assertIsNotNone(
            argument,
            "run_client passes no host keyword; the entry point moved and this check inspected nothing",
        )
        self.assertIsInstance(argument, ast.Constant)
        self.assertEqual(declared_host_type(ModbusClientSimulator), type(argument.value).__name__)


class TestTheBytesFormStillConnects(unittest.TestCase):
    """Settling on a string must not break the callers already passing bytes.

    A listening socket completes the handshake from its backlog, so the peer
    needs no accept loop and no thread -- the assertion is that the client's
    socket has a peer, which is what connecting means.
    """

    def setUp(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]

    def tearDown(self):
        self.listener.close()

    def test_a_bytes_host_reaches_the_peer(self):
        client = ModbusClientSimulator(host=b"127.0.0.1", port=self.port)
        client.connect()

        try:
            self.assertEqual(client.sock.getpeername()[1], self.port)
        finally:
            client.disconnect()

    def test_a_string_host_reaches_the_peer(self):
        client = ModbusClientSimulator(host="127.0.0.1", port=self.port)
        client.connect()

        try:
            self.assertEqual(client.sock.getpeername()[1], self.port)
        finally:
            client.disconnect()
