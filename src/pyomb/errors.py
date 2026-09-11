"""One exception class per scenario a caller may want to react to.

A caller catches the branch it cares about rather than matching on a message.

Three branches sit under ModbusBaseError, separating where the failure came
from: the network, a frame that will not parse, and a peer answering with a
Modbus exception code. Everything under ModbusProtocolError is one of those
codes.

A code appears twice by design: as a named constant where a class raises it,
and as a number in prose where the specification publishes it.

The tree is in the exception hierarchy section of docs/PLAYBOOK.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyomb.defines import (
    OMB_EXCEPTION_ACKNOWLEDGE,
    OMB_EXCEPTION_GATEWAY_PATH_UNAVAILABLE,
    OMB_EXCEPTION_GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND,
    OMB_EXCEPTION_ILLEGAL_DATA_ADDRESS,
    OMB_EXCEPTION_ILLEGAL_DATA_VALUE,
    OMB_EXCEPTION_ILLEGAL_FUNCTION,
    OMB_EXCEPTION_MEMORY_PARITY_ERROR,
    OMB_EXCEPTION_SLAVE_DEVICE_BUSY,
    OMB_EXCEPTION_SLAVE_DEVICE_FAILURE,
)

# The header type is needed for the annotation and not at runtime. Importing
# it for real would close a cycle, since pyomb.adu imports this module.
if TYPE_CHECKING:
    from pyomb.adu import ModbusHeader


class ModbusBaseError(Exception):
    """Generic Modbus error.

    The base class for all Modbus errors. This class should not be used
    directly to raise exceptions. Instead, use one of the more specific
    error classes.

    The main use of this class is to catch all Modbus errors in a single
    except block.

    Args:
        message         (unicode)   : A description of the error.
        extended_info   (unicode)   : Additional information (e.g. error code)

    Example:
        try:
            # code that may raise Modbus errors
        except ModbusError as e:
            print("Modbus error: {0}".format(e))

    """

    def __init__(self, message: str, extended_info: str = "") -> None:
        """Record the message and the extended information beside it."""
        self.message = message
        self.extended_info = extended_info

    def __str__(self) -> str:
        """The message, with the extended information appended when present."""
        if self.extended_info:
            return self.message + " (" + self.extended_info + ")"

        return self.message


class ModbusProtocolError(ModbusBaseError):
    """Generic Modbus protocol error.

    This error is raised when the server (or slave) returns an error code in
    response to a query. The error code is a single byte that indicates the
    type of error that occurred. The error code is described in the Modbus
    specification.

    Args:
        message     (unicode)   : A description of the error.
        error_code  (int)       : The error code returned by the server.

    Example:
        try:
            # Code that may raise Modbus protocol errors
            raise ModbusProtocolError("The server returned an error", 0x01)

        # Catch the error and print the error message
        except ModbusProtocolError as e:
            print("Modbus protocol error: {0}".format(e))

    """

    def __init__(self, message: str, error_code: int) -> None:
        """Render the exception code the peer returned into the message."""
        super().__init__(
            message=message,
            extended_info=f"Protocol Error Code 0x{error_code:X}",
        )


class ModbusIllegalFunctionError(ModbusProtocolError):
    """The function code is not valid.

    The function code received in the query is not an allowable action for the
    server (or slave). This may be because the function code is only applicable
    to newer devices, and was not implemented in the unit selected. It could
    also indicate that the server (or slave) is in the wrong state to process
    a request of this type, for example because it is unconfigured and is being
    asked to return register values.

    Args:
        fc (int)    :   The function code that generated the error


    Example:
        try:
            # Code that may raise Modbus illegal function errors
            raise ModbusIllegalFunctionError(0x01)

        # Catch the error and print the error message
        except ModbusIllegalFunctionError as e:
            print("Modbus illegal function error: {0}".format(e))
    """

    def __init__(self, fc: object) -> None:
        """Name the function code the peer refused."""
        super().__init__(message=f"The function code {fc} is not valid", error_code=OMB_EXCEPTION_ILLEGAL_FUNCTION)


class ModbusIllegalDataAddressError(ModbusProtocolError):
    """The data address is not valid.

    It is the combination of address and length that has to be allowable, not
    the address alone. A controller with 100 registers numbers them 0 to 99, so
    a request for 4 registers from address 96 reaches 96 through 99 and
    succeeds, while a request for 5 from the same address reaches 100 and
    fails with exception code 0x02.

    Args:
        address (int)    :   The data address that generated the error


    Example:
        try:
            # Code that may raise Modbus illegal data address errors
            raise ModbusIllegalDataAddressError(0x02)

        # Catch the error and print the error message
        except ModbusIllegalDataAddressError as e:
            print("Modbus illegal data address error: {0}".format(e))
    """

    def __init__(self, address: object) -> None:
        """Name the address, or address-and-length pair, that was refused."""
        super().__init__(
            message=f"The data address {address} is not valid", error_code=OMB_EXCEPTION_ILLEGAL_DATA_ADDRESS
        )


class ModbusIllegalDataValueError(ModbusProtocolError):
    """The data value is not valid.

    A value contained in the query data field is not an allowable value for
    server (or slave). This indicates a fault in the structure of the remainder
    of a complex request, such as that the implied length is incorrect. It
    specifically does NOT mean that a data item submitted for storage in a
    register has a value outside the expectation of the application program,
    since the MODBUS protocol is unaware of the significance of any particular
    value of any particular register.

    Args:
        data_value (int)    :   The data value that generated the error

    Example:
        try:
            # Code that may raise Modbus illegal data value errors
            raise ModbusIllegalDataValueError(0x03)

        # Catch the error and print the error message
        except ModbusIllegalDataValueError as e:
            print("Modbus illegal data value error: {0}".format(e))
    """

    def __init__(self, data_value: object) -> None:
        """Name the value the peer refused."""
        super().__init__(
            message=f"The data value {data_value} is not valid", error_code=OMB_EXCEPTION_ILLEGAL_DATA_VALUE
        )


class ModbusSlaveDeviceFailureError(ModbusProtocolError):
    """The slave device failed to perform the requested action.

    An unrecoverable error occurred while the server (or slave) was attempting
    to perform the requested action.

    Example:
        try:
            # Code that may raise Modbus slave device failure errors
            raise ModbusSlaveDeviceFailureError()

        # Catch the error and print the error message
        except ModbusSlaveDeviceFailureError as e:
            print("Modbus slave device failure error: {0}".format(e))
    """

    def __init__(self) -> None:
        """Report exception code 0x04, an unrecoverable failure on the peer."""
        super().__init__(
            message="The slave device failed to perform the requested action",
            error_code=OMB_EXCEPTION_SLAVE_DEVICE_FAILURE,
        )


class ModbusAcknowledgeError(ModbusProtocolError):
    """The slave device acknowledged the request but is processing it.

    Specialized use in conjunction with programming commands.

    The server (or slave) has accepted the request and is processing it, but a
    long duration of time will be required to do so. This response is returned
    to prevent a timeout error from occurring in the client (or master). The
    client (or master) can next issue a Poll Program Complete message to
    determine if processing is completed.

    Example:
        try:
            # Code that may raise Modbus slave device failure errors
            raise ModbusAcknowledgeError()

        # Catch the error and print the error message
        except ModbusAcknowledgeError as e:
            print("Modbus slave device failure error: {0}".format(e))
    """

    def __init__(self) -> None:
        """Report exception code 0x05, a request accepted and still running."""
        super().__init__(
            message="The slave device acknowledged the request but is processing it",
            error_code=OMB_EXCEPTION_ACKNOWLEDGE,
        )


class ModbusSlaveDeviceBusyError(ModbusProtocolError):
    """The slave device is busy processing a long-duration command.

    Specialized use in conjunction with programming commands. The server
    (or slave) is engaged in processing a long-duration program command. The
    client (or master) should retransmit the message later when the server
    (or slave) is free.

    Example:
        try:
            # Code that may raise Modbus slave device busy errors
            raise ModbusSlaveDeviceBusyError()

        # Catch the error and print the error message
        except ModbusSlaveDeviceBusyError as e:
            print("Modbus slave device busy error: {0}".format(e))
    """

    def __init__(self) -> None:
        """Report exception code 0x06, a peer that wants the request retried."""
        super().__init__(
            message="The slave device is busy processing a long-duration command",
            error_code=OMB_EXCEPTION_SLAVE_DEVICE_BUSY,
        )


class ModbusMemoryParityError(ModbusProtocolError):
    """The slave device detected a parity error in memory.

    Specialized use in conjunction with function codes 20 and 21 and reference
    type 6, to indicate that the extended file area failed to pass a consistency
    check.

    The server (or slave) attempted to read record file, but detected a parity
    error in the memory. The client (or master) can retry the request, but
    service may be required on the server (or slave) device.

    Example:
        try:
            # Code that may raise Modbus memory parity errors
            raise ModbusMemoryParityError()

        # Catch the error and print the error message
        except ModbusMemoryParityError as e:
            print("Modbus memory parity error: {0}".format(e))
    """

    def __init__(self) -> None:
        """Report exception code 0x08, a consistency check the peer failed."""
        super().__init__(
            message="The slave device detected a parity error in memory", error_code=OMB_EXCEPTION_MEMORY_PARITY_ERROR
        )


class ModbusGatewayPathUnavailableError(ModbusProtocolError):
    """The gateway could not find the path to the target device.

    Specialized use in conjunction with gateways, indicates that the gateway
    was unable to allocate an internal communication path from the input
    port to the output port for processing the request. Usually means that the
    gateway is misconfigured or overloaded.

    Example:
        try:
            # Code that may raise Modbus gateway path unavailable errors
            raise ModbusGatewayPathUnavailableError()

        # Catch the error and print the error message
        except ModbusGatewayPathUnavailableError as e:
            print("Modbus gateway path unavailable error: {0}".format(e))
    """

    def __init__(self) -> None:
        """Report exception code 0x0A, a gateway with no path to allocate."""
        super().__init__(
            message="The gateway could not find the path to the target device",
            error_code=OMB_EXCEPTION_GATEWAY_PATH_UNAVAILABLE,
        )


class ModbusGatewayTargetDeviceFailedToRespondError(ModbusProtocolError):
    """The gateway received no response from the target device.

    Specialized use in conjunction with gateways, indicates that no response
    was obtained from the target device. Usually means that the device is
    not present on the network.

    Example:
        try:
            # Code that may raise an error
            raise ModbusGatewayTargetDeviceFailedToRespondError()

        # Catch the error and print the error message
        except ModbusGatewayTargetDeviceFailedToRespondError as e:
            print("Modbus Error: {0}".format(e))
    """

    def __init__(self) -> None:
        """Report exception code 0x0B, a target that never answered the gateway."""
        super().__init__(
            message="The gateway received no response from the target device",
            error_code=OMB_EXCEPTION_GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND,
        )


class ModbusNetworkError(ModbusBaseError):
    """Generic Modbus network error.

    Possible causes of this error include:

    - Network timeout (no response from the server)
    - Network congestion (e.g. too many requests)
    - TCP handshake error (e.g. connection refused)
    - TLS/SSL handshake error (e.g. certificate validation failure)

    Args:
        message         (unicode)   : A description of the error.
        extended_info   (unicode)   : Additional information (e.g. error code)

    Example:
        try:
            # Code that may raise Modbus network errors
            raise ModbusNetworkError("Test network error")

        # Catch the error and print the error message
        except ModbusNetworkError as e:
            print("Modbus network error: {0}".format(e))
    """

    def __init__(self, message: str, extended_info: str = "") -> None:
        """Forward the caller's message and extended information unchanged."""
        super().__init__(message=message, extended_info=extended_info)


