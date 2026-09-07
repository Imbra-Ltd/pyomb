"""Each exception class renders the code the specification assigns it.

The vector below is typed from the MODBUS Exception Codes table of the Modbus
Application Protocol v1.1b3, not read from this library. A constant imported
from the package under test would agree with a wrong value as readily as with
a right one, which is the failure a fixed vector exists to catch.
"""

import inspect
import unittest

from pyomb import errors
from pyomb.errors import (
    ModbusAcknowledgeError,
    ModbusGatewayPathUnavailableError,
    ModbusGatewayTargetDeviceFailedToRespondError,
    ModbusIllegalDataAddressError,
    ModbusIllegalDataValueError,
    ModbusIllegalFunctionError,
    ModbusMemoryParityError,
    ModbusProtocolError,
    ModbusSlaveDeviceBusyError,
    ModbusSlaveDeviceFailureError,
)

# Class, the arguments it needs, and the code the specification table gives it.
# The three that take an argument name the field the peer refused.
VECTOR = (
    (ModbusIllegalFunctionError, (0x2B,), 0x01),
    (ModbusIllegalDataAddressError, (0x0064,), 0x02),
    (ModbusIllegalDataValueError, (0x0800,), 0x03),
    (ModbusSlaveDeviceFailureError, (), 0x04),
    (ModbusAcknowledgeError, (), 0x05),
    (ModbusSlaveDeviceBusyError, (), 0x06),
    (ModbusMemoryParityError, (), 0x08),
    (ModbusGatewayPathUnavailableError, (), 0x0A),
    (ModbusGatewayTargetDeviceFailedToRespondError, (), 0x0B),
)

# The table lists nine codes: 01 to 06, 08, 0A and 0B. The count is a floor
# rather than a length, so a vector that shrinks fails here.
CODES_IN_THE_TABLE = 9


def rendered(error):
    """Read the code an exception renders, without reaching into the object.

    Args:
        error (ModbusProtocolError) : The exception to read

    Returns:
        str : The extended information the exception appends to its message
    """

    return error.extended_info


class ExceptionCodesMatchTheSpecification(unittest.TestCase):
    """Pins every protocol exception to its published code."""

    def test_each_class_renders_the_code_the_table_assigns_it(self):
        """The rendered code is the specification's, not the library's."""

        wrong = []

        for cls, arguments, code in VECTOR:
            expected = f"Protocol Error Code 0x{code:X}"
            found = rendered(cls(*arguments))

            if found != expected:
                wrong.append(f"{cls.__name__}: {found!r} where the table gives {expected!r}")

        self.assertEqual(
            wrong,
            [],
            "exception classes rendering a code the Modbus Application Protocol v1.1b3 table "
            "does not assign them:\n  " + "\n  ".join(wrong),
        )

    def test_the_vector_covers_every_protocol_exception(self):
        """A class added later is checked, rather than silently unread."""

        declared = {
            member
            for _, member in inspect.getmembers(errors, inspect.isclass)
            if issubclass(member, ModbusProtocolError) and member is not ModbusProtocolError
        }

        self.assertGreaterEqual(
            len(declared),
            CODES_IN_THE_TABLE,
            f"the enumeration found {len(declared)} protocol exception class(es) where the "
            f"specification table carries {CODES_IN_THE_TABLE}, so the assertion below would "
            "pass having read almost nothing.",
        )

        unchecked = sorted(cls.__name__ for cls in declared - {row[0] for row in VECTOR})

        self.assertEqual(
            unchecked,
            [],
            "protocol exception classes carrying no row in the specification vector, so nothing "
            "asserts the code they render:\n  " + "\n  ".join(unchecked),
        )


if __name__ == "__main__":
    unittest.main()
