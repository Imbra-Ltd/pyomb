# coding: utf-8
"""
There are several specific :class:`Exception` classes to allow user code to
react to specific scenarios related to the Open Modbus Protocol.

Exception (Python standard library)
 +-- ...
 +-- ModbusBaseError
     +-- ModbusNetworkError
     +-- ModbusPacketError
     +-- ModbusProtocolError
        +-- ModbusIllegalFunction
        +-- ModbusIllegalDataAddress
        +-- ModbusIllegalDataValue
        +-- ModbusSlaveDeviceFailure
        +-- ModbusAcknowledge
        +-- ModbusSlaveDeviceBusy
        +-- ModbusMemoryParityError
        +-- ModbusGatewayPathUnavailable
        +-- ModbusGatewayTargetDeviceFailedToRespond
"""

from __future__ import print_function
from __future__ import unicode_literals

# Recommendations accodrding to chatGPT
# TODO: Reduce redundancy in the error messages
# TODO: Improve unicode string handling in the error messages
# TODO: Improve the examples in the docstrings with more realistic scenarios
# TODO: Use defines, if provided, for the error codes in the error messages


class ModbusBaseError(Exception):
    """Generic Modbus error

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

    def __init__(self, message, extended_info=""):
        """Initialize the ModbusError object"""

        # Set the error message and extended information
        self.message = message
        self.extended_info = extended_info

    def __str__(self):

        # Add the extended information if available
        if self.extended_info:
            result = self.message + " (" + self.extended_info + ")"

        # Otherwise, just return the error message
        else:
            result = self.message

        # Return the formatted error message
        return result


class ModbusProtocolError(ModbusBaseError):
    """Generic Modbus protocol error

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

    def __init__(self, message, error_code):
        """Initialize the ModbusProtocolError object"""

        # Define the error message and code
        error_code = "Protocol Error Code 0x{0:X}".format(error_code)

        # Call the parent class constructor
        super(ModbusProtocolError, self).__init__(message=message, extended_info=error_code)


class ModbusIllegalFunction(ModbusProtocolError):
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
            raise ModbusIllegalFunction(0x01)

        # Catch the error and print the error message
        except ModbusIllegalFunction as e:
            print("Modbus illegal function error: {0}".format(e))
    """

    def __init__(self, fc):
        """Initialize the ModbusIllegalFunction object"""

        # Call the parent class constructor
        super(ModbusIllegalFunction, self).__init__(
            message="The function code {0} is not valid".format(fc), error_code=0x01
        )


class ModbusIllegalDataAddress(ModbusProtocolError):
    """The data address is not valid.

    The data address received in the query is not an allowable address for the
    server (or slave). More specifically, the combination of reference number
    and transfer length is invalid. For a controller with 100 registers, the
    PDU addresses the first register as 0, and the last one as 99. If a request
    is submitted with a starting register address of 96 and a quantity of
    registers of 4, then this request will successfully operate (address-wise
    at least) on registers 96, 97, 98, 99. If a request is submitted with a
    starting register address of 96 and a quantity of registers of 5, then
    this request will fail with Exception Code 0x02 "Illegal Data Address"
    since it attempts to operate on registers 96, 97, 98, 99 and 100, and
    there is no register with address 100.

    Args:
        address (int)    :   The data address that generated the error


    Example:
        try:
            # Code that may raise Modbus illegal data address errors
            raise ModbusIllegalDataAddress(0x02)

        # Catch the error and print the error message
        except ModbusIllegalDataAddress as e:
            print("Modbus illegal data address error: {0}".format(e))
    """

    def __init__(self, address):
        super(ModbusIllegalDataAddress, self).__init__(
            message="The data address {0} is not valid".format(address), error_code=0x02
        )


class ModbusIllegalDataValue(ModbusProtocolError):
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
            raise ModbusIllegalDataValue(0x03)

        # Catch the error and print the error message
        except ModbusIllegalDataValue as e:
            print("Modbus illegal data value error: {0}".format(e))
    """

    def __init__(self, data_value):
        super(ModbusIllegalDataValue, self).__init__(
            message="The data value {0} is not valid".format(data_value), error_code=0x03
        )


