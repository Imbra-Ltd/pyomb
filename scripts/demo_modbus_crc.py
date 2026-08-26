"""
This script demonstrates how to checksum a Modbus RTU frame. The Modbus RTU
frame consists of:

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

"""

import struct
import sys

from pyomb.packets import CRC_FMT, calc_crc16


def demo(payload):
    """Print the checksum of one frame body as a value and as wire bytes."""

    crc = calc_crc16(payload)

    print("payload  : {0}".format(payload.hex(" ")))
    print("crc value: 0x{0:04X}".format(crc))
    print("on the wire: {0}".format(struct.pack(CRC_FMT, crc).hex(" ")))
    print("full frame: {0}".format((payload + struct.pack(CRC_FMT, crc)).hex(" ")))
    print("")


if __name__ == "__main__":
    # State the encoding rather than inheriting the console's, so what this
    # prints is what the reader sees on any machine.
    sys.stdout.reconfigure(encoding="utf-8")

    # Read holding registers, slave 17, two registers from address 0. The
    # published checksum for this frame ends C6 9B.
    demo(bytes.fromhex("110300000002"))

    # Read input registers, slave 1, one register returning 0xFFFF. The
    # published checksum for this frame ends B8 80.
    demo(bytes.fromhex("010402FFFF"))
