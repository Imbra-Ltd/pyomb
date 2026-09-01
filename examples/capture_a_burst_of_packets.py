"""Send several Modbus messages in one shot and capture them at the far end.

`ModbusTcpSender` drives a list of packets down a socket; `ModbusTcpReceiver`
reads whatever arrives on the other one and keeps it. Between them they are
how this library stress-tests a peer and how it records what a peer sent, and
neither is visible from the packet classes -- framing a request is arithmetic
you can read, driving a socket is not.

Both ends are held here rather than pointed at a device, so the file runs with
nothing installed but the project. A listener is opened on a port the
operating system picks, a second socket connects to it, and the accepted
connection is the receiving end. The README shows port 502, the registered
Modbus port a real device listens on; 0 asks for a free one instead, which is
what lets this file run without privileges on any machine.

The sender closes its socket when it is done. That is what ends the capture:
`run_once` reads messages until the peer goes away, so without the close it
would sit waiting for a fourth message that is never coming.
"""

import socket

from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusRequestFC3, ModbusTcpRequest
from pyomb.stream import ModbusTcpReceiver, ModbusTcpSender

# Seconds to wait on either socket. Bounded rather than blocking, so a
# failure here reports itself instead of hanging with nothing on the screen.
TIMEOUT = 10.0


def burst():
    """Build the packets to send, each with the header length it needs.

    Returns:
        list: The requests, in the order they go out.
    """
    packets = []

    for pdu in (
        ModbusRequestFC1(start_addr=0, quantity=1),
        ModbusRequestFC1(start_addr=8, quantity=16),
        ModbusRequestFC3(start_addr=0, quantity=2),
    ):
        # The length field counts the unit identifier plus the PDU. The sender
        # recomputes it before serializing, so this is what it will arrive as
        # rather than a value the example has to keep in step by hand.
        packets.append(ModbusTcpRequest(header=ModbusHeader(unit_id=1, length=len(pdu) + 1), pdu=pdu))

    return packets


def main() -> None:
    """Send a burst down one socket and capture it off the other."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    # Valid only once the listener is up, because that is when the operating
    # system has actually assigned the port.
    port = listener.getsockname()[1]
    print(f"listening on port {port}")

    sending = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sending.settimeout(TIMEOUT)

    try:
        sending.connect(("127.0.0.1", port))
        receiving, _ = listener.accept()
        receiving.settimeout(TIMEOUT)

        try:
            packets = burst()

            sender = ModbusTcpSender(sock=sending, packets=packets)
            sender.run_once()

            # Closing before the capture starts, so the reader reaches the end
            # of the stream rather than the end of the timeout. A real monitor
            # keeps the connection open and calls stop() instead.
            sending.close()

            receiver = ModbusTcpReceiver(sock=receiving)
            captured = receiver.run_once()

            print(f"sent {len(packets)}, captured {len(captured)}")

            for packet in captured:
                print(packet)

        finally:
            receiving.close()

    finally:
        sending.close()
        listener.close()


if __name__ == "__main__":
    main()