class ModbusTimeoutError(ModbusNetworkError):
    """Nothing arrived before the port's timeout elapsed.

    Raised by a stream over a serial port when a read returns no bytes at
    all. A serial line never closes, so silence is the only way a peer that
    is absent, powered off or addressed wrongly shows up. Catch it apart from
    its parent to retry a request that was never answered without also
    retrying a port that failed.

    Args:
        message         (unicode)   : A description of the error.
        extended_info   (unicode)   : Additional information (e.g. the wait)

    Example:
        try:
            frame = stream.receive()

        # The peer never answered; the port itself is fine.
        except ModbusTimeoutError as e:
            print("Modbus timeout: {0}".format(e))
    """

    def __init__(self, message: str, extended_info: str = "") -> None:
        """Forward the caller's message and extended information unchanged."""
        super().__init__(message=message, extended_info=extended_info)


class ModbusPacketError(ModbusBaseError):
    """Generic Modbus packet error.

    Possible causes of this error include:

    - Incorrect packet length (too short or too long)
    - Malformed packet (e.g. missing header or CRC)
    - Invalid packet data (e.g. incorrect function code)
    - Incorrect packet structure (e.g. missing or extra fields)

    Args:
        message         (unicode)   : A description of the error.
        extended_info   (unicode)   : Additional information (e.g. error code)

    Example:
        try:
            # Code that may raise Modbus packet errors
            raise ModbusPacketError("Test packet error")

        # Catch the error and print the error message
        except ModbusPacketError as e:
            print("Modbus packet error: {0}".format(e))
    """

    def __init__(self, message: str, extended_info: str = "") -> None:
        """Forward the caller's message and extended information unchanged."""
        super().__init__(message=message, extended_info=extended_info)


