"""Ask a packet which constraints it breaks, then put it on the wire anyway.

The check reports and never refuses. `serialize()` calls neither
`violations()` nor `validate()`, deliberately: emitting a frame a device
rejects is how this library grades the device, so a codec that quietly
corrected its operator would be useless for the job it exists to do.

The bound crossed below is not this library's opinion. The Modbus Application
Protocol v1.1b3 caps Read Holding Registers at 125 registers per request, so
125 conforms and 126 is one register past the edge.

Nothing here opens a socket: the codec does not import one.
"""

import sys

from pyomb.errors import ModbusPacketError
from pyomb.packets import ModbusRequestFC3


def main() -> None:
    """Report what two read-holding-registers requests break, and send one."""
    conforming = ModbusRequestFC3(start_addr=0, quantity=125)
    print(f"quantity=125 reports {len(conforming.violations())} violations")

    over_the_bound = ModbusRequestFC3(start_addr=0, quantity=126)

    # A finding carries the rule's identity, so a harness asserts which bound
    # was crossed rather than matching prose that may be reworded.
    for finding in over_the_bound.violations():
        print(finding)
        print(f"  field={finding.field} value={finding.value}")

    # The frame goes out regardless, and the last two bytes are the quantity
    # the specification does not allow, sitting on the wire.
    print(f"serialized anyway: {over_the_bound.serialize().hex()}")

    # validate() is the same check with the opposite manners -- it raises
    # where violations() returns. Neither is reached by serialize().
    try:
        over_the_bound.validate()
    except ModbusPacketError as error:
        print(f"validate() raises: {error}")


if __name__ == "__main__":
    # State the encoding rather than inheriting the console's, so what
    # this prints is what the reader sees on any machine.
    sys.stdout.reconfigure(encoding="utf-8")

    main()
