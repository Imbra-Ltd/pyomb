"""Checksum a Modbus RTU frame, and show why the result goes out backwards.

An RTU frame ends with a two-byte checksum, and it is the one multi-byte field
in Modbus sent low byte first. Get that order wrong and the frames still
round-trip against this library's own decoder while every device rejects them.

Each frame below is compared against a complete frame written out from a
published source, checksum bytes included, so this walkthrough disagrees when
the codec changes rather than following it. The comparison is on bytes and not
on the 16-bit value, which matches whichever order it is later packed in.

The algorithm is in the RTU checksum section of docs/PLAYBOOK.md.
"""

import struct
import sys

from pyomb.packets import CRC_FMT, calc_crc16

# Complete frames from crccalc.com and the Modbus over Serial Line reference
# implementation, written out rather than computed. See the module docstring.
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

    # The serializer's own format string, so this prints the byte order that
    # reaches a device rather than a second opinion about it.
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
