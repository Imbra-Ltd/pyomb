"""A bug in response-building is not disguised as a device failure.

The dispatch handler turns any failure while building or sending a response
into Modbus exception code 0x04 (SLAVE_DEVICE_FAILURE), which is correct for
a factory that legitimately refuses a request. It used to do the same for a
bug in this module itself -- a broken factory, a coding mistake -- reporting
a specification-compliant response for what was actually a defect nothing
would ever surface.

Both properties are pinned by patching ResponseFactory.create_fc1_rsp, the
narrowest place to inject either kind of failure without depending on which
request shape a factory happens to reject.
"""

import unittest
from unittest.mock import patch

from pyomb.errors import ModbusIllegalDataValueError, ModbusSlaveDeviceFailureError
from pyomb.simulators.server import ModbusServerSimulator, ResponseFactory

# Trans-ID 1, Prot-ID 0, Length 6, Unit-ID 1, FC1 read 1 coil from address 0.
FC1_REQUEST = bytes.fromhex("000100000006") + bytes([1]) + bytes([1, 0, 0, 0, 1])


class RecordingConnection:
    """Stands in for a client socket and keeps what the server wrote."""

    def __init__(self):
        self.sent = []

    def send(self, data):
        """Record one write and report it as fully sent.

        Args:
            data (bytes) : The bytes the server is sending

        Returns:
            int : The number of bytes accepted
        """
        self.sent.append(data)

        return len(data)


class ABuiltInProtocolErrorStillBecomesSlaveDeviceFailure(unittest.TestCase):
    """The control: narrowing the catch must not remove the intended behaviour."""

    def setUp(self):
        self.server = ModbusServerSimulator()
        self.conn = RecordingConnection()

    def test_a_response_factory_error_is_reported_as_exception_code_4(self):
        with (
            patch.object(ResponseFactory, "create_fc1_rsp", side_effect=ModbusIllegalDataValueError(3)),
            self.assertRaises(ModbusSlaveDeviceFailureError),
        ):
            self.server.on_data(FC1_REQUEST, self.conn)


class ABugInResponseBuildingIsNotDisguised(unittest.TestCase):
    """The fix: a coding mistake must surface as itself, not as a device failure."""

    def setUp(self):
        self.server = ModbusServerSimulator()
        self.conn = RecordingConnection()

    def test_an_unrelated_bug_propagates_as_itself(self):
        with (
            patch.object(ResponseFactory, "create_fc1_rsp", side_effect=TypeError("wrong type")),
            self.assertRaises(TypeError),
        ):
            self.server.on_data(FC1_REQUEST, self.conn)

    def test_nothing_is_written_back_for_the_unrelated_bug(self):
        with patch.object(ResponseFactory, "create_fc1_rsp", side_effect=TypeError("wrong type")):
            with self.assertRaises(TypeError):
                self.server.on_data(FC1_REQUEST, self.conn)

            self.assertEqual(self.conn.sent, [])


if __name__ == "__main__":
    unittest.main()
