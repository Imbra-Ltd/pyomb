# encoding: utf-8
"""Modbus Packet Classes.

This module contains the classes for the Modbus Packets following the original
Modbus Application Protocol Specification. The module supports both Modbus TCP
TCP and Modbus RTU messages.

The user is free to create custom Modbus PDU classes by subclassing the
ModbusPdu class and registering the new class with the ModbusPduParser class.
The user must provide the format string for the PDU, the function code and
the PDU-ID.

The PDU-Identifier (PDU ID) is used to register the PDU class with the PDU
parser. Requests have a PDU-ID in the range 0x0001 to 0x7FFF, while responses
have a PDU ID in the range 0x8001 to 0xFFFF. The error PDU has the PDU-ID
0x8000.
"""

from __future__ import division, print_function

import struct
from abc import ABCMeta, abstractmethod
from typing import ClassVar

from .errors import ModbusPacketError

################################################################################
# ABSTRACT CLASSES
################################################################################


class ModbusPacketAbc(metaclass=ABCMeta):
    """Abstract class for Modbus Packets."""

    def __eq__(self, other):
        """Check if two packets are equal"""
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Check if two packets are not equal"""
        return not self.__eq__(other)

    # This operation and the one below it carry no tuning parameters. A packet
    # knows its own wire layout, so a caller that could hand one in could also
    # ask a concrete packet for a frame its specification does not allow. Where
    # a layout genuinely varies per call, the class offering that freedom
    # exposes it under its own name rather than widening these; see
    # ModbusPdu.pack.
    @abstractmethod
    def serialize(self):
        """Serialize the packet and return a stream of bytes

        Returns:
            bytes : The serialized packet
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def deserialize(cls, stream):
        """Deserialize the packet from a stream of bytes

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusPacketAbc : The deserialized packet
        """
        raise NotImplementedError


class ModbusPduParserAbc(metaclass=ABCMeta):
    """Abstract class for Modbus PDU Parser."""

    @abstractmethod
    def parse_request(self, stream):
        """Parse the Modbus Request PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to parse

        Returns:
            ModbusPduAbc() : The Modbus PDU object
        """
        raise NotImplementedError

    @abstractmethod
    def parse_response(self, stream):
        """Parse the Modbus Response PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to parse

        Returns:
            ModbusPduAbc() : The Modbus PDU object
        """
        raise NotImplementedError


################################################################################
# BASE CLASSES
################################################################################