class ModbusSlaveDeviceFailure(ModbusProtocolError):
    """The slave device failed to perform the requested action.

    An unrecoverable error occurred while the server (or slave) was attempting
    to perform the requested action.

    Example:
        try:
            # Code that may raise Modbus slave device failure errors
            raise ModbusSlaveDeviceFailure()

        # Catch the error and print the error message
        except ModbusSlaveDeviceFailure as e:
            print("Modbus slave device failure error: {0}".format(e))
    """

    def __init__(self):
        super(ModbusSlaveDeviceFailure, self).__init__(
            message="The slave device failed to perform the requested action", error_code=0x04
        )


class ModbusAcknowledge(ModbusProtocolError):
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
            raise ModbusAcknowledge()

        # Catch the error and print the error message
        except ModbusAcknowledge as e:
            print("Modbus slave device failure error: {0}".format(e))
    """

    def __init__(self):
        super(ModbusAcknowledge, self).__init__(
            message="The slave device acknowledged the request but is processing it", error_code=0x05
        )


class ModbusSlaveDeviceBusy(ModbusProtocolError):
    """The slave device is busy processing a long-duration command.

    Specialized use in conjunction with programming commands. The server
    (or slave) is engaged in processing a long-duration program command. The
    client (or master) should retransmit the message later when the server
    (or slave) is free.

    Example:
        try:
            # Code that may raise Modbus slave device busy errors
            raise ModbusSlaveDeviceBusy()

        # Catch the error and print the error message
        except ModbusSlaveDeviceBusy as e:
            print("Modbus slave device busy error: {0}".format(e))
    """

    def __init__(self):
        super(ModbusSlaveDeviceBusy, self).__init__(
            message="The slave device is busy processing a long-duration command", error_code=0x06
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

    def __init__(self):
        super(ModbusMemoryParityError, self).__init__(
            message="The slave device detected a parity error in memory", error_code=0x08
        )


class ModbusGatewayPathUnavailable(ModbusProtocolError):
    """The gateway could not find the path to the target device.

    Specialized use in conjunction with gateways, indicates that the gateway
    was unable to allocate an internal communication path from the input
    port to the output port for processing the request. Usually means that the
    gateway is misconfigured or overloaded.

    Example:
        try:
            # Code that may raise Modbus gateway path unavailable errors
            raise ModbusGatewayPathUnavailable()

        # Catch the error and print the error message
        except ModbusGatewayPathUnavailable as e:
            print("Modbus gateway path unavailable error: {0}".format(e))
    """

    def __init__(self):
        super(ModbusGatewayPathUnavailable, self).__init__(
            message="The gateway could not find the path to the target device", error_code=0x0A
        )


class ModbusGatewayTargetDeviceFailedToRespond(ModbusProtocolError):
    """The gateway received no response from the target device.

    Specialized use in conjunction with gateways, indicates that no response
    was obtained from the target device. Usually means that the device is
    not present on the network.

    Example:
        try:
            # Code that may raise an error
            raise ModbusGatewayTargetDeviceFailedToRespond()

        # Catch the error and print the error message
        except ModbusGatewayTargetDeviceFailedToRespond as e:
            print("Modbus Error: {0}".format(e))
    """

    def __init__(self):
        super(ModbusGatewayTargetDeviceFailedToRespond, self).__init__(
            message="The gateway received no response from the target device", error_code=0x0B
        )


class ModbusNetworkError(ModbusBaseError):
    """Generic Modbus network error

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

    def __init__(self, message, extended_info=""):
        """Initialize the ModbusNetworkError object"""

        # Call the parent class constructor
        super(ModbusNetworkError, self).__init__(message=message, extended_info=extended_info)


class ModbusPacketError(ModbusBaseError):
    """Generic Modbus Packet Error

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

    def __init__(self, message, extended_info=""):
        """Initialize the ModbusPacketError object"""

        # Call the parent class constructor
        super(ModbusPacketError, self).__init__(message=message, extended_info=extended_info)
