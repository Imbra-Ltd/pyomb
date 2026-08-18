import unittest
from pyomb.stream import ModbusTcpStream, ModbusFragmenter
from stub_socket import StubSocket


class TestModbusStream(unittest.TestCase):
    def test_initialization(self):

        # Create an instance of the mocked socket
        sock = StubSocket()

        # Test initialization
        stream = ModbusTcpStream(sock=sock, fragmenter=ModbusFragmenter(), frag_delay=0, frag_size=7, burst=False)

        # Test initialization
        self.assertEqual(stream.sock, sock)
        self.assertIsInstance(stream.fragmenter, ModbusFragmenter)
        self.assertEqual(stream.frag_delay, 0)
        self.assertEqual(stream.frag_size, 7)
        self.assertEqual(stream.burst, False)

    def test_send(self):

        sock = StubSocket()

        # Test message
        test_message = b"0123456789"

        # Test initialization
        stream = ModbusTcpStream(sock=sock, fragmenter=ModbusFragmenter(), frag_delay=0, frag_size=0, burst=False)

        # Test send without burst
        stream.send(test_message)

        data_sent = sock.sent_data[0]

        # Test the data sent
        self.assertEqual(data_sent, test_message)

        # Flush the socket
        sock.flush()

        # Set the fragment size
        stream.frag_size = 7

        # Test send
        stream.send(test_message)

        data_sent = sock.sent_data

        # Test the data sent
        expected = [b"0123456", b"789"]
        self.assertEqual(data_sent, expected)

    def test_receive(self):

        # Create a stub socket instance
        sock = StubSocket()

        test_message = sock.recv_data

        # Create the stream instance with no fragmentation
        stream = ModbusTcpStream(sock=sock, fragmenter=ModbusFragmenter(), frag_delay=0, frag_size=0, burst=False)

        # Test with no fragmentation
        received = stream.receive()

        # Test the received data
        self.assertEqual(received, test_message)

        # Reset the socket
        sock.reset()

        # Test with fragmentation
        stream.frag_size = 7

        # Test receive
        received = stream.receive()

        # Test the received data
        self.assertEqual(received, test_message)
