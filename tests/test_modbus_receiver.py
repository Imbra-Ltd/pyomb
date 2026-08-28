import unittest

from stub_socket import StubSocket

from pyomb.packets import ModbusHeader, ModbusPdu, ModbusTcpPacket
from pyomb.stream import ModbusTcpReceiver


class TestModbusReceiver(unittest.TestCase):
    def test_initialization(self):

        # Create an instance of the mocked socket
        sock = StubSocket()

        receiver = ModbusTcpReceiver(
            sock=sock,
        )

        self.assertEqual(receiver.sock, sock)

    def test_run_once(self):

        # Create an instance of the mocked socket
        sock = StubSocket()

        # FC=15, start_addr=1, quantity=3, byte_count=2, data=b'\x00\x01\x00\x02'
        # The MBAP length counts the unit identifier plus the PDU.
        pdu = ModbusPdu(fc=15, data=(0, 1, 0, 3, 2, 0, 1))
        expected_packet = ModbusTcpPacket(header=ModbusHeader(unit_id=1, length=len(pdu) + 1), pdu=pdu)

        # Create the receiver instance
        receiver = ModbusTcpReceiver(
            sock=sock,
        )

        # Set the data to be received
        sock.recv_data = expected_packet.serialize()

        # Run the receiver
        received_packet = receiver.run_once()[0]

        # Test the data received
        self.assertEqual(received_packet, expected_packet)