class ModbusHeader(ModbusPacketAbc):
    """Modbus Application Protocol Header (MBAP).

    The Modbus Application Protocol Header (MBAP) is used in Modbus TCP
    transactions. It contains the transaction id, the protocol id, the length
    of the data and the unit id.

    Args:
        trans_id (int)  : The transaction id
        prot_id (int)   : The protocol id; zero for Modbus TCP
        length (int)    : The length of the data
        unit_id (int)   : The unit id

    Example:
        >>> header1 = ModbusHeader(trans_id=1, prot_id=0, length=3, unit_id=4)
        >>> stream = header1.serialize()
        >>> header2 = ModbusHeader.deserialize(stream)
        >>> assert header1 == header2
    """

    HEADER_FMT = ">HHHB"
    SIZE = struct.calcsize(HEADER_FMT)

    def __init__(self, trans_id=0, prot_id=0, length=0, unit_id=0):
        """Initialize the Modbus Header.

        The Modbus Header is used in Modbus TCP transactions. It contains the
        transaction id, the protocol id, the length of the data and the unit id.

        The message format is as follows:

        - Byte 0: Transaction ID (Hi)
        - Byte 1: Transaction ID (Lo)
        - Byte 2: Protocol ID (Hi)
        - Byte 3: Protocol ID (Lo)
        - Byte 4: Length (Hi)
        - Byte 5: Length (Lo)
        - Byte 6: Unit ID

        Args:
            trans_id (int)  : The transaction id
            prot_id (int)   : The protocol id; zero for Modbus TCP
            length (int)    : The length of the data
            unit_id (int)   : The unit id
        """

        # Set the instance attributes
        self.trans_id = trans_id
        self.prot_id = prot_id
        self.length = length
        self.unit_id = unit_id

    def __len__(self):
        """Return the length of the header."""
        return struct.calcsize(self.HEADER_FMT)

    def __str__(self):
        """Return a string representation of the header"""
        msg = "HEADER: (Trans-ID: {0}, Prot-ID: {1}, Length: {2}, Unit-ID: {3})"
        return msg.format(self.trans_id, self.prot_id, self.length, self.unit_id)

    def serialize(self):
        """Serialize the header to a stream of bytes.

        Returns:
            bytes : The serialized header
        """

        try:
            stream = struct.pack(self.HEADER_FMT, self.trans_id, self.prot_id, self.length, self.unit_id)

        except Exception as e:
            message = "Error serializing the Modbus Header: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the header from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusHeader : The Modbus Header object
        """

        try:
            # Unpack the header bytes
            header = struct.unpack(cls.HEADER_FMT, stream)

        except Exception as e:
            message = "Error deserializing the Modbus Header: {0}".format(e)
            raise ModbusPacketError(message)

        return cls(trans_id=header[0], prot_id=header[1], length=header[2], unit_id=header[3])


class ModbusPdu(ModbusPacketAbc):
    """Modbus Protocol Data Unit (PDU).

    This is the base class for all Modbus Protocol Data Units (PDU). Each
    concrete PDU class should define the function code, the format string
    for the data and a unique PDU ID.

    The PDU ID is used to register the PDU class with the ModbusPduParser class.
    Requests have a PDU ID in the range 0x0000 to 0x7FFF, while responses have
    a PDU ID in the range 0x8000 to 0xFFFF.

    Args:
        fc (int)     : Function code
        data (tuple) : Packed PDU data. A subclass declaring PDU_FIELDS
            derives its payload from those fields and ignores this argument

    Example:
        >>> pdu1 = ModbusPdu(fc=1, data=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusPdu.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    # Default PDU format
    PDU_FORMAT = ">B{0}B"

    # Default PDU ID
    PDU_ID = 0x0000

    # The named fields the class carries, in wire order. None means the class
    # stores its payload rather than deriving one, which is what this class
    # does: it models no function code, so it has no named fields to read.
    PDU_FIELDS: ClassVar[tuple[str, ...] | None] = None

    # The trailing field holding a sequence that flattens into the payload,
    # or None where the layout is scalars only.
    PDU_TAIL: ClassVar[str | None] = None

    def __init__(self, fc, data=None):
        """Initialize the Modbus PDU."""

        self.fc = fc

        # A class declaring named fields reads its payload back from them, so
        # storing the argument here would restore the second copy the property
        # below exists to remove. Only a storing class takes the argument.
        if self.PDU_FIELDS is None:
            self.data = data

    def _field_names(self):
        """Name every field the payload is derived from, in wire order.

        Returns:
            list : The declared field names, empty where the class carries none
        """

        names = list(self.PDU_FIELDS or ())

        if self.PDU_TAIL is not None:
            names.append(self.PDU_TAIL)

        return names

    @property
    def data(self):
        """The PDU payload.

        A class declaring named fields derives this from them on every read,
        so a field changed after construction reaches the wire. The generic
        PDU declares none and stores what it was given.

        Returns:
            tuple : The payload in wire order
        """

        if self.PDU_FIELDS is None:
            return self._data

        values = tuple(getattr(self, name) for name in self.PDU_FIELDS)

        if self.PDU_TAIL is not None:
            values += tuple(getattr(self, self.PDU_TAIL))

        return values

    @data.setter
    def data(self, value):
        """Store the payload, or refuse where the class derives it.

        Args:
            value (tuple) : The payload to store

        Raises:
            ModbusPacketError : If the class derives its payload from fields
        """

        if self.PDU_FIELDS is not None:
            names = self._field_names()
            instead = "set " + ", ".join(names) if names else "it carries none"
            message = "{0} derives data from its named fields; {1}".format(
                type(self).__name__,
                instead,
            )
            raise ModbusPacketError(message)

        self._data = value

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.data)))

    def __str__(self):
        """Return a string representation of the PDU"""
        msg = "PDU: (FC: {0:02d}, Data: {1})"
        return msg.format(self.fc, self.data)

    def is_request(self):
        """Check if the PDU is a request."""
        return self.PDU_ID < 0x8000

    def pack(self, fmt):
        """Pack the function code and the data under an explicit format string.

        This is the escape hatch for a PDU shape the library does not model.
        Prefer serialize(), which supplies the format the class declares.

        Args:
            fmt (str)   : The format string to pack under

        Returns:
            bytes : The packed PDU
        """

        try:
            # Pack the data using the format string
            packed_bytes = struct.pack(fmt, self.fc, *self.data)

        except Exception as e:
            message = "Error serializing the Modbus PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return the packed bytes
        return packed_bytes

    @classmethod
    def unpack(cls, stream, fmt):
        """Unpack a PDU from a stream of bytes under an explicit format string.

        This is the escape hatch for a PDU shape the library does not model.
        Prefer deserialize(), which supplies the format the class declares.

        Args:
            stream (bytes)  : The stream of bytes to unpack
            fmt (str)       : The format string to unpack under

        Returns:
            ModbusPdu : The Modbus PDU object
        """

        try:
            # Unpack the message bytes
            pdu = struct.unpack(fmt, stream)

            # First byte is the function code
            fc = pdu[0]

            # The rest of the bytes are the data
            data = pdu[1:]

        except Exception as e:
            message = "Error deserializing the Modbus PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(fc, data)

    def serialize(self):
        """Serialize the PDU to a stream of bytes.

        Returns:
            bytes : The serialized PDU

        Raises:
            ModbusPacketError : If the data field carries no length
        """

        # pack() guards what it packs, but the format it is handed is built
        # here, so a data field that is not a sequence fails before pack() is
        # entered. Guarding only the call would let a TypeError out of an
        # operation whose callers catch ModbusPacketError.
        try:
            pdu_format = self.PDU_FORMAT.format(len(self.data))

        except TypeError as error:
            message = f"Error serializing the Modbus PDU: {error}"
            raise ModbusPacketError(message) from error

        return self.pack(pdu_format)

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the PDU from a stream of bytes.

        Args:
            stream (bytes)  : The stream of bytes to deserialize

        Returns:
            ModbusPdu : The Modbus PDU object

        Raises:
            ModbusPacketError : If the stream carries no length
        """

        # The first byte is the function code, the rest is the data. The
        # length is measured here rather than inside unpack(), so a stream
        # that cannot be measured is converted here too.
        try:
            pdu_format = cls.PDU_FORMAT.format(len(stream) - 1)

        except TypeError as error:
            message = f"Error deserializing the Modbus PDU: {error}"
            raise ModbusPacketError(message) from error

        return cls.unpack(stream, pdu_format)


################################################################################
# PDU PARSER
################################################################################


class ModbusPduParser(ModbusPduParserAbc):
    """Modbus PDU Parser.

    The parser is responsible for parsing the Modbus PDU based on the function
    code. It contains a registry that maps the function code to the concrete
    Modbus PDU class. The registry is populated with the default ModbusPdu
    classes and can be extended with custom PDU classes.

    Example:
        >>> parser = ModbusPduParser()
        >>> parser.register(ModbusRequestFC1)
        >>> pdu1 = ModbusRequestFC1(start_addr=1, quantity=2)
        >>> stream = pdu1.serialize()
        >>> pdu2 = parser.parse_request(stream)
        >>> assert pdu1 == pdu2

    Note: There is registration of all Modbus Requests and Responses in the end
    of the module, so if it is not commented there is no need to make an
    additional registration before serialization like in the example above.
    """

    _registry: dict[int, type[ModbusPdu]] = {}

    @classmethod
    def register(cls, pdu_class):
        """Register a Modbus PDU.

        Args:
            pdu_class (type) : The Modbus PDU to register

        """

        if not issubclass(pdu_class, ModbusPdu):
            message = "The class must be a subclass of ModbusPdu"
            raise ModbusPacketError(message)

        cls._registry[pdu_class.PDU_ID] = pdu_class

    @classmethod
    def unregister(cls, pdu_class):
        """Unregister a Modbus PDU.

        Args:
            pdu_class (type) : The Modbus PDU to unregister
        """

        if not issubclass(pdu_class, ModbusPdu):
            message = "The class must be a subclass of ModbusPdu"
            raise ModbusPacketError(message)

        del cls._registry[pdu_class.PDU_ID]

    @classmethod
    def set_registry(cls, registry):
        """Set the Modbus PDU registry.

        Args:
            registry (dict) : The Modbus PDU registry
        """
        cls._registry = registry

    @classmethod
    def get_registry(cls):
        """Get the Modbus PDU registry.

        Returns:
            dict : The Modbus PDU registry
        """
        return cls._registry

    @classmethod
    def clear_registry(cls):
        """Clear the Modbus PDU registry."""
        cls._registry.clear()

    @classmethod
    def parse_request(cls, stream):
        """Parse a Modbus PDU Request from a stream of bytes.

        Args:
            stream (bytes) : The stream of bytes to parse
        """

        try:
            # Get the function code from the stream (first byte)
            func_code = struct.unpack(">B", stream[:1])[0]

            # Parse the PDU based on the function code, return default if not found
            # Requests have the function code in the range 0x0000 to 0x007F
            pdu = cls._registry.get(func_code, ModbusPdu)

        except Exception as e:
            message = "Error parsing the Modbus Request: {0}".format(e)
            raise ModbusPacketError(message)

        # Return the deserialized PDU
        return pdu.deserialize(stream)

    @classmethod
    def parse_response(cls, stream):
        """Parse a Modbus PDU Response from a stream of bytes.

        Args:
            stream (bytes) : The stream of bytes to parse
        """

        try:
            # Get the function code from the stream (first byte)
            func_code = struct.unpack(">B", stream[:1])[0]

            # Check if the function code is an error
            if func_code >= 0x80:
                pdu = ModbusError.deserialize(stream)

            else:
                # Parse the PDU based on the function code, return default if
                # not found. Responses have the function code in the range
                # 0x8000 to 0x807F, with 0x8000 being the error PDU.
                pdu = cls._registry.get(func_code + 0x8000, ModbusPdu)

        except Exception as e:
            message = "Error parsing the Modbus Response: {0}".format(e)
            raise ModbusPacketError(message)

        # Return the deserialized PDU
        return pdu.deserialize(stream)


################################################################################
# PDU CLASSES
################################################################################


class ModbusError(ModbusPdu):
    """Modbus Error PDU.

    The Modbus Error PDU is used to report exceptions that occur during the
    processing of a Modbus request. The PDU contains the function code and the
    exception code.

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Exception code

    Args:
        fc (int)        : The function code that caused the error
        exc_code (int)  : The exception code that occurred

    Example:
        >>> pdu1 = ModbusError(fc=1, exc_code=2)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusError.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BB"
    PDU_ID = 0x8000
    PDU_FIELDS = ("exc_code",)
    ERROR_MASK = 0x80

    def __init__(self, fc, exc_code):
        """Initialize the Modbus Error PDU."""

        # Set instance attributes
        self.exc_code = exc_code

        # Call parent constructor
        super(ModbusError, self).__init__(
            fc=fc,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def __str__(self):
        """Return a string representation of the Modbus Error PDU."""
        msg = "ERROR: (Function Code: {0}, Exception Code: {1})"
        return msg.format(self.fc, self.exc_code)

    def serialize(self):
        """Serialize the error PDU to a stream of bytes

        Returns:
            bytes : The serialized error PDU
        """

        try:
            # Add 0x80 (error mask) to the function code and pack it
            func_code = struct.pack(">B", self.fc + self.ERROR_MASK)

            # Pack the exception code
            exc_code = struct.pack(">B", self.exc_code)

        except Exception as e:
            message = "Error serializing the Modbus Error PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return the packed bytes
        return func_code + exc_code

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the error PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusError() : The Modbus Error PDU
        """

        try:
            # Unpack the PDU bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

            # Get the function code by subtracting 0x80 (error mask)
            func_code = pdu[0] - cls.ERROR_MASK

            # Get the exception code
            exc_code = pdu[1]

        except Exception as e:
            message = "Error deserializing the Modbus Error PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(fc=func_code, exc_code=exc_code)


class ModbusRequestFC1(ModbusPdu):
    """Request FC1 PDU (Read Discrete Outputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Start address (Hi)
    - Byte 2: Start address (Lo)
    - Byte 3: Quantity of outputs (Hi)
    - Byte 4: Quantity of outputs (Lo)

    Args:
        start_addr (int)  : The starting address
        quantity (int)    : The quantity of outputs to read

    Example:
        >>> pdu1 = ModbusRequestFC1(start_addr=1, quantity=2)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC1.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x0001
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr, quantity):
        """Initialize the Modbus Request FC1 PDU."""

        # Set instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call parent constructor
        super(ModbusRequestFC1, self).__init__(
            fc=0x01,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the request FC1 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC1 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC1 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC1 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC1() : The Modbus Request FC1 PDU
        """

        try:
            # Unpack the PDU bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC1 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(start_addr=pdu[1], quantity=pdu[2])


class ModbusResponseFC1(ModbusPdu):
    """Response FC1 PDU (Read Discrete Outputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: - Byte count N
    - Byte 2: Output status (1-8)
    - Byte 3: Output status (9-16)
    - ...
    - Byte N: Output status (N*8-1)-(N*8)

    Args:
        byte_count (int)        : The number of bytes in the response
        output_status (tuple)   : The status of the discrete outputs

    Example:
        >>> pdu1 = ModbusResponseFC1(byte_count=2, output_status=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC1.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BB{0}B"
    PDU_ID = 0x8001
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "output_status"

    def __init__(self, byte_count, output_status):
        # Set instance attributes
        self.byte_count = byte_count
        self.output_status = tuple(output_status)

        # Call parent constructor
        super(ModbusResponseFC1, self).__init__(
            fc=0x01,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT.format(self.byte_count))

    def serialize(self):
        """Serialize the response FC1 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC1 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(self.byte_count))

        except Exception as e:
            message = "Error serializing the FC1 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC1 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC1() : The Modbus Response FC1 PDU
        """

        try:
            # Calculate the pdu data length to generate the format string
            #   The pdu has 1 byte for the FC and 1 byte for the byte count
            #   The rest of the bytes are the output status bytes
            pdu_data_length = len(stream) - 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(pdu_data_length)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the output status
            output_status = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC1 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(byte_count=byte_count, output_status=output_status)


class ModbusRequestFC2(ModbusPdu):
    """Request FC2 PDU (Read Discrete Inputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Start address (Hi)
    - Byte 2: Start address (Lo)
    - Byte 3: Quantity of inputs (Hi)
    - Byte 4: Quantity of inputs (Lo)

    Args:
        start_addr (int)  : The starting address
        quantity (int)    : The quantity of inputs to read

    Example:
        >>> pdu1 = ModbusRequestFC2(start_addr=1, quantity=2)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC2.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    # Generic PDU format string of the FC2 request PDU
    PDU_FORMAT = ">BHH"
    PDU_ID = 0x0002
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr, quantity):
        """Initialize the Modbus Request FC2 PDU."""

        # Set instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call parent constructor
        super(ModbusRequestFC2, self).__init__(
            fc=0x02,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the request FC2 PDU to a stream of bytes

        Returns:
            bytes : The serialized request FC2 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC2 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC2 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC2() : The Modbus Request FC2 PDU
        """

        try:
            # Unpack the PDU bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC2 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(start_addr=pdu[1], quantity=pdu[2])


class ModbusResponseFC2(ModbusPdu):
    """Response FC2 PDU (Read Discrete Inputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Byte count N
    - Byte 2: Input status (1-8)
    - Byte 3: Input status (9-16)
    - ...
    - Byte N: Input status (N*8-1)-(N*8)

    Args:
        byte_count (int)        : The number of bytes in the response
        input_status (tuple)    : The status of the discrete inputs

    Example:
        >>> pdu1 = ModbusResponseFC2(byte_count=2, input_status=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC2.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    # Generic PDU format string of the FC2 response PDU
    PDU_FORMAT = ">BB{0}B"
    PDU_ID = 0x8002
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "input_status"

    def __init__(self, byte_count, input_status):
        """Initialize the Modbus Response FC2 PDU."""

        # Set the instance attributes
        self.byte_count = byte_count
        self.input_status = tuple(input_status)

        # Call the parent constructor
        super(ModbusResponseFC2, self).__init__(
            fc=0x02,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(self.byte_count))

    def serialize(self):
        """Serialize the response FC2 PDU from a stream of bytes

        Returns:
            bytes : The serialized response FC2 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(self.byte_count))

        except Exception as e:
            message = "Error serializing the FC2 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC2 PDU to a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC2() : The Modbus Response FC2 PDU
        """

        try:
            # Calculate the pdu data length to generate the format string
            #   The pdu has 1 byte for the FC and 1 byte for the byte count
            #   The rest of the bytes are the input status bytes
            pdu_data_length = len(stream) - 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(pdu_data_length)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the input status
            input_status = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC2 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return cls(byte_count=byte_count, input_status=input_status)


class ModbusRequestFC3(ModbusPdu):
    """Request FC3 PDU (Read Analog Outputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Start address (Hi)
    - Byte 2: Start address (Lo)
    - Byte 3: Quantity of analog outputs (Hi)
    - Byte 4: Quantity of analog outputs (Lo)

    Args:
        start_addr (int)  : The starting address
        quantity (int)    : The quantity of outputs to read

    Example:
        >>> pdu1 = ModbusRequestFC3(start_addr=1, quantity=2)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC3.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x0003
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr, quantity):
        """Initialize the Modbus Request FC3 PDU."""

        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call the parent constructor
        super(ModbusRequestFC3, self).__init__(
            fc=0x03,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the request FC3 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC3 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC3 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC3 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC3() : The Modbus Request FC3 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC3 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(start_addr=pdu[1], quantity=pdu[2])


class ModbusResponseFC3(ModbusPdu):
    """Response FC3 PDU (Read Analog Outputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Byte count N
    - Byte 2: Register value 1 Hi
    - Byte 3: Register value 1 Lo
    - ...
    - Byte N-1: Register value N/2 Hi
    - Byte N: Register value N/2 Lo

    Args:
        byte_count (int)     : The number of bytes in the response
        values (tuple)       : The values of the analog outputs

    Example:
        >>> pdu1 = ModbusResponseFC3(byte_count=2, values=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC3.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BB{0}H"
    PDU_ID = 0x8003
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "values"

    def __init__(self, byte_count, values):
        """Initialize the Modbus Response FC3 PDU."""

        # Set the instance attributes
        self.byte_count = byte_count
        self.values = tuple(values)

        # Call the parent constructor
        super(ModbusResponseFC3, self).__init__(
            fc=0x03,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.values)))

    def serialize(self):
        """Serialize the response FC3 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC3 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.values)))

        except Exception as e:
            message = "Error serializing the FC3 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC3 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC3() : The Modbus Response FC3 PDU
        """

        try:
            # Calculate the pdu data length to generate the format string
            # -----------------------------------------------------------
            # The pdu has 1 byte for the FC and 1 byte for the byte count
            # The rest of the bytes are the register values, each register
            # is 2 bytes long.

            reg_count = (len(stream) - 2) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(reg_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the register values
            values = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC3 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(byte_count=byte_count, values=values)


class ModbusRequestFC4(ModbusPdu):
    """Request FC4 PDU (Read Analog Inputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Start address (Hi)
    - Byte 2: Start address (Lo)
    - Byte 3: Quantity of analog inputs (Hi)
    - Byte 4: Quantity of analog inputs (Lo)

    Args:
        start_addr (int)  : The starting address
        quantity (int)    : The quantity of inputs to read

    Example:
        >>> pdu1 = ModbusRequestFC4(start_addr=1, quantity=2)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC4.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x0004
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr, quantity):
        """Initialize the Modbus Request FC4 PDU"""

        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call the parent constructor
        super(ModbusRequestFC4, self).__init__(
            fc=0x04,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the request FC4 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC4 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC4 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC4 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC4() : The Modbus Request FC4 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC4 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(start_addr=pdu[1], quantity=pdu[2])


class ModbusResponseFC4(ModbusPdu):
    """Response FC4 PDU (Read Analog Inputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Byte count N
    - Byte 2: Register value 1 Hi
    - Byte 3: Register value 1 Lo
    - ...
    - Byte N-1: Register value N/2 Hi
    - Byte N: Register value N/2 Lo

    Args:
        byte_count (int)    : The number of bytes in the response
        values (tuple)      : The values of the analog inputs

    Example:
        >>> pdu1 = ModbusResponseFC4(byte_count=2, values=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC4.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BB{0}H"
    PDU_ID = 0x8004
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "values"

    def __init__(self, byte_count, values):
        """Initialize the Modbus Response FC4 PDU."""

        # Set the instance attributes
        self.byte_count = byte_count
        self.values = tuple(values)

        # Call the parent constructor
        super(ModbusResponseFC4, self).__init__(
            fc=0x04,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.values)))

    def serialize(self):
        """Serialize the response FC4 PDU to a stream of bytes

        Returns:
            bytes : The serialized response FC4 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.values)))

        except Exception as e:
            message = "Error serializing the FC4 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC4 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC4() : The Modbus Response FC4 PDU
        """

        try:
            # Calculate the pdu data length to generate the format string
            # -----------------------------------------------------------
            # The pdu has 1 byte for the FC and 1 byte for the byte count
            # The rest of the bytes are the register values, each register
            # is 2 bytes long.

            reg_count = (len(stream) - 2) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(reg_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the register values
            values = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC4 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(byte_count=byte_count, values=values)


class ModbusRequestFC5(ModbusPdu):
    """Request FC5 PDU (Write Single Discrete Output).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Output address (Hi)
    - Byte 2: Output address (Lo)
    - Byte 3: Output value (Hi)
    - Byte 4: Output value (Lo)

    Args:
        output_address (int)    : The output address
        output_value (int)      : The output value

    Example:
        >>> pdu1 = ModbusRequestFC5(output_address=1, output_value=1)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC5.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x0005
    PDU_FIELDS = ("output_address", "output_value")

    def __init__(self, output_address, output_value):
        """Initialize the Modbus Request FC5 PDU."""

        # Set the instance attributes
        self.output_address = output_address
        self.output_value = output_value

        # Call the parent constructor
        super(ModbusRequestFC5, self).__init__(
            fc=0x05,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the request FC5 PDU from a stream of bytes.

        Returns:
            bytes : The serialized request FC5 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC5 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC5 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC5() : The Modbus Request FC5 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC5 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(output_address=pdu[1], output_value=pdu[2])


class ModbusResponseFC5(ModbusPdu):
    """Response FC5 PDU (Write Single Discrete Output).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Output address (Hi)
    - Byte 2: Output address (Lo)
    - Byte 3: Output value (Hi)
    - Byte 4: Output value (Lo)

    Args:
        output_address (int)    : The output address
        output_value (int)      : The output value

    Example:
        >>> pdu1 = ModbusResponseFC5(output_address=1, output_value=1)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC5.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x8005
    PDU_FIELDS = ("output_address", "output_value")

    def __init__(self, output_address, output_value):
        """Initialize the Modbus Response FC5 PDU"""

        # Set the instance attributes
        self.output_address = output_address
        self.output_value = output_value

        # Call the parent constructor
        super(ModbusResponseFC5, self).__init__(
            fc=0x05,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the response FC5 PDU to a stream of bytes

        Returns:
            bytes : The serialized response FC5 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC5 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC5 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC5() : The Modbus Response FC5 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(">BHH", stream)

        except Exception as e:
            message = "Error deserializing the FC5 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(output_address=pdu[1], output_value=pdu[2])


class ModbusRequestFC6(ModbusPdu):
    """Request FC6 PDU (Write Single Analog Output).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Output address (Hi)
    - Byte 2: Output address (Lo)
    - Byte 3: Output value (Hi)
    - Byte 4: Output value (Lo)

    Args:
        output_address (int)    : The output address
        output_value (int)      : The output value

    Example:
        >>> pdu1 = ModbusRequestFC6(output_address=1, output_value=1)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC6.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x0006
    PDU_FIELDS = ("output_address", "output_value")

    def __init__(self, output_address, output_value):
        """Initialize the Modbus Request FC6 PDU."""

        # Set the instance attributes
        self.output_address = output_address
        self.output_value = output_value

        # Call the parent constructor
        super(ModbusRequestFC6, self).__init__(
            fc=0x06,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the request FC6 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC6 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC6 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC6 PDU.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC6() : The Modbus Request FC6 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC6 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(output_address=pdu[1], output_value=pdu[2])


class ModbusResponseFC6(ModbusPdu):
    """Response FC6 PDU (Write Single Analog Output).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Output address (Hi)
    - Byte 2: Output address (Lo)
    - Byte 3: Output value (Hi)
    - Byte 4: Output value (Lo)

    Args:
        output_address (int)    : The output address
        output_value (int)      : The output value

    Example:
        >>> pdu1 = ModbusResponseFC6(output_address=1, output_value=1)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC6.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x8006
    PDU_FIELDS = ("output_address", "output_value")

    def __init__(self, output_address, output_value):
        """Initialize the Modbus Response FC6 PDU."""

        # Set the instance attributes
        self.output_address = output_address
        self.output_value = output_value

        # Call the parent constructor
        super(ModbusResponseFC6, self).__init__(
            fc=0x06,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the response FC6 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC6 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC6 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC6 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC6() : The Modbus Response FC6 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC6 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(output_address=pdu[1], output_value=pdu[2])


class ModbusRequestFC7(ModbusPdu):
    """Request FC7 PDU (Read Exception Status).

    The message format is as follows:

    - Byte 0: Function code

    Example:
        >>> pdu1 = ModbusRequestFC7()
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC7.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">B"
    PDU_ID = 0x0007
    PDU_FIELDS = ()

    def __init__(self):
        """Initialize the Modbus Request FC7 PDU."""

        # Call the parent constructor
        super(ModbusRequestFC7, self).__init__(
            fc=0x07,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the request FC7 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC7 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC7 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC7 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC7() : The Modbus Request FC7 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC7 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return cls()


class ModbusResponseFC7(ModbusPdu):
    """Response FC7 PDU (Read Exception Status).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Exception Status

    Args:
        status (int)    : The exception status

    Example:
        >>> pdu1 = ModbusResponseFC7(status=1)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC7.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BB"
    PDU_ID = 0x8007
    PDU_FIELDS = ("status",)

    def __init__(self, status):
        """Initialize the Modbus Response FC7 PDU."""

        # Set the instance attributes
        self.status = status

        # Call the parent constructor
        super(ModbusResponseFC7, self).__init__(
            fc=0x07,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the response FC7 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC7 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC7 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC7 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC7() : The Modbus Response FC7 PDU
        """

        try:
            # Unpack the pdu
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC7 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(status=pdu[1])


class ModbusRequestFC8(ModbusPdu):
    """Request FC8 PDU (Diagnostics).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Sub-function code Hi
    - Byte 2: Sub-function code Lo
    - Byte 2: Data 1 Hi
    - Byte 3: Data 1 Lo
    - ...
    - Byte N-1: Data N/2 Hi
    - Byte N: Data N/2 Lo

    Args:
        sub_func (int)  : The sub-function code
        subfunc_data (tuple)    : The data to send assiciated with the sub-func

    Example:
        >>> pdu1 = ModbusRequestFC8(sub_func=1, subfunc_data=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC8.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BH{0}H"
    PDU_ID = 0x0008
    PDU_FIELDS = ("sub_func",)
    PDU_TAIL = "subfunc_data"

    def __init__(self, sub_func, subfunc_data):
        """Initialize the Modbus Request FC8 PDU"""

        # Set the instance attributes
        self.sub_func = sub_func
        self.subfunc_data = tuple(subfunc_data)

        # Call the parent constructor
        super(ModbusRequestFC8, self).__init__(
            fc=0x08,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.subfunc_data)))

    def serialize(self):
        """Serialize the request FC8 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC8 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.subfunc_data)))

        except Exception as e:
            message = "Error serializing the FC8 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC8 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC8() : The Modbus Request FC8 PDU
        """

        try:
            # Create the format string
            # ----------------------------------------------------------------------
            # The pdu has 1 byte for the FC, 2 bytes for the sub-function
            # and the rest of the bytes are the data bytes.
            data_count = (len(stream) - 3) // 2

            pdu_format = cls.PDU_FORMAT.format(data_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Get the sub-function
            sub_func = pdu[1]

            # Get the data
            subfunc_data = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC8 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(sub_func=sub_func, subfunc_data=subfunc_data)


class ModbusResponseFC8(ModbusPdu):
    """Response FC8 PDU (Diagnostics).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Sub-function code Hi
    - Byte 2: Sub-function code Lo
    - Byte 3: Data 1 Hi
    - Byte 4: Data 1 Lo
    - ...
    - Byte N-1: Data N/2 Hi
    - Byte N: Data N/2 Lo

    Args:
        sub_func (int)  : The sub-function code
        subfunc_data (tuple)    : The data to send assiciated with the sub-func

    Example:
        >>> pdu1 = ModbusResponseFC8(sub_func=1, subfunc_data=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC8.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BH{0}H"
    PDU_ID = 0x8008
    PDU_FIELDS = ("sub_func",)
    PDU_TAIL = "subfunc_data"

    def __init__(self, sub_func, subfunc_data):
        """Initialize the Modbus Response FC8 PDU."""

        # Set the instance attributes
        self.sub_func = sub_func
        self.subfunc_data = tuple(subfunc_data)

        # Call the parent constructor
        super(ModbusResponseFC8, self).__init__(
            fc=0x08,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.subfunc_data)))

    def serialize(self):
        """Serialize the response FC8 PDU to a stream of bytes

        Returns:
            bytes : The serialized response FC8 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.subfunc_data)))

        except Exception as e:
            message = "Error serializing the FC8 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC8 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC8() : The Modbus Response FC8 PDU
        """

        try:
            # Create the format string
            # ----------------------------------------------------------------------
            # The pdu has 1 byte for the FC, 2 bytes for the sub-function
            # and the rest of the bytes are the data bytes.

            # Calculate the pdu data length to generate the format string
            data_count = (len(stream) - 3) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(data_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Get the sub-function
            sub_func = pdu[1]

            # Get the data
            subfunc_data = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC8 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(sub_func=sub_func, subfunc_data=subfunc_data)


class ModbusRequestFC15(ModbusPdu):
    """Request FC15 PDU (Write Multiple Discrete Outputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Start address (Hi)
    - Byte 2: Start address (Lo)
    - Byte 3: Quantity of outputs (Hi)
    - Byte 4: Quantity of outputs (Lo)
    - Byte 5: Byte count N
    - Byte 6: Outputs value (1-8)
    - ...
    - Byte N: Outputs value (N*8-1)-(N*8)

    Args:
        start_addr (int)        : The starting address
        quantity (int)          : The quantity of outputs
        byte_count (int)        : The number of bytes in the request
        values (tuple)          : The values of the outputs

    Example:
        >>> pdu1 = ModbusRequestFC15(start_addr=1, quantity=2, byte_count=1, values=(1,))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC15.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHHB{0}B"
    PDU_ID = 0x000F
    PDU_FIELDS = ("start_addr", "quantity", "byte_count")
    PDU_TAIL = "values"

    def __init__(self, start_addr, quantity, byte_count, values):
        """Initialize the Modbus Request FC15 PDU."""

        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity
        self.byte_count = byte_count
        self.values = tuple(values)

        super(ModbusRequestFC15, self).__init__(
            fc=0x0F,
        )

    def __len__(self):
        fmt = self.PDU_FORMAT.format(len(self.values))
        return struct.calcsize(fmt)

    def serialize(self):
        """Serialize the request FC15 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC15 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.values)))

        except Exception as e:
            message = "Error serializing the FC15 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC15 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC15() : The Modbus Request FC15 PDU
        """

        try:
            # Calculate the pdu data length to generate the format string
            # -----------------------------------------------------------
            # The pdu has 1 byte for the FC, 2 bytes for the starting address
            # 2 bytes for the quantity of outputs, 1 byte for the byte count.
            # The rest of the bytes are the output status bytes.

            pdu_data_length = len(stream) - 6

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(pdu_data_length)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract starting address
            start_addr = pdu[1]

            # Extract the quantity of coils
            quantity = pdu[2]

            # Extract the byte count
            byte_count = pdu[3]

            # Extract the values
            values = pdu[4:]

        except Exception as e:
            message = "Error deserializing the FC15 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(start_addr=start_addr, quantity=quantity, byte_count=byte_count, values=values)


class ModbusResponseFC15(ModbusPdu):
    """Response FC15 PDU (Write Multiple Discrete Outputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Start address (Hi)
    - Byte 2: Start address (Lo)
    - Byte 3: Quantity of outputs (Hi)
    - Byte 4: Quantity of outputs (Lo)

    Args:
        start_addr (int)  : The starting address
        quantity (int)    : The quantity of outputs

    Example:
        >>> pdu1 = ModbusResponseFC15(start_addr=1, quantity=2)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC15.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x800F
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr, quantity):
        """Initialize the Modbus Response FC15 PDU."""

        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call the parent constructor
        super(ModbusResponseFC15, self).__init__(
            fc=0x0F,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the response FC15 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC15 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC15 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC15 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC15() : The Modbus Response FC15 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

            # Get the starting address
            start_addr = pdu[1]

            # Get the quantity of outputs
            quantity = pdu[2]

        except Exception as e:
            message = "Error deserializing the FC15 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(start_addr=start_addr, quantity=quantity)


class ModbusRequestFC16(ModbusPdu):
    """Request FC16 PDU (Write Multiple Analog Outputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Start address (Hi)
    - Byte 2: Start address (Lo)
    - Byte 3: Quantity of outputs (Hi)
    - Byte 4: Quantity of outputs (Lo)
    - Byte 5: Byte count N
    - Byte 6: Register value 1 Hi
    - Byte 7: Register value 1 Lo
    - ...
    - Byte N-1: Register value N/2 Hi
    - Byte N: Register value N/2 Lo

    Args:
        start_addr (int)  : The starting address
        quantity (int)    : The quantity of outputs
        byte_count (int)  : The number of bytes in the request
        values (tuple)    : The values of the analog outputs

    Example:
        >>> pdu1 = ModbusRequestFC16(start_addr=1, quantity=2, byte_count=2, values=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC16.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHHB{0}H"
    PDU_ID = 0x0010
    PDU_FIELDS = ("start_addr", "quantity", "byte_count")
    PDU_TAIL = "values"

    def __init__(self, start_addr, quantity, byte_count, values):
        """Initialize the Modbus Request FC16 PDU."""

        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity
        self.byte_count = byte_count
        self.values = tuple(values)

        # Call the parent constructor
        super(ModbusRequestFC16, self).__init__(
            fc=0x10,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        fmt = self.PDU_FORMAT.format(len(self.values))
        return struct.calcsize(fmt)

    def serialize(self):
        """Serialize the request FC16 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC16 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.values)))

        except Exception as e:
            message = "Error serializing the FC16 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC16 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC16 : The Modbus Request FC16 PDU
        """

        try:
            # Calculate the pdu data length to generate the format string
            # -----------------------------------------------------------
            # The pdu has 1 byte for the FC, 2 bytes for the starting address
            # 2 bytes for the quantity of outputs, 1 byte for the byte count.
            # The rest of the bytes are the register values, each register
            # is 2 bytes long.

            reg_count = (len(stream) - 6) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(reg_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract starting address
            start_addr = pdu[1]

            # Extract the quantity of outputs
            quantity = pdu[2]

            # Extract the byte count
            byte_count = pdu[3]

            # Extract the values
            values = pdu[4:]

        except Exception as e:
            message = "Error deserializing the FC16 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(start_addr=start_addr, quantity=quantity, byte_count=byte_count, values=values)


class ModbusResponseFC16(ModbusPdu):
    """Response FC16 PDU (Write Multiple Analog Outputs).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Start address (Hi)
    - Byte 2: Start address (Lo)
    - Byte 3: Quantity of outputs (Hi)
    - Byte 4: Quantity of outputs (Lo)

    Args:
        start_addr (int)  : The starting address
        quantity (int)          : The quantity of outputs

    Example:
        >>> pdu1 = ModbusResponseFC16(start_addr=1, quantity=2)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC16.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHH"
    PDU_ID = 0x8010
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr, quantity):
        """Initialize the Modbus Response FC16 PDU."""

        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call the parent constructor
        super(ModbusResponseFC16, self).__init__(
            fc=0x10,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the response FC16 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC16 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC16 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC16 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC16() : The Modbus Response FC16 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

            # Get the starting address
            start_addr = pdu[1]

            # Get the quantity of outputs
            quantity = pdu[2]

        except Exception as e:
            message = "Error deserializing the FC16 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(start_addr=start_addr, quantity=quantity)


class ModbusRequestFC22(ModbusPdu):
    """Request FC22 PDU (Mask Write Register).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Reference address (Hi)
    - Byte 2: Reference address (Lo)
    - Byte 3: And mask (Hi)
    - Byte 4: And mask (Lo)
    - Byte 5: Or mask (Hi)
    - Byte 6: Or mask (Lo)

    Args:
        ref_addr (int)    : The reference address
        and_mask (int)    : The AND mask
        or_mask (int)     : The OR mask

    Example:
        >>> pdu1 = ModbusRequestFC22(ref_addr=1, and_mask=1, or_mask=1)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC22.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHHH"
    PDU_ID = 0x0016
    PDU_FIELDS = ("ref_addr", "and_mask", "or_mask")

    def __init__(self, ref_addr, and_mask, or_mask):
        """Initialize the Modbus Request FC22 PDU."""

        # Set the instance attributes
        self.ref_addr = ref_addr
        self.and_mask = and_mask
        self.or_mask = or_mask

        # Call the parent constructor
        super(ModbusRequestFC22, self).__init__(
            fc=0x16,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the request FC22 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC22 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC22 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC22 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC22() : The Modbus Request FC22 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC22 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(ref_addr=pdu[1], and_mask=pdu[2], or_mask=pdu[3])


class ModbusResponseFC22(ModbusPdu):
    """Response FC22 PDU (Mask Write Register).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Reference address (Hi)
    - Byte 2: Reference address (Lo)
    - Byte 3: And mask (Hi)
    - Byte 4: And mask (Lo)
    - Byte 5: Or mask (Hi)
    - Byte 6: Or mask (Lo)

    Args:
        ref_addr (int)    : The reference address
        and_mask (int)    : The AND mask
        or_mask (int)     : The OR mask

    Example:
        >>> pdu1 = ModbusResponseFC22(ref_addr=1, and_mask=1, or_mask=1)
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC22.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHHH"
    PDU_ID = 0x8016
    PDU_FIELDS = ("ref_addr", "and_mask", "or_mask")

    def __init__(self, ref_addr, and_mask, or_mask):
        """Initialize the Modbus Response FC22 PDU."""

        # Set the instance attributes
        self.ref_addr = ref_addr
        self.and_mask = and_mask
        self.or_mask = or_mask

        # Call the parent constructor
        super(ModbusResponseFC22, self).__init__(
            fc=0x16,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self):
        """Serialize the response FC22 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC22 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT)

        except Exception as e:
            message = "Error serializing the FC22 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC22 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC22() : The Modbus Response FC22 PDU
        """

        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except Exception as e:
            message = "Error deserializing the FC22 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(ref_addr=pdu[1], and_mask=pdu[2], or_mask=pdu[3])


class ModbusRequestFC23(ModbusPdu):
    """Request FC23 PDU (Read/Write Multiple Registers).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Read start address (Hi)
    - Byte 2: Read start address (Lo)
    - Byte 3: Read quantity of registers (Hi)
    - Byte 4: Read quantity of registers (Lo)
    - Byte 5: Write start address (Hi)
    - Byte 6: Write start address (Lo)
    - Byte 7: Write quantity of registers (Hi)
    - Byte 8: Write quantity of registers (Lo)
    - Byte 9: Write byte count
    - Byte 10: Write register value 1 Hi
    - Byte 11: Write register value 1 Lo
    - ...
    - Byte N-1: Write register value N/2 Hi

    Args:
        read_start_addr (int)    : The starting address for reading
        read_quantity (int)            : The quantity of registers to read
        write_start_addr (int)   : The starting address for writing
        write_quantity (int)           : The quantity of registers to write
        write_byte_count (int)         : The number of bytes in the write request
        write_values (tuple)           : The values to write to the registers

    Example:
        >>> pdu1 = ModbusRequestFC23(
        ...     read_start_addr=1,
        ...     read_quantity=2,
        ...     write_start_addr=1,
        ...     write_quantity=2,
        ...     write_byte_count=2,
        ...     write_values=(1, 2)
        ... )
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC23.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BHHHHB{0}H"
    PDU_ID = 0x0017
    PDU_FIELDS = ("read_start_addr", "read_quantity", "write_start_addr", "write_quantity", "write_byte_count")
    PDU_TAIL = "write_values"

    def __init__(
        self, read_start_addr, read_quantity, write_start_addr, write_quantity, write_byte_count, write_values
    ):
        """Initialize the Modbus Request FC23 PDU."""

        # Set the instance attributes
        self.read_start_addr = read_start_addr
        self.read_quantity = read_quantity
        self.write_start_addr = write_start_addr
        self.write_quantity = write_quantity
        self.write_byte_count = write_byte_count
        self.write_values = tuple(write_values)

        # Call the parent constructor
        super(ModbusRequestFC23, self).__init__(
            fc=0x17,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        fmt = self.PDU_FORMAT.format(len(self.write_values))
        return struct.calcsize(fmt)

    def serialize(self):
        """Serialize the request FC23 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC23 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.write_values)))

        except Exception as e:
            message = "Error serializing the FC23 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC23 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC23() : The Modbus Request FC23 PDU
        """

        try:
            # Calculate the pdu data length to generate the format string
            # -----------------------------------------------------------
            # The pdu has 1 byte for the FC, 2 bytes for the read starting address
            # 2 bytes for the read quantity, 2 bytes for the write starting address
            # 2 bytes for the write quantity, 1 byte for the write byte count.
            # The rest of the bytes are the register values, each register
            # is 2 bytes long.

            reg_count = (len(stream) - 10) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(reg_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract read starting address
            read_start_addr = pdu[1]

            # Extract read quantity
            read_quantity = pdu[2]

            # Extract write starting address
            write_start_addr = pdu[3]

            # Extract write quantity
            write_quantity = pdu[4]

            # Extract write byte count
            write_byte_count = pdu[5]

            # Extract the write values
            write_values = pdu[6:]

        except Exception as e:
            message = "Error deserializing the FC23 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(
            read_start_addr=read_start_addr,
            read_quantity=read_quantity,
            write_start_addr=write_start_addr,
            write_quantity=write_quantity,
            write_byte_count=write_byte_count,
            write_values=write_values,
        )


class ModbusResponseFC23(ModbusPdu):
    """Response FC23 PDU (Read/Write Multiple Registers).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: Byte count N
    - Byte 2: Register value 1 Hi
    - Byte 3: Register value 1 Lo
    - ...
    - Byte N-1: Register value N/2 Hi
    - Byte N: Register value N/2 Lo

    Args:
        byte_count (int)    : The number of bytes in the response
        values (tuple)      : The values of the registers

    Example:
        >>> pdu1 = ModbusResponseFC23(byte_count=2, values=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC23.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BB{0}H"
    PDU_ID = 0x8017
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "values"

    def __init__(self, byte_count, values):
        """Initialize the Modbus Response FC23 PDU."""

        # Set the instance attributes
        self.byte_count = byte_count
        self.values = tuple(values)

        # Call the parent constructor
        super(ModbusResponseFC23, self).__init__(
            fc=0x17,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        fmt = self.PDU_FORMAT.format(len(self.values))
        return struct.calcsize(fmt)

    def serialize(self):
        """Serialize the response FC23 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC23 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.values)))

        except Exception as e:
            message = "Error serializing the FC23 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC23 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC23() : The Modbus Response FC23 PDU
        """

        try:
            # Calculate the pdu data length to generate the format string
            # -----------------------------------------------------------
            # The pdu has 1 byte for the FC and 1 byte for the byte count
            # The rest of the bytes are the register values, each register
            # is 2 bytes long.

            reg_count = (len(stream) - 2) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(reg_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the register values
            values = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC23 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(byte_count=byte_count, values=values)


class ModbusRequestFC43(ModbusPdu):
    """Request FC43 PDU (Device Identification).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: MEI type code
    - Byte 2: MEI data byte 1
    - Byte 3: MEI data byte 2
    - ...
    - Byte N: MEI data byte N-2

    *MEI = Modbus Encapsulated Interface

    Args:
        mei_type (int)      : The MEI type code
        mei_data (tuple)    : The MEI data bytes

    Example:
        >>> pdu1 = ModbusRequestFC43(mei_type=1, mei_data=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusRequestFC43.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BB{0}B"
    PDU_ID = 0x002B
    PDU_FIELDS = ("mei_type",)
    PDU_TAIL = "mei_data"

    def __init__(self, mei_type, mei_data):
        """Initialize the Modbus Request FC43 PDU."""

        # Set the instance attributes
        self.mei_type = mei_type
        self.mei_data = tuple(mei_data)

        # Call the parent constructor
        super(ModbusRequestFC43, self).__init__(
            fc=0x2B,
        )

    def __len__(self):
        """Return the length of the PDU data."""
        fmt = self.PDU_FORMAT.format(len(self.mei_data))
        return struct.calcsize(fmt)

    def serialize(self):
        """Serialize the request FC43 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC43 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.mei_data)))

        except Exception as e:
            message = "Error serializing the FC43 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the request FC43 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC43() : The Modbus Request FC43 PDU
        """

        try:
            # Create the format string
            # ----------------------------------------------------------------------
            # The pdu has 1 byte for the FC, 1 byte for the MEI type
            # and the rest of the bytes are the MEI data bytes.

            data_count = len(stream) - 2

            pdu_format = cls.PDU_FORMAT.format(data_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Get the MEI type
            mei_type = pdu[1]

            # Get the MEI data
            mei_data = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC43 Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(mei_type=mei_type, mei_data=mei_data)


class ModbusResponseFC43(ModbusPdu):
    """Response FC43 PDU (Device Identification).

    The message format is as follows:

    - Byte 0: Function code
    - Byte 1: MEI type code
    - Byte 2: MEI data byte 1
    - Byte 3: MEI data byte 2
    - ...
    - Byte N: MEI data byte N-2

    *MEI = Modbus Encapsulated Interface

    Args:
        mei_type (int)      : The MEI type code
        mei_data (tuple)    : The MEI data bytes

    Example:
        >>> pdu1 = ModbusResponseFC43(mei_type=1, mei_data=(1, 2))
        >>> stream = pdu1.serialize()
        >>> pdu2 = ModbusResponseFC43.deserialize(stream)
        >>> assert pdu1 == pdu2
    """

    PDU_FORMAT = ">BB{0}B"
    PDU_ID = 0x802B
    PDU_FIELDS = ("mei_type",)
    PDU_TAIL = "mei_data"

    def __init__(self, mei_type, mei_data):
        """Initialize the Modbus Response FC43 PDU."""

        # Set the instance attributes
        self.mei_type = mei_type
        self.mei_data = tuple(mei_data)

        # Call the parent constructor
        super(ModbusResponseFC43, self).__init__(
            fc=0x2B,
        )

    def __len__(self):
        """Return the length of the PDU data"""
        fmt = self.PDU_FORMAT.format(len(self.mei_data))
        return struct.calcsize(fmt)

    def serialize(self):
        """Serialize the response FC43 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC43 PDU
        """

        try:
            stream = self.pack(self.PDU_FORMAT.format(len(self.mei_data)))

        except Exception as e:
            message = "Error serializing the FC43 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return stream

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the response FC43 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC43() : The Modbus Response FC43 PDU
        """

        try:
            # Create the format string
            # ----------------------------------------------------------------------
            # The pdu has 1 byte for the FC, 1 byte for the MEI type
            # and the rest of the bytes are the MEI data bytes.
            data_count = len(stream) - 2

            pdu_format = cls.PDU_FORMAT.format(data_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Get the MEI type
            mei_type = pdu[1]

            # Get the MEI data
            mei_data = pdu[2:]

        except Exception as e:
            message = "Error deserializing the FC43 Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return new instance
        return cls(mei_type=mei_type, mei_data=mei_data)


################################################################################
# MODBUS RTU PACKETS
################################################################################

# Modbus RTU appends the checksum low byte first, unlike every other multi-byte
# field in the protocol, which is big-endian. Packing it with '>H' produces a
# frame that round-trips against this library and is rejected by every other
# implementation, so the order is named here rather than spelled inline.
CRC_FMT = "<H"

# Width of the checksum on the wire, in bytes.
CRC_SIZE = struct.calcsize(CRC_FMT)


def calc_crc16(data):
    """Compute the CRC-16/MODBUS checksum of a buffer.

    The result is the checksum as an ordinary integer. It is the caller's job
    to place it on the wire low byte first, which CRC_FMT does.

    Args:
        data (bytes) : The bytes to checksum

    Returns:
        int : The CRC value
    """

    crc = 0xFFFF

    for byte in bytearray(data):
        # XOR the byte into the least significant byte of the crc
        crc ^= byte

        for _ in range(8):
            # Shift right, and on a set least significant bit fold in the
            # reversed generator polynomial 0xA001.
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001

            else:
                crc >>= 1

    return crc


def validate_crc(stream, packet_name):
    """Check the trailing CRC of an RTU ADU against its own payload.

    Args:
        stream (bytes)      : The complete RTU ADU, checksum included
        packet_name (str)   : The packet description used in the error message

    Returns:
        int : The CRC carried by the frame

    Raises:
        ModbusPacketError : If the frame contradicts its own checksum
    """

    # The shortest ADU any function code can produce is a slave id, a function
    # code and the checksum. Anything shorter has no checksum to check, and
    # slicing one out of it would fail on the unpack instead.
    if len(stream) < 2 + CRC_SIZE:
        message = ("The {0} is {1} byte(s) long, too short to carry a slave id, a function code and a CRC").format(
            packet_name, len(stream)
        )
        raise ModbusPacketError(message)

    (received,) = struct.unpack(CRC_FMT, stream[-CRC_SIZE:])
    expected = calc_crc16(stream[:-CRC_SIZE])

    if received != expected:
        message = (
            "The {0} carries CRC 0x{1:04X} but its payload computes to 0x{2:04X}, so the frame is corrupt"
        ).format(packet_name, received, expected)
        raise ModbusPacketError(message)

    return received


class ModbusRtuRequest(ModbusPacketAbc):
    """Modbus RTU Request.

    The Modbus RTU ADU consists of the slave address, the PDU and the CRC.

    Args:
        slave_id (int)      : The slave id
        pdu (ModbusPduAbc)  : The Modbus Request PDU

    Example:
        >>> pdu = ModbusRequestFC1(start_addr=1, quantity=2)
        >>> request1 = ModbusRtuRequest(slave_id=1, pdu=pdu)
        >>> stream = request1.serialize()
        >>> request2 = ModbusRtuRequest.deserialize(stream)
        >>> assert request1 == request2
    """

    _pdu_parser = ModbusPduParser

    def __init__(self, slave_id, pdu):
        """Initialize the Modbus RTU Request Packet."""

        # Set the instance attributes
        self.slave_id = slave_id
        self.pdu = pdu
        self.crc = 0xFFFF

    def __str__(self):
        """Return a string representation of the Modbus RTU Request Packet."""
        msg = "MODBUS RTU REQ: (Slave ID: {0}, {1}, CRC: {2})"
        return msg.format(self.slave_id, self.pdu, self.crc)

    @classmethod
    def get_parser(cls):
        """Get the PDU parser.

        Returns:
            ModbusPduParser : The PDU parser
        """
        return cls._pdu_parser

    @classmethod
    def set_parser(cls, parser):
        """Set the PDU parser.

        Args:
            parser (type) : The PDU parser
        """

        if not issubclass(parser, ModbusPduParserAbc):
            message = "The parser must be a subclass of ModbusPduParserAbc"
            raise ModbusPacketError(message)

        cls._pdu_parser = parser

    def set_crc(self, value):
        """Set the Modbus CRC."""
        self.crc = value

    def calc_crc(self):
        """Calculate the Modbus CRC over the slave id and the PDU.

        The checksum covers everything ahead of it in the ADU. The result is
        stored on the packet and returned.

        Returns:
            int : The CRC value
        """

        self.crc = calc_crc16(bytearray([self.slave_id]) + self.pdu.serialize())

        return self.crc

    def serialize(self):
        """Serialize the Modbus RTU ADU to a stream of bytes.

        The checksum is recomputed from the current slave id and PDU, so the
        emitted frame always agrees with itself. Any value previously assigned
        through set_crc() is overwritten.

        Returns:
            bytes : The serialized Modbus RTU ADU
        """

        try:
            # Pack the slave id and the PDU, then checksum what was packed
            slave_id = struct.pack(">B", self.slave_id)
            pdu = self.pdu.serialize()
            self.crc = calc_crc16(slave_id + pdu)
            crc = struct.pack(CRC_FMT, self.crc)

        except Exception as e:
            message = "Error serializing the RTU Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return the packed bytes
        return slave_id + pdu + crc

    @classmethod
    def deserialize(cls, stream, verify_crc=True):
        """Deserialize the Modbus RTU Packet from a stream of bytes.

        Args:
            stream (bytes)      : The stream of bytes to deserialize
            verify_crc (bool)   : Check the frame against its own checksum.
                                  Pass False to accept a corrupt frame, which
                                  tests constructing one need.

        Returns:
            ModbusRtuRequest() : The Modbus RTU Request Packet

        Raises:
            ModbusPacketError : If the frame contradicts its own checksum
        """

        # Checked before parsing: a corrupt frame is worth rejecting on the
        # checksum rather than on whatever the damaged bytes decode to.
        if verify_crc:
            validate_crc(stream, "RTU Request")

        try:
            # The slave id is the first byte
            (slave_id,) = struct.unpack(">B", stream[:1])

            # The crc is the last two bytes, low byte first
            (crc,) = struct.unpack(CRC_FMT, stream[-CRC_SIZE:])

            # Parse the concrete pdu from the stream
            pdu = cls._pdu_parser.parse_request(stream[1:-CRC_SIZE])

            # Create a new instance of the class
            packet = cls(slave_id=slave_id, pdu=pdu)
            packet.set_crc(crc)

        except Exception as e:
            message = "Error deserializing the RTU Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return the packet
        return packet


class ModbusRtuResponse(ModbusPacketAbc):
    """Modbus RTU Response.

    The Modbus RTU ADU consists of the slave address, the PDU and the CRC.

    Args:
        slave_id (int)      : The slave id
        pdu (ModbusPduAbc)  : The Modbus Response PDU

    Example:
        >>> pdu = ModbusResponseFC1(byte_count=2, output_status=(1, 2))
        >>> request1 = ModbusRtuResponse(slave_id=1, pdu=pdu)
        >>> stream = request1.serialize()
        >>> request2 = ModbusRtuResponse.deserialize(stream)
        >>> assert request1 == request2
    """

    _pdu_parser = ModbusPduParser

    def __init__(self, slave_id, pdu):
        """Initialize the Modbus RTU Response Packet."""

        # Set the instance attributes
        self.slave_id = slave_id
        self.pdu = pdu
        self.crc = 0xFFFF

    def __str__(self):
        """Return a string representation of the Modbus RTU Response Packet"""
        msg = "MODBUS RTU RSP: (Slave ID: {0}, {1}, CRC: {2})"
        return msg.format(self.slave_id, self.pdu, self.crc)

    @classmethod
    def get_parser(cls):
        """Get the PDU parser.

        Returns:
            type : The PDU parser
        """
        return cls._pdu_parser

    @classmethod
    def set_parser(cls, parser):
        """Set the PDU parser

        Args:
            parser (type) : The PDU parser
        """

        if not issubclass(parser, ModbusPduParserAbc):
            message = "The parser must be a subclass of ModbusPduParserAbc"
            raise ModbusPacketError(message)

        cls._pdu_parser = parser

    def set_crc(self, value):
        """Set the Modbus CRC"""
        self.crc = value

    def calc_crc(self):
        """Calculate the Modbus CRC over the slave id and the PDU.

        The checksum covers everything ahead of it in the ADU. The result is
        stored on the packet and returned.

        Returns:
            int : The CRC value
        """

        self.crc = calc_crc16(bytearray([self.slave_id]) + self.pdu.serialize())

        return self.crc

    def serialize(self):
        """Serialize the Modbus RTU Packet to a stream of bytes.

        The checksum is recomputed from the current slave id and PDU, so the
        emitted frame always agrees with itself. Any value previously assigned
        through set_crc() is overwritten.

        Returns:
            bytes : The serialized Modbus RTU Packet
        """

        try:
            # Pack the slave id and the PDU, then checksum what was packed
            slave_id = struct.pack(">B", self.slave_id)
            pdu = self.pdu.serialize()
            self.crc = calc_crc16(slave_id + pdu)
            crc = struct.pack(CRC_FMT, self.crc)

        except Exception as e:
            message = "Error serializing the RTU Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return the packed bytes
        return slave_id + pdu + crc

    @classmethod
    def deserialize(cls, stream, verify_crc=True):
        """Deserialize the Modbus RTU Packet.

        Args:
            stream (bytes)      : The stream of bytes to deserialize
            verify_crc (bool)   : Check the frame against its own checksum.
                                  Pass False to accept a corrupt frame, which
                                  tests constructing one need.

        Returns:
            ModbusRtuResponse() : The Modbus RTU Response Packet

        Raises:
            ModbusPacketError : If the frame contradicts its own checksum
        """

        # Checked before parsing: a corrupt frame is worth rejecting on the
        # checksum rather than on whatever the damaged bytes decode to.
        if verify_crc:
            validate_crc(stream, "RTU Response")

        try:
            # The slave id is the first byte
            (slave_id,) = struct.unpack(">B", stream[:1])

            # The crc is the last two bytes, low byte first
            (crc,) = struct.unpack(CRC_FMT, stream[-CRC_SIZE:])

            # Parse the concrete pdu from the stream
            pdu = cls._pdu_parser.parse_response(stream[1:-CRC_SIZE])

            # Create a new instance of the class
            packet = cls(slave_id=slave_id, pdu=pdu)
            packet.set_crc(crc)

        except Exception as e:
            message = "Error deserializing the RTU Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return the packet
        return packet


################################################################################
# MODBUS TCP PACKETS
################################################################################


def validate_mbap_length(header, stream):
    """Check the MBAP length field against the bytes actually received.

    The length field counts the unit identifier plus the PDU, so a well-formed
    ADU is ModbusHeader.SIZE + length - 1 bytes long. The field arrives from
    the network and is never trusted on its own.

    Args:
        header (ModbusHeader) : The deserialized header
        stream (bytes)        : The complete ADU the header was read from

    Raises:
        ModbusPacketError : If the declared length contradicts the ADU size
    """

    expected = ModbusHeader.SIZE + header.length - 1

    if len(stream) != expected:
        message = (
            "MBAP length field declares {0} byte(s) after the protocol "
            "identifier, implying an ADU of {1} byte(s), but {2} byte(s) "
            "were received"
        ).format(header.length, expected, len(stream))
        raise ModbusPacketError(message)


class ModbusTcpPacket(ModbusPacketAbc):
    """Generic Modbus TCP Packet.

    This is a generic packet that manages serialization and deserialization. It
    is intented to be used by components that do not differentiate between a
    request and a response, such as sniffers, proxies or gateways. In this
    case the message is just forwarded without any processing.

    Args:
        header (ModbusHeaderAbc)    : The Modbus TCP Header
        pdu (ModbusPduAbc)          : The Modbus Request PDU

    Example:
        >>> # Create the required PDU
        >>> pdu = ModbusRequestFC1(start_addr=1, quantity=2)
        >>>
        >>> # Create the Modbus TCP Header and add the unit-id byte to the PDU length
        >>> header = ModbusHeader(length=len(pdu)+1, unit_id=1)
        >>>
        >>> # Create the Modbus TCP Packet
        >>> packet1 = ModbusTcpPacket(header=header, pdu=pdu)
        >>>
        >>> # Serialize the packet
        >>> stream = packet1.serialize()
        >>>
        >>> # Deserialize the packet
        >>> packet2 = ModbusTcpPacket.deserialize(stream)
        >>>
        >>> # Check the frame survives the round trip. Deserializing yields a
        >>> # generic ModbusPdu rather than the ModbusRequestFC1 that went in,
        >>> # which is what this class is for, so compare the bytes and not the
        >>> # objects -- the two hold the same frame in different shapes.
        >>> assert packet2.serialize() == stream
    """

    def __init__(self, header, pdu):
        """Initialize the Modbus TCP Packet."""

        # Set the instance attributes
        self.header = header
        self.pdu = pdu

    def __str__(self):
        """Return a string representation of the Modbus TCP Request Packet."""
        msg = "MODBUS TCP PCKT -> | {0} | {1}"
        return msg.format(self.header, self.pdu)

    def serialize(self):
        """Serialize the generic Modbus TCP Packet to a stream of bytes.

        Returns:
            bytes : The serialized Modbus TCP Packet
        """

        try:
            header_bytes = self.header.serialize()
            pdu_bytes = self.pdu.serialize()

        except Exception as e:
            message = "Error serializing the TCP Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return header_bytes + pdu_bytes

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the generic Modbus TCP Packet.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusPacket() : The Modbus TCP Request Packet
        """

        try:
            # Get the header
            header = ModbusHeader.deserialize(stream[: ModbusHeader.SIZE])

            # Reject a length field that contradicts the received ADU
            validate_mbap_length(header, stream)

            # Get the concrete request PDU
            pdu = ModbusPdu.deserialize(stream[ModbusHeader.SIZE :])

        except Exception as e:
            message = "Error deserializing the TCP Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(header=header, pdu=pdu)


class ModbusTcpRequest(ModbusPacketAbc):
    """Modbus TCP Request.

    A dedicated Modbus TCP Request Packet that manages serialization,
    deserialization and PDU parsing. It is typically by the client to
    send a request to a server that is captured and processed by the server.
    The deserialization on the server side will return the concrete request PDU
    instance whose attributes can be accessed and used to generate a response.

    Args:
        header (ModbusHeaderAbc)   : The Modbus TCP Header
        pdu (ModbusPduAbc)         : The Modbus Request PDU

    Example:
        >>> # Create the required PDU
        >>> pdu = ModbusRequestFC1(start_addr=1, quantity=2)
        >>>
        >>> # Create the Modbus TCP Header and add the unit-id byte to the PDU length
        >>> header = ModbusHeader(length=len(pdu)+1, unit_id=1)
        >>>
        >>> # Create the Modbus TCP Packet
        >>> packet1 = ModbusTcpRequest(header=header, pdu=pdu)
        >>>
        >>>  # Serialize the packet
        >>> stream = packet1.serialize()
        >>>
        >>> # Deserialize the packet
        >>> packet2 = ModbusTcpRequest.deserialize(stream)
        >>>
        >>> # Check if the packets are equal
        >>> assert packet1 == packet2
    """

    _pdu_parser = ModbusPduParser

    def __init__(self, header, pdu):
        """Initialize the Modbus TCP Request Packet"""

        # Set the instance attributes
        self.header = header
        self.pdu = pdu

    def __str__(self):
        """Return a string representation of the Modbus TCP Request Packet."""
        msg = "MODBUS TCP REQ -> | {0} | {1}"
        return msg.format(self.header, self.pdu)

    @classmethod
    def get_parser(cls):
        """Get the PDU parser.

        Returns:
            type : The PDU parser
        """
        return cls._pdu_parser

    @classmethod
    def set_parser(cls, parser):
        """Set the PDU parser.

        Args:
            parser (type) : The PDU parser
        """

        if not issubclass(parser, ModbusPduParserAbc):
            message = "The parser must be a subclass of ModbusPduParserAbc"
            raise ModbusPacketError(message)

        cls._pdu_parser = parser

    def serialize(self):
        """Serialize the Modbus TCP Packet to a stream of bytes.

        Returns:
            bytes : The serialized Modbus TCP Packet
        """

        try:
            header_bytes = self.header.serialize()
            pdu_bytes = self.pdu.serialize()

        except Exception as e:
            message = "Error serializing the TCP Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return header_bytes + pdu_bytes

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the Modbus TCP Packet.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusTcpRequest() : The Modbus TCP Request Packet
        """

        try:
            # Get the header
            header = ModbusHeader.deserialize(stream[: ModbusHeader.SIZE])

            # Reject a length field that contradicts the received ADU
            validate_mbap_length(header, stream)

            # Get the concrete request PDU
            pdu = cls._pdu_parser.parse_request(stream[ModbusHeader.SIZE :])

        except Exception as e:
            message = "Error deserializing the TCP Request PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(header=header, pdu=pdu)


class ModbusTcpResponse(ModbusPacketAbc):
    """Modbus TCP Response.

    A dedicated Modbus TCP Request Packet that manages serialization,
    deserialization and PDU parsing. It is typically by the server to
    send a response to a client that is captured and processed by the client.
    The deserialization on the client side will return the concrete response PDU
    instance whose attributes can be accessed and used to control the state
    of the client.

    Args:
        header (ModbusHeaderAbc)   : The Modbus TCP Header
        pdu (ModbusPduAbc)         : The Modbus Response PDU

    Example:
        >>> # Create the required PDU
        >>> pdu = ModbusResponseFC1(byte_count=2, output_status=(1, 2))
        >>>
        >>> # Create the Modbus TCP Header and add the unit-id byte to the PDU length
        >>> header = ModbusHeader(length=len(pdu)+1, unit_id=1)
        >>>
        >>> # Create the Modbus TCP Packet
        >>> packet1 = ModbusTcpResponse(header=header, pdu=pdu)
        >>>
        >>>  # Serialize the packet
        >>> stream = packet1.serialize()
        >>>
        >>> # Deserialize the packet
        >>> packet2 = ModbusTcpResponse.deserialize(stream)
        >>>
        >>> # Check if the packets are equal
        >>> assert packet1 == packet2
    """

    _pdu_parser = ModbusPduParser

    def __init__(self, header, pdu):
        """Initialize the Modbus TCP Response Packet."""

        # Set the instance attributes
        self.header = header
        self.pdu = pdu

    def __str__(self):
        """Return a string representation of the Modbus TCP Response Packet"""
        msg = "MODBUS TCP RSP -> | {0} | {1}"
        return msg.format(self.header, self.pdu)

    @classmethod
    def get_parser(cls):
        """Get the PDU parser.

        Returns:
            type : The PDU parser
        """
        return cls._pdu_parser

    @classmethod
    def set_parser(cls, parser):
        """Set the PDU parser.

        Args:
            parser (type) : The PDU parser
        """

        if not issubclass(parser, ModbusPduParserAbc):
            message = "The parser must be a subclass of ModbusPduParserAbc"
            raise ModbusPacketError(message)

        cls._pdu_parser = parser

    def serialize(self):
        """Serialize the Modbus TCP Packet to a stream of bytes.

        Returns:
            bytes : The serialized Modbus TCP Packet
        """

        try:
            header_bytes = self.header.serialize()
            pdu_bytes = self.pdu.serialize()

        except Exception as e:
            message = "Error serializing the TCP Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        return header_bytes + pdu_bytes

    @classmethod
    def deserialize(cls, stream):
        """Deserialize the Modbus TCP Packet.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusTcpResponse() : The Modbus TCP Response Packet
        """

        try:
            # Get the header
            header = ModbusHeader.deserialize(stream[: ModbusHeader.SIZE])

            # Reject a length field that contradicts the received ADU
            validate_mbap_length(header, stream)

            # Get the concrete request PDU
            pdu = cls._pdu_parser.parse_response(stream[ModbusHeader.SIZE :])

        except Exception as e:
            message = "Error deserializing the TCP Response PDU: {0}".format(e)
            raise ModbusPacketError(message)

        # Return a new instance of the class
        return cls(header=header, pdu=pdu)


################################################################################
# REGISTER PDU CLASSES
################################################################################

ModbusPduParser.register(ModbusRequestFC1)
ModbusPduParser.register(ModbusResponseFC1)
ModbusPduParser.register(ModbusRequestFC2)
ModbusPduParser.register(ModbusResponseFC2)
ModbusPduParser.register(ModbusRequestFC3)
ModbusPduParser.register(ModbusResponseFC3)
ModbusPduParser.register(ModbusRequestFC4)
ModbusPduParser.register(ModbusResponseFC4)
ModbusPduParser.register(ModbusRequestFC5)
ModbusPduParser.register(ModbusResponseFC5)
ModbusPduParser.register(ModbusRequestFC6)
ModbusPduParser.register(ModbusResponseFC6)
ModbusPduParser.register(ModbusRequestFC7)
ModbusPduParser.register(ModbusResponseFC7)
ModbusPduParser.register(ModbusRequestFC8)
ModbusPduParser.register(ModbusResponseFC8)
ModbusPduParser.register(ModbusRequestFC15)
ModbusPduParser.register(ModbusResponseFC15)
ModbusPduParser.register(ModbusRequestFC16)
ModbusPduParser.register(ModbusResponseFC16)
ModbusPduParser.register(ModbusRequestFC22)
ModbusPduParser.register(ModbusResponseFC22)
ModbusPduParser.register(ModbusRequestFC23)
ModbusPduParser.register(ModbusResponseFC23)
ModbusPduParser.register(ModbusRequestFC43)
ModbusPduParser.register(ModbusResponseFC43)
