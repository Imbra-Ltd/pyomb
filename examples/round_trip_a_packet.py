"""Serialize a packet, read it back, and check the two agree.

A round trip proves the codec is self-consistent. It proves nothing about the
wire, because both halves share whatever assumption either one got wrong -- so
this example ends by comparing the frame against a byte sequence written out by
hand from the specification, which is the half that would catch a shared
mistake.
"""

from pyomb.packets import ModbusHeader, ModbusRequestFC1, ModbusTcpRequest

# Function code 1, one coil from address 0, unit 1, transaction 0. Written out
# field by field rather than captured from this library's own output, so it
# disagrees when the codec changes rather than following it.
EXPECTED = bytes.fromhex(
    "0000"  # transaction identifier
    "0000"  # protocol identifier
    "0006"  # length: unit identifier plus PDU
    "01"  # unit identifier
    "01"  # function code 1, read coils
    "0000"  # start address
    "0001"  # quantity
)


def main() -> None:
    """Round-trip one request and compare the frame with the fixed vector."""
    pdu = ModbusRequestFC1(start_addr=0, quantity=1)
    header = ModbusHeader(unit_id=1, length=len(pdu) + 1)

    original = ModbusTcpRequest(header=header, pdu=pdu)
    frame = original.serialize()

    restored = ModbusTcpRequest.deserialize(frame)

    print(restored)
    print("round trip reproduces the frame:", restored.serialize() == frame)
    print("frame matches the written-out vector:", frame == EXPECTED)


if __name__ == "__main__":
    main()