class ModbusPduParseError(ModbusPacketError):
    """A PDU that would not parse, behind an MBAP header that did.

    The header carries the transaction, protocol and unit identifiers a
    response has to echo, so a caller holding one of these can answer the peer
    with an exception response instead of dropping it. A plain
    ModbusPacketError says only that the frame is unusable, which is the right
    answer when the header itself is unreadable or its length field
    contradicts the bytes received.

    Args:
        message         (unicode)       : A description of the error.
        header          (ModbusHeader)  : The header the response echoes.
        fc              (int)           : The function code the request carried.
        extended_info   (unicode)       : Additional information.

    Example:
        try:
            request = ModbusTcpRequest.deserialize(stream)

        # The header survived, so the peer can be told what was wrong.
        except ModbusPduParseError as e:
            reply = ModbusError(fc=e.fc, exc_code=OMB_EXCEPTION_ILLEGAL_DATA_VALUE)
            print(e.header.trans_id)
    """

    def __init__(self, message: str, header: ModbusHeader, fc: int, extended_info: str = "") -> None:
        """Record the header and function code beside the caller's message."""
        self.header = header
        self.fc = fc

        super().__init__(message=message, extended_info=extended_info)


class ModbusModeError(ModbusBaseError):
    """The operation is not valid in the component's current mode.

    A component that owns a resource refuses the operations that would hand
    that resource to a caller. Nothing reached the wire, so this is neither a
    protocol failure nor a network one: it says the caller and the component
    disagree about which of them is driving.

    Possible causes of this error include:

    - Accepting a connection on a server that processes connections itself
    - Driving a component that has already been handed to something else

    Args:
        message         (unicode)   : A description of the error.
        extended_info   (unicode)   : Additional information (e.g. the mode)

    Example:
        try:
            # Code that may raise Modbus mode errors
            raise ModbusModeError("Test mode error")

        # Catch the error and print the error message
        except ModbusModeError as e:
            print("Modbus mode error: {0}".format(e))
    """

    def __init__(self, message: str, extended_info: str = "") -> None:
        """Forward the caller's message and extended information unchanged."""
        super().__init__(message=message, extended_info=extended_info)
