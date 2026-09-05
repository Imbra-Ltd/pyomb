import unittest

from pyomb.packets import ModbusHeader, ModbusPdu, ModbusTcpPacket
from pyomb.stream import ModbusTcpSender
from tests.helpers.stub_socket import StubSocket


class TestModbusSender(unittest.TestCase):
    def test_initialization(self):
        # Create an instance of the mocked socket
        sock = StubSocket()

        requests = [
            # FC=15, start_addr=1, quantity=3, byte_count=2, data=b'\x00\x01\x00\x02'
            ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=15, data=(0, 1, 0, 3, 2, 0, 1))),
            # FC1, start_addr=1, quantity=3
            ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=1, data=(0, 1, 0, 3))),
        ]

        # Test initialization
        stream = ModbusTcpSender(
            sock=sock,
            packets=requests,
        )

        # Test initialization
        self.assertEqual(stream.sock, sock)
        self.assertEqual(stream.packets, requests)

    def test_run_once(self):
        # Create an instance of the mocked socket
        sock = StubSocket()

        requests = [
            # FC=15, start_addr=1, quantity=3, byte_count=2, data=b'\x00\x01\x00\x02'
            ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=15, data=(0, 1, 0, 3, 2, 0, 1))),
            # FC1, start_addr=1, quantity=3
            ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=1, data=(0, 1, 0, 3))),
        ]

        # Create the sender instance
        sender = ModbusTcpSender(sock=sock, packets=requests)

        # Set the fragment size to 0 to disable fragmentation
        sender.set_frag_size(0)

        # Get the constructed packets
        sender.run_once()

        # Expected data
        expected_data = [packet.serialize() for packet in requests]

        # Test the data sent
        self.assertEqual(sock.sent_data, expected_data)

        # Reset the socket
        sock.reset()

        # Set the fragment size to 7 to enable fragmentation
        sender.set_frag_size(7)

        # Get the constructed packets
        sender.run_once()

        # Expected data
        serialized_data = [packet.serialize() for packet in requests]

        # Fragment the data
        expected_data = []
        for data in serialized_data:
            for i in range(0, len(data), 7):
                expected_data.append(data[i : i + 7])

        # Test the data sent
        self.assertEqual(sock.sent_data, expected_data)
