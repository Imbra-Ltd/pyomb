"""Send several Modbus messages in one shot and capture them at the far end.

`ModbusTcpSender` drives a list of packets down a socket and
`ModbusTcpReceiver` keeps whatever arrives on the other. Framing a request is
arithmetic you can read; driving a socket is not.

Both ends are local, so nothing but the project need be installed. Port 0 asks
the operating system for a free port; a real device listens on 502.

The sender closes its socket when done, and that is what ends the capture --
`run_once` reads until the peer goes away. A real monitor keeps the connection
open and calls `stop()` instead.
"""

import socket
import sys

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
        # The length field counts the unit identifier plus the PDU, and the
        # sender recomputes it before serializing.
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
            # of the stream rather than the end of the timeout.
            sending.close()

            receiver = ModbusTcpReceiver(sock=receiving)
            captured = receiver.run_once()

            print(f"sent {len(packets)}, captured {len(captured)}")

            for packet in captured:
                print(packet)

            # Printed first, so a short capture still shows what arrived. The
            # raise is what the examples job reads -- it checks exit status.
            if len(captured) != len(packets):
                dropped = f"sent {len(packets)} packet(s), captured {len(captured)}"
                raise ValueError(dropped)

        finally:
            receiving.close()

    finally:
        sending.close()
        listener.close()


if __name__ == "__main__":
    # State the encoding rather than inheriting the console's, so what
    # this prints is what the reader sees on any machine.
    sys.stdout.reconfigure(encoding="utf-8")

    main()
