"""Build a Modbus TCP request and read the frame it puts on the wire.

The smallest thing this library does, and the one to reach for when checking a
frame against the specification by eye. Nothing here opens a socket: the codec
does not import one, so a frame can be built and inspected with no peer at all.

The frame below is function code 1, read coils, one coil from address 0. Read
it in order: transaction identifier, protocol identifier, length, unit
identifier, then the PDU.
"""

import sys

from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest


def main() -> None:
    """Serialize one read-coils request and print it as hex."""
    pdu = ModbusRequestFC1(start_addr=0, quantity=1)

    # The length field counts the unit identifier plus the PDU, not the whole
    # frame. Wrong here means a frame this library reads and a device rejects.
    header = ModbusHeader(unit_id=1, length=len(pdu) + 1)

    packet = ModbusTcpRequest(header=header, pdu=pdu)
    frame = packet.serialize()

    print(frame.hex())
    print(f"{len(frame)} bytes")


if __name__ == "__main__":
    # State the encoding rather than inheriting the console's, so what
    # this prints is what the reader sees on any machine.
    sys.stdout.reconfigure(encoding="utf-8")

    main()
