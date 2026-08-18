from pyomb.stream import ModbusTcpSender, ModbusTcpReceiver
from pyomb.packets import ModbusTcpPacket, ModbusHeader, ModbusPdu
from pyomb.logger import Logger
import socket
import threading


log = Logger("Testing stream module")


class SimpleTest(object):
    SENT_DATA = None
    RCVD_DATA = None
    FRAG_SIZE = 0

    @staticmethod
    def run_server():
        """Prepares and starts the server to receive Modbus messages."""

        # Make the server socket and wait for SYNC requests
        log.info("Binding the server socket...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 502))

        # Start listening for incoming connections
        log.info("Server listening on {0}:{1}".format("localhost", 502))
        sock.listen(1)

        # Accept the incoming connection
        log.info("Accepting the incoming connection...")
        conn, addr = sock.accept()

        # Start the socket server-client communication
        log.info("TCP connection established. Start the receiver...")
        received_data = ModbusTcpReceiver(conn).run_once()

        # Stop the receiver
        log.info("Stopping the receiver...")
        ModbusTcpReceiver(conn).stop()

        # Close the socket
        log.info("Closing the receiver socket...")

        # Set the received data
        SimpleTest.RCVD_DATA = received_data

    @classmethod
    def run_client(cls):
        """Starts the client to send Modbus messages"""

        # Connect to the remote machine
        log.info("Connecting to the remote machine...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("localhost", 502))

        requests = [
            # FC=15, starting_address=1, quantity=3, byte_count=2, data=b'\x00\x01\x00\x02'
            ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=15, data=(0, 1, 0, 3, 2, 0, 1))),
            # FC1, starting_address=1, quantity=3
            ModbusTcpPacket(ModbusHeader(unit_id=1), ModbusPdu(fc=1, data=(0, 1, 0, 3))),
        ]

        # Create the sender instance
        sender = ModbusTcpSender(sock=sock, packets=requests)

        # Get the constructed packets
        SimpleTest.SENT_DATA = sender.packets

        # Start the sender
        log.info("Starting the sender...")
        sender.run_once()

        # Stop the sender
        log.info("Stopping the sender...")
        sender.stop()

        # Close the socket
        log.info("Closing the sender socket...")
        sock.close()


if __name__ == "__main__":
    # Start the server thread
    server = threading.Thread(target=SimpleTest().run_server)
    server.start()

    # Start the client thread
    client = threading.Thread(target=SimpleTest().run_client)
    client.start()

    # Wait for the threads to finish
    server.join()
    client.join()

    # Print the sent and received data
    data_rcvd = SimpleTest.RCVD_DATA
    data_sent = SimpleTest.SENT_DATA

    print("Data sent:")
    for i in data_sent:
        print(i)

    print("Data received:")
    for i in data_rcvd:
        print(i)

    if data_rcvd == data_sent:
        log.info("Test PASSED")
    else:
        log.info("Test FAILED")
