"""Send a request in pieces and reassemble the reply by its declared length.

This is the point of the transport. A Modbus frame does not arrive one frame
per recv(): a peer may split it however it likes, and the only thing that says
where a frame ends is the length field in its own header. Reading one recv()
and calling it a frame works on a quiet link and fails on a busy one.

`frag_size` forces the failure into the open. The request leaves in 8-byte
pieces, and the response is reassembled from however many pieces come back.

The server here is this project's own simulator, started in-process on a port
the operating system picks. The README shows port 502, which is the registered
Modbus port and what a real device listens on; 0 asks for a free one instead,
which is what lets this file run without privileges on any machine.
"""

import socket

from pyomb import OmbServerSim
from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest, ModbusTcpResponse
from pyomb.stream import ModbusTcpStream

# Seconds to wait for the listener and for the exchange. Bounded rather than
# blocking, so a failure here reports itself instead of hanging.
TIMEOUT = 10.0

NO_LISTENER = "the server never reached its accept loop"


def exchange(port: int) -> ModbusTcpResponse:
    """Send one fragmented request to a listening server and read the reply.

    Args:
        port (int) : The port the server is listening on

    Returns:
        ModbusTcpResponse : The reassembled response
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    sock.connect(("127.0.0.1", port))

    try:
        pdu = ModbusRequestFC1(start_addr=0, quantity=1)
        header = ModbusHeader(unit_id=1, length=len(pdu) + 1)
        request = ModbusTcpRequest(header=header, pdu=pdu)

        stream = ModbusTcpStream(sock=sock, frag_size=8)
        stream.send(request.serialize())

        # receive() reads the header, takes the declared length from it, then
        # keeps reading until exactly that many bytes have arrived.
        return ModbusTcpResponse.deserialize(stream.receive())

    finally:
        sock.close()


def main() -> None:
    """Start the simulator, exchange one fragmented frame, then stop it."""
    server = OmbServerSim(port=0)
    server.daemon = True
    server.start()

    if not server.startedEvent.wait(TIMEOUT):
        raise SystemExit(NO_LISTENER)

    # Valid only once the listener is up, because that is when the operating
    # system has actually assigned the port.
    print(f"server listening on port {server.port}")

    try:
        print(exchange(server.port))

    finally:
        server.stop()
        server.join(TIMEOUT)


if __name__ == "__main__":
    main()
