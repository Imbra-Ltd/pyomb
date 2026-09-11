"""Exchange RTU frames over a port the caller opened, without a serial library.

`ModbusRtuStream` takes any open object with `read(size)` and `write(data)`:
pyserial's `Serial("COM3", 19200, parity="E", timeout=1.0)`, a socket's
`makefile("rwb", buffering=0)`, or the in-memory pair below. The library opens
no port itself, which is what lets it work with whichever serial library the
machine has.

Both ends are in this process, so nothing but the project need be installed.
The frames are published specification vectors, and the reply that comes back
is compared against its published bytes.
"""

import sys

from pyomb.adu import ModbusRtuRequest, ModbusRtuResponse
from pyomb.transport import ModbusRtuStream, RtuSide

# 11 03 00 6B 00 03 -- read three holding registers from 0x006B on slave 17,
# and the three registers coming back.
FC3_REQUEST = b"\x11\x03\x00\x6b\x00\x03\x76\x87"
FC3_RESPONSE = b"\x11\x03\x06\xae\x41\x56\x52\x43\x40\x49\xad"


class MemoryPort:
    """One end of an in-memory line: reads from one buffer, writes to another.

    read() hands back what is waiting up to size, and nothing once the buffer
    is empty -- which is what a real port does when its timeout elapses.
    """

    def __init__(self, inbox, outbox):
        """Bind the buffer this end reads from and the one it writes to."""
        self.inbox = inbox
        self.outbox = outbox

    def read(self, size):
        """Return what is waiting, up to size bytes, and nothing once empty."""
        chunk = bytes(self.inbox[:size])
        del self.inbox[:size]

        return chunk

    def write(self, data):
        """Append the bytes to the other end's inbox and report the count."""
        self.outbox.extend(data)

        return len(data)


def main() -> None:
    """Send a request down one end of the line and answer it from the other."""
    to_device = bytearray()
    to_master = bytearray()

    # The master reads responses; the device reads requests. Each side is told
    # which, because a function code alone does not say.
    master = ModbusRtuStream(port=MemoryPort(inbox=to_master, outbox=to_device), side=RtuSide.RESPONSE)
    device = ModbusRtuStream(port=MemoryPort(inbox=to_device, outbox=to_master), side=RtuSide.REQUEST)

    master.send(FC3_REQUEST)
    request = ModbusRtuRequest.deserialize(device.receive())
    print(f"device read : {request}")

    device.send(FC3_RESPONSE)
    reply = master.receive()
    print(f"master read : {ModbusRtuResponse.deserialize(reply)}")
    print(f"on the wire : {reply.hex(' ')}")

    # Printed first, so a wrong reply still shows what arrived. The raise is
    # what the examples job reads -- it checks exit status.
    if reply != FC3_RESPONSE:
        mismatch = f"read {reply.hex(' ')}, published {FC3_RESPONSE.hex(' ')}"
        raise ValueError(mismatch)

    print("the reply matches its published bytes")


if __name__ == "__main__":
    # State the encoding rather than inheriting the console's, so what
    # this prints is what the reader sees on any machine.
    sys.stdout.reconfigure(encoding="utf-8")

    main()
