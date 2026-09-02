"""Checksum a Modbus RTU frame, and show why the result goes out backwards.

The Modbus RTU frame consists of:

    - Slave ID (1 byte)
    - PDU (Protocol Data Unit) (variable length)
    - CRC (2 bytes)

The CRC is calculated using the following polynomial:

    x^16 + x^15 + x^2 + 1

which is applied in its reversed form, 0xA001, because the algorithm shifts
right. The CRC is initialized to 0xFFFF and covers the slave id and the PDU,
everything ahead of the checksum itself.

Each byte is XORed into the low byte of the running value, and then for each
of its eight bits:

    - If the least significant bit is 1, the CRC is shifted to the right by 1
        bit and XORed with the polynomial.
    - If the least significant bit is 0, the CRC is shifted to the right by 1
        bit.

The result is a 16-bit integer, and it goes onto the wire low byte first --
the one place in Modbus where a multi-byte field is not big-endian. Getting
that order wrong produces frames that round-trip against your own decoder and
are rejected by every device. For more information on the CRC calculation,
refer to the wikipedia page:

    - https://en.wikipedia.org/wiki/Modbus#CRC16-CCITT

Each frame below is compared against a complete frame written out from
outside this library, checksum bytes included, so the walkthrough disagrees
when the codec changes rather than following it. The comparison is against
the bytes rather than the 16-bit value on purpose: a value matches whichever
order it is later packed in, so checking only the number would agree with the
byte-swapped frame every device rejects.
"""

import struct
import sys

from pyomb.packets import CRC_FMT, calc_crc16

# Complete RTU frames, as printed by crccalc.com and by the reference
# implementation in the Modbus over Serial Line specification. Each is the
# slave id, the PDU, and the two checksum bytes in the order they are sent.
# Written out here rather than computed, so a change to the codec breaks the
# comparison instead of moving it with it.
PUBLISHED = (
    # Read holding registers, slave 17, two registers from address 0.
    "11 03 00 00 00 02 c6 9b",
    # Read input registers, slave 1, one register returning 0xFFFF.
    "01 04 02 ff ff b8 80",
)

# The checksum occupies the last two bytes of a frame; everything ahead of it
# is what the checksum covers.
CRC_SIZE = 2


def walk_through(published: str) -> None:
    """Print one frame's checksum, and raise if it is not the published one.

    Args:
        published (str): A complete RTU frame as spaced hex, including its
            two checksum bytes.

    Raises:
        ValueError: If the frame this library builds differs from the
            published one.
    """
    frame = bytes.fromhex(published)
    payload = frame[:-CRC_SIZE]

    crc = calc_crc16(payload)

    # Packed through the same format string the serializer uses, so what
    # prints here is the byte order that reaches a device rather than a
    # second opinion about it.
    on_the_wire = struct.pack(CRC_FMT, crc)
    built = payload + on_the_wire

    print(f"payload    : {payload.hex(' ')}")
    print(f"crc value  : 0x{crc:04X}")
    print(f"on the wire: {on_the_wire.hex(' ')}")
    print(f"full frame : {built.hex(' ')}")
    print("")

    if built != frame:
        mismatch = f"built {built.hex(' ')}, published frame is {frame.hex(' ')}"
        raise ValueError(mismatch)


def main() -> None:
    """Check each published frame and print how its checksum is carried."""
    for published in PUBLISHED:
        walk_through(published)

    print(f"{len(PUBLISHED)} frames match their published bytes")


if __name__ == "__main__":
    # State the encoding rather than inheriting the console's, so what
    # this prints is what the reader sees on any machine.
    sys.stdout.reconfigure(encoding="utf-8")

    main()
