"""Modbus Packet Classes.

Packet classes for Modbus TCP and Modbus RTU, following the Modbus Application
Protocol Specification. The banners below divide the module into constraints,
the abstract and base classes, the parser, and the function-code classes.

A custom PDU subclasses ModbusPdu and registers with ModbusPduParser, giving
its format string, function code and PDU identifier. That identifier runs
0x0001 to 0x7FFF for a request and 0x8001 to 0xFFFF for a response, with
0x8000 reserved for the error PDU.
"""

from __future__ import annotations

import struct
import warnings
from abc import ABCMeta, abstractmethod
from typing import ClassVar

from .errors import ModbusPacketError, ModbusPduParseError

################################################################################
# CONSTRAINTS
################################################################################


class ModbusViolation:
    """A constraint a packet component does not satisfy.

    A finding carries the rule's identity rather than only a message, so a
    test grading a peer can assert which bound was crossed. Building a frame
    that breaks a rule stays possible: this reports, it does not prevent.

    Args:
        source (str) : The component that declared the constraint
        field (str)  : The field carrying the offending value
        rule (str)   : The constraint, as the specification states it
        value (int)  : The value that broke it

    Example:
        >>> pdu = ModbusRequestFC3(start_addr=0, quantity=126)
        >>> finding = pdu.violations()[0]
        >>> finding.field
        'quantity'
    """

    def __init__(self, source: str, field: str, rule: str, value: int) -> None:
        """Initialize the violation."""
        self.source = source
        self.field = field
        self.rule = rule
        self.value = value

    def __eq__(self, other: object) -> bool:
        """Check if two violations report the same finding."""
        return self.__dict__ == other.__dict__

    def __ne__(self, other: object) -> bool:
        """Check if two violations report different findings."""
        return not self.__eq__(other)

    def __str__(self) -> str:
        """Return a string representation of the violation."""
        msg = "{0}.{1} is {2}; the specification requires {3}"
        return msg.format(self.source, self.field, self.value, self.rule)

    def __repr__(self) -> str:
        """Return the same text the string form carries."""
        return f"ModbusViolation({self})"


################################################################################
# ABSTRACT CLASSES
################################################################################


class ModbusPacketAbc(metaclass=ABCMeta):
    """Abstract class for Modbus Packets."""

    # Field name to inclusive low and high, from the specification. Empty
    # states that it bounds nothing here, which is not the same as unread.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}

    # The attributes holding components this one carries, so asking a packet
    # for its findings returns the parts' findings too.
    PARTS: ClassVar[tuple[str, ...]] = ()

    def _finding(self, field: str, rule: str) -> ModbusViolation:
        """Build a finding naming this component and one of its fields.

        Args:
            field (str) : The field carrying the offending value
            rule (str)  : The constraint, as the specification states it

        Returns:
            ModbusViolation : The finding
        """
        return ModbusViolation(
            source=type(self).__name__,
            field=field,
            rule=rule,
            value=getattr(self, field),
        )

    def _fixed_count(self, field: str, expected: int, rule: str) -> tuple[ModbusViolation, ...]:
        """Report a count that disagrees with what the other fields imply.

        Args:
            field (str)    : The counting field
            expected (int) : What the other fields fix it at
            rule (str)     : The constraint, as the specification states it

        Returns:
            tuple : One finding, or empty when the count agrees
        """
        if getattr(self, field) == expected:
            return ()

        return (self._finding(field, f"{rule}, which is {expected}"),)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report every constraint this packet and its parts break.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        found = []

        for field in sorted(self.LIMITS):
            low, high = self.LIMITS[field]
            value = getattr(self, field)

            if not low <= value <= high:
                # A field the specification fixes at one value reads as that
                # value rather than as a range running from it to itself.
                rule = f"0x{low:04X}"

                if low != high:
                    rule = f"{rule} to 0x{high:04X}"

                found.append(self._finding(field, rule))

        for part in self.PARTS:
            component = getattr(self, part, None)

            if component is not None:
                found.extend(component.violations())

        return tuple(found)

    def validate(self) -> None:
        """Raise unless the packet and its parts are conforming.

        Raises:
            ModbusPacketError : If any constraint is broken, naming each one
        """
        found = self.violations()

        if found:
            raise ModbusPacketError("; ".join(str(finding) for finding in found))

    def __eq__(self, other: object) -> bool:
        """Check if two packets are equal."""
        return self.__dict__ == other.__dict__

    def __ne__(self, other: object) -> bool:
        """Check if two packets are not equal."""
        return not self.__eq__(other)

    # No tuning parameters here or below: a packet knows its own wire layout,
    # and a caller handing one in could ask for a frame the spec disallows.
    @abstractmethod
    def serialize(self) -> bytes:
        """Serialize the packet and return a stream of bytes.

        Returns:
            bytes : The serialized packet
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def deserialize(cls, stream: bytes) -> ModbusPacketAbc:
        """Deserialize the packet from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusPacketAbc : The deserialized packet
        """
        raise NotImplementedError


class ModbusPduParserAbc(metaclass=ABCMeta):
    """Abstract class for Modbus PDU Parser."""

    @classmethod
    @abstractmethod
    def parse_request(cls, stream: bytes) -> ModbusPdu:
        """Parse the Modbus Request PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to parse

        Returns:
            ModbusPdu : The Modbus PDU object
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def parse_response(cls, stream: bytes) -> ModbusPdu:
        """Parse the Modbus Response PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to parse

        Returns:
            ModbusPdu : The Modbus PDU object
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

    # Zero for every Modbus frame, per the Messaging Implementation Guide
    # v1.0b. The other three header fields carry no stated bound.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"prot_id": (0x0000, 0x0000)}

    def __init__(self, trans_id: int = 0, prot_id: int = 0, length: int = 0, unit_id: int = 0) -> None:
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

    def __len__(self) -> int:
        """Return the length of the header."""
        return struct.calcsize(self.HEADER_FMT)

    def __str__(self) -> str:
        """Return a string representation of the header."""
        msg = "HEADER: (Trans-ID: {0}, Prot-ID: {1}, Length: {2}, Unit-ID: {3})"
        return msg.format(self.trans_id, self.prot_id, self.length, self.unit_id)

    def serialize(self) -> bytes:
        """Serialize the header to a stream of bytes.

        Returns:
            bytes : The serialized header
        """
        try:
            stream = struct.pack(self.HEADER_FMT, self.trans_id, self.prot_id, self.length, self.unit_id)

        except struct.error as e:
            message = f"Error serializing the Modbus Header: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusHeader:
        """Deserialize the header from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusHeader : The Modbus Header object
        """
        try:
            # Unpack the header bytes
            header = struct.unpack(cls.HEADER_FMT, stream)

        except struct.error as e:
            message = f"Error deserializing the Modbus Header: {e}"
            raise ModbusPacketError(message) from e

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
        data (tuple or bytes) : The PDU payload, either as a tuple of values
            or as the finished bytes. Bytes are the wider input: they carry
            any sequence, where a tuple carries what the format string can
            describe. A subclass declaring PDU_FIELDS derives its payload
            from those fields and ignores this argument

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

    # Models no function code, so the specification bounds nothing. Declared
    # rather than inherited, which would not be tellable from unread.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}

    # The named fields in wire order. None means the class stores its payload
    # rather than deriving one, which is what a class with no function code does.
    PDU_FIELDS: ClassVar[tuple[str, ...] | None] = None

    # The trailing field holding a sequence that flattens into the payload,
    # or None where the layout is scalars only.
    PDU_TAIL: ClassVar[str | None] = None

    def __init__(self, fc: int, data: tuple[int, ...] | bytes | bytearray | None = None) -> None:
        """Initialize the Modbus PDU."""
        self.fc = fc

        # A class with named fields reads its payload back from them, so
        # storing the argument would restore the copy the property removes.
        if self.PDU_FIELDS is None:
            self.data = () if data is None else data

    def _field_names(self) -> list[str]:
        """Name every field the payload is derived from, in wire order.

        Returns:
            list : The declared field names, empty where the class carries none
        """
        names = list(self.PDU_FIELDS or ())

        if self.PDU_TAIL is not None:
            names.append(self.PDU_TAIL)

        return names

    @property
    def data(self) -> tuple[int, ...]:
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
    def data(self, value: tuple[int, ...] | bytes | bytearray) -> None:
        """Store the payload, or refuse where the class derives it.

        Args:
            value (tuple or bytes) : The payload to store

        Raises:
            ModbusPacketError : If the class derives its payload from fields
        """
        if self.PDU_FIELDS is not None:
            names = self._field_names()
            instead = "set " + ", ".join(names) if names else "it carries none"
            message = f"{type(self).__name__} derives data from its named fields; {instead}"
            raise ModbusPacketError(message)

        # Held as the tuple of byte values, the form deserialize() produces,
        # so a packet built from bytes equals one read back from its output.
        if isinstance(value, (bytes, bytearray)):
            value = tuple(value)

        self._data = value

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.data)))

    def __str__(self) -> str:
        """Return a string representation of the PDU."""
        msg = "PDU: (FC: {0:02d}, Data: {1})"
        return msg.format(self.fc, self.data)

    def is_request(self) -> bool:
        """Check if the PDU is a request."""
        return self.PDU_ID < 0x8000

    def pack(self, fmt: str) -> bytes:
        """Pack under an explicit format string.

        Deprecated. Put the finished bytes in data instead, which expresses
        every layout a format string can and every layout it cannot. Removed
        in 0.6.0.

        Args:
            fmt (str)   : The format string to pack under

        Returns:
            bytes : The packed PDU
        """
        warnings.warn(
            "ModbusPdu.pack is deprecated and is removed in 0.6.0; build the bytes and pass them as data instead",
            DeprecationWarning,
            stacklevel=2,
        )

        return self._pack(fmt)

    @classmethod
    def unpack(cls, stream: bytes, fmt: str) -> ModbusPdu:
        """Unpack under an explicit format string.

        Deprecated. Use deserialize(), which reads the payload as bytes.
        Removed in 0.6.0.

        Args:
            stream (bytes)  : The stream of bytes to unpack
            fmt (str)       : The format string to unpack under

        Returns:
            ModbusPdu : The Modbus PDU object
        """
        warnings.warn(
            "ModbusPdu.unpack is deprecated and is removed in 0.6.0; use "
            "deserialize(), which reads the payload as bytes",
            DeprecationWarning,
            stacklevel=2,
        )

        return cls._unpack(stream, fmt)

    def _pack(self, fmt: str) -> bytes:
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

        except struct.error as e:
            message = f"Error serializing the Modbus PDU: {e}"
            raise ModbusPacketError(message) from e

        # Return the packed bytes
        return packed_bytes

    @classmethod
    def _unpack(cls, stream: bytes, fmt: str) -> ModbusPdu:
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

        except struct.error as e:
            message = f"Error deserializing the Modbus PDU: {e}"
            raise ModbusPacketError(message) from e

        # Return a new instance of the class
        return cls(fc, data)

    def serialize(self) -> bytes:
        """Serialize the PDU to a stream of bytes.

        Returns:
            bytes : The serialized PDU

        Raises:
            ModbusPacketError : If the data field carries no length
        """
        # The format is built here, so a non-sequence fails before pack() is
        # entered, where a TypeError would escape callers catching ModbusPacketError.
        try:
            pdu_format = self.PDU_FORMAT.format(len(self.data))

        except TypeError as error:
            message = f"Error serializing the Modbus PDU: {error}"
            raise ModbusPacketError(message) from error

        return self._pack(pdu_format)

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusPdu:
        """Deserialize the PDU from a stream of bytes.

        Args:
            stream (bytes)  : The stream of bytes to deserialize

        Returns:
            ModbusPdu : The Modbus PDU object

        Raises:
            ModbusPacketError : If the stream carries no length
        """
        # First byte the function code, the rest data. Measured here, so a
        # stream that cannot be measured is converted here too.
        try:
            pdu_format = cls.PDU_FORMAT.format(len(stream) - 1)

        except TypeError as error:
            message = f"Error deserializing the Modbus PDU: {error}"
            raise ModbusPacketError(message) from error

        return cls._unpack(stream, pdu_format)


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

    # One shared table keyed by function code, populated by register() at the
    # end of this module. ClassVar says so: a parser instance never owns one.
    _registry: ClassVar[dict[int, type[ModbusPdu]]] = {}

    @classmethod
    def register(cls, pdu_class: type[ModbusPdu]) -> None:
        """Register a Modbus PDU.

        Args:
            pdu_class (type) : The Modbus PDU to register

        """
        if not issubclass(pdu_class, ModbusPdu):
            message = "The class must be a subclass of ModbusPdu"
            raise ModbusPacketError(message)

        cls._registry[pdu_class.PDU_ID] = pdu_class

    @classmethod
    def unregister(cls, pdu_class: type[ModbusPdu]) -> None:
        """Unregister a Modbus PDU.

        Args:
            pdu_class (type) : The Modbus PDU to unregister
        """
        if not issubclass(pdu_class, ModbusPdu):
            message = "The class must be a subclass of ModbusPdu"
            raise ModbusPacketError(message)

        del cls._registry[pdu_class.PDU_ID]

    @classmethod
    def set_registry(cls, registry: dict[int, type[ModbusPdu]]) -> None:
        """Set the Modbus PDU registry.

        Args:
            registry (dict) : The Modbus PDU registry
        """
        cls._registry = registry

    @classmethod
    def get_registry(cls) -> dict[int, type[ModbusPdu]]:
        """Get the Modbus PDU registry.

        Returns:
            dict : The Modbus PDU registry
        """
        return cls._registry

    @classmethod
    def clear_registry(cls) -> None:
        """Clear the Modbus PDU registry."""
        cls._registry.clear()

    @classmethod
    def parse_request(cls, stream: bytes) -> ModbusPdu:
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

        except struct.error as e:
            message = f"Error parsing the Modbus Request: {e}"
            raise ModbusPacketError(message) from e

        # Return the deserialized PDU
        return pdu.deserialize(stream)

    @classmethod
    def parse_response(cls, stream: bytes) -> ModbusPdu:
        """Parse a Modbus PDU Response from a stream of bytes.

        Args:
            stream (bytes) : The stream of bytes to parse
        """
        try:
            # Get the function code from the stream (first byte)
            func_code = struct.unpack(">B", stream[:1])[0]

            pdu: type[ModbusPdu] | ModbusPdu

            # Check if the function code is an error
            if func_code >= 0x80:
                pdu = ModbusError.deserialize(stream)

            else:
                # Dispatch on the function code. An exception response
                # carries 0x8000 to 0x807F, 0x8000 being the error PDU.
                pdu = cls._registry.get(func_code + 0x8000, ModbusPdu)

        except (ModbusPacketError, struct.error) as e:
            message = f"Error parsing the Modbus Response: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("exc_code",)
    ERROR_MASK = 0x80

    def __init__(self, fc: int, exc_code: int) -> None:
        """Initialize the Modbus Error PDU."""
        # Set instance attributes
        self.exc_code = exc_code

        # Call parent constructor
        super().__init__(
            fc=fc,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def __str__(self) -> str:
        """Return a string representation of the Modbus Error PDU."""
        msg = "ERROR: (Function Code: {0}, Exception Code: {1})"
        return msg.format(self.fc, self.exc_code)

    def serialize(self) -> bytes:
        """Serialize the error PDU to a stream of bytes.

        Returns:
            bytes : The serialized error PDU
        """
        try:
            # Add 0x80 (error mask) to the function code and pack it
            func_code = struct.pack(">B", self.fc + self.ERROR_MASK)

            # Pack the exception code
            exc_code = struct.pack(">B", self.exc_code)

        except (struct.error, TypeError) as e:
            message = f"Error serializing the Modbus Error PDU: {e}"
            raise ModbusPacketError(message) from e

        # Return the packed bytes
        return func_code + exc_code

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusError:
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

        except struct.error as e:
            message = f"Error deserializing the Modbus Error PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Read Coils: 1 to 2000 coils.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"quantity": (0x0001, 0x07D0)}
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr: int, quantity: int) -> None:
        """Initialize the Modbus Request FC1 PDU."""
        # Set instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call parent constructor
        super().__init__(
            fc=0x01,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the request FC1 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC1 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC1 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC1:
        """Deserialize the request FC1 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC1() : The Modbus Request FC1 PDU
        """
        try:
            # Unpack the PDU bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC1 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification's rule here ties fields together or names a value
    # set, so it lives in violations() below rather than in a range.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "output_status"

    def __init__(self, byte_count: int, output_status: tuple[int, ...]) -> None:
        """Hold the byte count and the coil states the response carries."""
        # Set instance attributes
        self.byte_count = byte_count
        self.output_status = tuple(output_status)

        # Call parent constructor
        super().__init__(
            fc=0x01,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(self.byte_count))

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Read Coils: the byte count is the number of status bytes returned.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        return tuple(
            list(super().violations())
            + list(self._fixed_count("byte_count", len(self.output_status), "the number of status bytes"))
        )

    def serialize(self) -> bytes:
        """Serialize the response FC1 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC1 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(self.byte_count))

        except ModbusPacketError as e:
            message = f"Error serializing the FC1 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC1:
        """Deserialize the response FC1 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC1() : The Modbus Response FC1 PDU
        """
        try:
            # Layout: FC(1) + byte count(1) + output status bytes.
            pdu_data_length = len(stream) - 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(pdu_data_length)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the output status
            output_status = pdu[2:]

        except struct.error as e:
            message = f"Error deserializing the FC1 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Read Discrete Inputs: 1 to 2000 inputs.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"quantity": (0x0001, 0x07D0)}
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr: int, quantity: int) -> None:
        """Initialize the Modbus Request FC2 PDU."""
        # Set instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call parent constructor
        super().__init__(
            fc=0x02,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the request FC2 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC2 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC2 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC2:
        """Deserialize the request FC2 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC2() : The Modbus Request FC2 PDU
        """
        try:
            # Unpack the PDU bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC2 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification's rule here ties fields together or names a value
    # set, so it lives in violations() below rather than in a range.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "input_status"

    def __init__(self, byte_count: int, input_status: tuple[int, ...]) -> None:
        """Initialize the Modbus Response FC2 PDU."""
        # Set the instance attributes
        self.byte_count = byte_count
        self.input_status = tuple(input_status)

        # Call the parent constructor
        super().__init__(
            fc=0x02,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(self.byte_count))

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Read Discrete Inputs: the byte count is the number of status bytes returned.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        return tuple(
            list(super().violations())
            + list(self._fixed_count("byte_count", len(self.input_status), "the number of status bytes"))
        )

    def serialize(self) -> bytes:
        """Serialize the response FC2 PDU from a stream of bytes.

        Returns:
            bytes : The serialized response FC2 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(self.byte_count))

        except ModbusPacketError as e:
            message = f"Error serializing the FC2 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC2:
        """Deserialize the response FC2 PDU to a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC2() : The Modbus Response FC2 PDU
        """
        try:
            # Layout: FC(1) + byte count(1) + input status bytes.
            pdu_data_length = len(stream) - 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(pdu_data_length)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the input status
            input_status = pdu[2:]

        except struct.error as e:
            message = f"Error deserializing the FC2 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Read Holding Registers: 1 to 125 registers.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"quantity": (0x0001, 0x007D)}
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr: int, quantity: int) -> None:
        """Initialize the Modbus Request FC3 PDU."""
        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call the parent constructor
        super().__init__(
            fc=0x03,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the request FC3 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC3 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC3 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC3:
        """Deserialize the request FC3 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC3() : The Modbus Request FC3 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC3 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification's rule here ties fields together or names a value
    # set, so it lives in violations() below rather than in a range.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "values"

    def __init__(self, byte_count: int, values: tuple[int, ...]) -> None:
        """Initialize the Modbus Response FC3 PDU."""
        # Set the instance attributes
        self.byte_count = byte_count
        self.values = tuple(values)

        # Call the parent constructor
        super().__init__(
            fc=0x03,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.values)))

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Read Holding Registers: the byte count is twice the registers returned.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        return tuple(
            list(super().violations())
            + list(self._fixed_count("byte_count", 2 * len(self.values), "twice the registers returned"))
        )

    def serialize(self) -> bytes:
        """Serialize the response FC3 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC3 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.values)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC3 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC3:
        """Deserialize the response FC3 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC3() : The Modbus Response FC3 PDU
        """
        try:
            # Layout: FC(1) + byte count(1) + register values(2 each).

            reg_count = (len(stream) - 2) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(reg_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the register values
            values = pdu[2:]

        except struct.error as e:
            message = f"Error deserializing the FC3 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Read Input Registers: 1 to 125 registers.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"quantity": (0x0001, 0x007D)}
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr: int, quantity: int) -> None:
        """Initialize the Modbus Request FC4 PDU."""
        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call the parent constructor
        super().__init__(
            fc=0x04,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the request FC4 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC4 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC4 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC4:
        """Deserialize the request FC4 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC4() : The Modbus Request FC4 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC4 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification's rule here ties fields together or names a value
    # set, so it lives in violations() below rather than in a range.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "values"

    def __init__(self, byte_count: int, values: tuple[int, ...]) -> None:
        """Initialize the Modbus Response FC4 PDU."""
        # Set the instance attributes
        self.byte_count = byte_count
        self.values = tuple(values)

        # Call the parent constructor
        super().__init__(
            fc=0x04,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.values)))

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Read Input Registers: the byte count is twice the registers returned.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        return tuple(
            list(super().violations())
            + list(self._fixed_count("byte_count", 2 * len(self.values), "twice the registers returned"))
        )

    def serialize(self) -> bytes:
        """Serialize the response FC4 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC4 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.values)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC4 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC4:
        """Deserialize the response FC4 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC4() : The Modbus Response FC4 PDU
        """
        try:
            # Layout: FC(1) + byte count(1) + register values(2 each).

            reg_count = (len(stream) - 2) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(reg_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the register values
            values = pdu[2:]

        except struct.error as e:
            message = f"Error deserializing the FC4 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification's rule here ties fields together or names a value
    # set, so it lives in violations() below rather than in a range.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("output_address", "output_value")

    def __init__(self, output_address: int, output_value: int) -> None:
        """Initialize the Modbus Request FC5 PDU."""
        # Set the instance attributes
        self.output_address = output_address
        self.output_value = output_value

        # Call the parent constructor
        super().__init__(
            fc=0x05,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Write Single Coil: the output value is 0x0000 or 0xFF00.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        found = list(super().violations())

        if self.output_value not in (0x0000, 0xFF00):
            found.append(self._finding("output_value", "0x0000 or 0xFF00"))

        return tuple(found)

    def serialize(self) -> bytes:
        """Serialize the request FC5 PDU from a stream of bytes.

        Returns:
            bytes : The serialized request FC5 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC5 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC5:
        """Deserialize the request FC5 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC5() : The Modbus Request FC5 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC5 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification's rule here ties fields together or names a value
    # set, so it lives in violations() below rather than in a range.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("output_address", "output_value")

    def __init__(self, output_address: int, output_value: int) -> None:
        """Initialize the Modbus Response FC5 PDU."""
        # Set the instance attributes
        self.output_address = output_address
        self.output_value = output_value

        # Call the parent constructor
        super().__init__(
            fc=0x05,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Write Single Coil echoes the request, so the same value rule holds.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        found = list(super().violations())

        if self.output_value not in (0x0000, 0xFF00):
            found.append(self._finding("output_value", "0x0000 or 0xFF00"))

        return tuple(found)

    def serialize(self) -> bytes:
        """Serialize the response FC5 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC5 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC5 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC5:
        """Deserialize the response FC5 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC5() : The Modbus Response FC5 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(">BHH", stream)

        except struct.error as e:
            message = f"Error deserializing the FC5 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("output_address", "output_value")

    def __init__(self, output_address: int, output_value: int) -> None:
        """Initialize the Modbus Request FC6 PDU."""
        # Set the instance attributes
        self.output_address = output_address
        self.output_value = output_value

        # Call the parent constructor
        super().__init__(
            fc=0x06,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the request FC6 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC6 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC6 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC6:
        """Deserialize the request FC6 PDU.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC6() : The Modbus Request FC6 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC6 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("output_address", "output_value")

    def __init__(self, output_address: int, output_value: int) -> None:
        """Initialize the Modbus Response FC6 PDU."""
        # Set the instance attributes
        self.output_address = output_address
        self.output_value = output_value

        # Call the parent constructor
        super().__init__(
            fc=0x06,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the response FC6 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC6 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC6 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC6:
        """Deserialize the response FC6 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC6() : The Modbus Response FC6 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC6 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ()

    def __init__(self) -> None:
        """Initialize the Modbus Request FC7 PDU."""
        # Call the parent constructor
        super().__init__(
            fc=0x07,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the request FC7 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC7 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC7 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC7:
        """Deserialize the request FC7 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC7() : The Modbus Request FC7 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC7 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("status",)

    def __init__(self, status: int) -> None:
        """Initialize the Modbus Response FC7 PDU."""
        # Set the instance attributes
        self.status = status

        # Call the parent constructor
        super().__init__(
            fc=0x07,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the response FC7 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC7 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC7 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC7:
        """Deserialize the response FC7 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC7() : The Modbus Response FC7 PDU
        """
        try:
            # Unpack the pdu
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC7 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("sub_func",)
    PDU_TAIL = "subfunc_data"

    def __init__(self, sub_func: int, subfunc_data: tuple[int, ...]) -> None:
        """Initialize the Modbus Request FC8 PDU."""
        # Set the instance attributes
        self.sub_func = sub_func
        self.subfunc_data = tuple(subfunc_data)

        # Call the parent constructor
        super().__init__(
            fc=0x08,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.subfunc_data)))

    def serialize(self) -> bytes:
        """Serialize the request FC8 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC8 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.subfunc_data)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC8 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC8:
        """Deserialize the request FC8 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC8() : The Modbus Request FC8 PDU
        """
        try:
            # Layout: FC(1) + sub-function(2) + data bytes.
            data_count = (len(stream) - 3) // 2

            pdu_format = cls.PDU_FORMAT.format(data_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Get the sub-function
            sub_func = pdu[1]

            # Get the data
            subfunc_data = pdu[2:]

        except struct.error as e:
            message = f"Error deserializing the FC8 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("sub_func",)
    PDU_TAIL = "subfunc_data"

    def __init__(self, sub_func: int, subfunc_data: tuple[int, ...]) -> None:
        """Initialize the Modbus Response FC8 PDU."""
        # Set the instance attributes
        self.sub_func = sub_func
        self.subfunc_data = tuple(subfunc_data)

        # Call the parent constructor
        super().__init__(
            fc=0x08,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT.format(len(self.subfunc_data)))

    def serialize(self) -> bytes:
        """Serialize the response FC8 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC8 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.subfunc_data)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC8 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC8:
        """Deserialize the response FC8 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC8() : The Modbus Response FC8 PDU
        """
        try:
            # Layout: FC(1) + sub-function(2) + data bytes.

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

        except struct.error as e:
            message = f"Error deserializing the FC8 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Write Multiple Coils: 1 to 1968 coils.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"quantity": (0x0001, 0x07B0)}
    PDU_FIELDS = ("start_addr", "quantity", "byte_count")
    PDU_TAIL = "values"

    def __init__(self, start_addr: int, quantity: int, byte_count: int, values: tuple[int, ...]) -> None:
        """Initialize the Modbus Request FC15 PDU."""
        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity
        self.byte_count = byte_count
        self.values = tuple(values)

        super().__init__(
            fc=0x0F,
        )

    def __len__(self) -> int:
        """The PDU's wire length, which varies with the number of values."""
        fmt = self.PDU_FORMAT.format(len(self.values))
        return struct.calcsize(fmt)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Write Multiple Coils: the byte count is the quantity in whole bytes.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        # The specification writes this as N = quantity / 8, and N = N + 1
        # where the remainder is not zero.
        whole_bytes = -(-self.quantity // 8)

        return tuple(
            list(super().violations())
            + list(self._fixed_count("byte_count", whole_bytes, "the quantity rounded up to whole bytes"))
        )

    def serialize(self) -> bytes:
        """Serialize the request FC15 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC15 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.values)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC15 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC15:
        """Deserialize the request FC15 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC15() : The Modbus Request FC15 PDU
        """
        try:
            # Layout: FC(1) + start address(2) + quantity(2) + byte count(1) + output status bytes.

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

        except struct.error as e:
            message = f"Error deserializing the FC15 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Write Multiple Coils echoes the quantity written.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"quantity": (0x0001, 0x07B0)}
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr: int, quantity: int) -> None:
        """Initialize the Modbus Response FC15 PDU."""
        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call the parent constructor
        super().__init__(
            fc=0x0F,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the response FC15 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC15 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC15 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC15:
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

        except struct.error as e:
            message = f"Error deserializing the FC15 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Write Multiple Registers: 1 to 123 registers.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"quantity": (0x0001, 0x007B)}
    PDU_FIELDS = ("start_addr", "quantity", "byte_count")
    PDU_TAIL = "values"

    def __init__(self, start_addr: int, quantity: int, byte_count: int, values: tuple[int, ...]) -> None:
        """Initialize the Modbus Request FC16 PDU."""
        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity
        self.byte_count = byte_count
        self.values = tuple(values)

        # Call the parent constructor
        super().__init__(
            fc=0x10,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        fmt = self.PDU_FORMAT.format(len(self.values))
        return struct.calcsize(fmt)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Write Multiple Registers: the byte count is twice the quantity.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        return tuple(
            list(super().violations())
            + list(self._fixed_count("byte_count", 2 * self.quantity, "twice the quantity of registers"))
        )

    def serialize(self) -> bytes:
        """Serialize the request FC16 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC16 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.values)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC16 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC16:
        """Deserialize the request FC16 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC16 : The Modbus Request FC16 PDU
        """
        try:
            # Layout: FC(1) + start address(2) + quantity(2) + byte count(1) + register values(2 each).

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

        except struct.error as e:
            message = f"Error deserializing the FC16 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Write Multiple Registers echoes the quantity written.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"quantity": (0x0001, 0x007B)}
    PDU_FIELDS = ("start_addr", "quantity")

    def __init__(self, start_addr: int, quantity: int) -> None:
        """Initialize the Modbus Response FC16 PDU."""
        # Set the instance attributes
        self.start_addr = start_addr
        self.quantity = quantity

        # Call the parent constructor
        super().__init__(
            fc=0x10,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the response FC16 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC16 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC16 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC16:
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

        except struct.error as e:
            message = f"Error deserializing the FC16 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("ref_addr", "and_mask", "or_mask")

    def __init__(self, ref_addr: int, and_mask: int, or_mask: int) -> None:
        """Initialize the Modbus Request FC22 PDU."""
        # Set the instance attributes
        self.ref_addr = ref_addr
        self.and_mask = and_mask
        self.or_mask = or_mask

        # Call the parent constructor
        super().__init__(
            fc=0x16,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the request FC22 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC22 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC22 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC22:
        """Deserialize the request FC22 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC22() : The Modbus Request FC22 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC22 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("ref_addr", "and_mask", "or_mask")

    def __init__(self, ref_addr: int, and_mask: int, or_mask: int) -> None:
        """Initialize the Modbus Response FC22 PDU."""
        # Set the instance attributes
        self.ref_addr = ref_addr
        self.and_mask = and_mask
        self.or_mask = or_mask

        # Call the parent constructor
        super().__init__(
            fc=0x16,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        return struct.calcsize(self.PDU_FORMAT)

    def serialize(self) -> bytes:
        """Serialize the response FC22 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC22 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT)

        except ModbusPacketError as e:
            message = f"Error serializing the FC22 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC22:
        """Deserialize the response FC22 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC22() : The Modbus Response FC22 PDU
        """
        try:
            # Unpack the PDU from the stream of bytes
            pdu = struct.unpack(cls.PDU_FORMAT, stream)

        except struct.error as e:
            message = f"Error deserializing the FC22 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Read/Write Multiple Registers: 1 to 125 read, 1 to 121 written.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {
        "read_quantity": (0x0001, 0x007D),
        "write_quantity": (0x0001, 0x0079),
    }
    PDU_FIELDS = ("read_start_addr", "read_quantity", "write_start_addr", "write_quantity", "write_byte_count")
    PDU_TAIL = "write_values"

    def __init__(
        self,
        read_start_addr: int,
        read_quantity: int,
        write_start_addr: int,
        write_quantity: int,
        write_byte_count: int,
        write_values: tuple[int, ...],
    ) -> None:
        """Initialize the Modbus Request FC23 PDU."""
        # Set the instance attributes
        self.read_start_addr = read_start_addr
        self.read_quantity = read_quantity
        self.write_start_addr = write_start_addr
        self.write_quantity = write_quantity
        self.write_byte_count = write_byte_count
        self.write_values = tuple(write_values)

        # Call the parent constructor
        super().__init__(
            fc=0x17,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        fmt = self.PDU_FORMAT.format(len(self.write_values))
        return struct.calcsize(fmt)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Read/Write Multiple Registers:
        the write byte count is twice the quantity written.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        return tuple(
            list(super().violations())
            + list(
                self._fixed_count(
                    "write_byte_count",
                    2 * self.write_quantity,
                    "twice the quantity of registers written",
                )
            )
        )

    def serialize(self) -> bytes:
        """Serialize the request FC23 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC23 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.write_values)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC23 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC23:
        """Deserialize the request FC23 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC23() : The Modbus Request FC23 PDU
        """
        try:
            # Layout: FC(1) + read start(2) + read quantity(2) + write start(2) + write quantity(2) + write byte
            # count(1) + register values(2 each).

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

        except struct.error as e:
            message = f"Error deserializing the FC23 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # The specification's rule here ties fields together or names a value
    # set, so it lives in violations() below rather than in a range.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}
    PDU_FIELDS = ("byte_count",)
    PDU_TAIL = "values"

    def __init__(self, byte_count: int, values: tuple[int, ...]) -> None:
        """Initialize the Modbus Response FC23 PDU."""
        # Set the instance attributes
        self.byte_count = byte_count
        self.values = tuple(values)

        # Call the parent constructor
        super().__init__(
            fc=0x17,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        fmt = self.PDU_FORMAT.format(len(self.values))
        return struct.calcsize(fmt)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the rule the specification ties across fields.

        Modbus Application Protocol v1.1b3, Read/Write Multiple Registers: the byte count is twice the registers read.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        return tuple(
            list(super().violations())
            + list(self._fixed_count("byte_count", 2 * len(self.values), "twice the registers read"))
        )

    def serialize(self) -> bytes:
        """Serialize the response FC23 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC23 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.values)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC23 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC23:
        """Deserialize the response FC23 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC23() : The Modbus Response FC23 PDU
        """
        try:
            # Layout: FC(1) + byte count(1) + register values(2 each).

            reg_count = (len(stream) - 2) // 2

            # Generate the format string
            pdu_format = cls.PDU_FORMAT.format(reg_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Extract byte count
            byte_count = pdu[1]

            # Extract the register values
            values = pdu[2:]

        except struct.error as e:
            message = f"Error deserializing the FC23 Response PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Read Device Identification is MEI type 14.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"mei_type": (0x0E, 0x0E)}
    PDU_FIELDS = ("mei_type",)
    PDU_TAIL = "mei_data"

    def __init__(self, mei_type: int, mei_data: tuple[int, ...]) -> None:
        """Initialize the Modbus Request FC43 PDU."""
        # Set the instance attributes
        self.mei_type = mei_type
        self.mei_data = tuple(mei_data)

        # Call the parent constructor
        super().__init__(
            fc=0x2B,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        fmt = self.PDU_FORMAT.format(len(self.mei_data))
        return struct.calcsize(fmt)

    def serialize(self) -> bytes:
        """Serialize the request FC43 PDU to a stream of bytes.

        Returns:
            bytes : The serialized request FC43 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.mei_data)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC43 Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusRequestFC43:
        """Deserialize the request FC43 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusRequestFC43() : The Modbus Request FC43 PDU
        """
        try:
            # Layout: FC(1) + MEI type(1) + MEI data bytes.

            data_count = len(stream) - 2

            pdu_format = cls.PDU_FORMAT.format(data_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Get the MEI type
            mei_type = pdu[1]

            # Get the MEI data
            mei_data = pdu[2:]

        except struct.error as e:
            message = f"Error deserializing the FC43 Request PDU: {e}"
            raise ModbusPacketError(message) from e

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

    # Modbus Application Protocol v1.1b3, Read Device Identification is MEI type 14.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"mei_type": (0x0E, 0x0E)}
    PDU_FIELDS = ("mei_type",)
    PDU_TAIL = "mei_data"

    def __init__(self, mei_type: int, mei_data: tuple[int, ...]) -> None:
        """Initialize the Modbus Response FC43 PDU."""
        # Set the instance attributes
        self.mei_type = mei_type
        self.mei_data = tuple(mei_data)

        # Call the parent constructor
        super().__init__(
            fc=0x2B,
        )

    def __len__(self) -> int:
        """Return the length of the PDU data."""
        fmt = self.PDU_FORMAT.format(len(self.mei_data))
        return struct.calcsize(fmt)

    def serialize(self) -> bytes:
        """Serialize the response FC43 PDU to a stream of bytes.

        Returns:
            bytes : The serialized response FC43 PDU
        """
        try:
            stream = self._pack(self.PDU_FORMAT.format(len(self.mei_data)))

        except ModbusPacketError as e:
            message = f"Error serializing the FC43 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return stream

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusResponseFC43:
        """Deserialize the response FC43 PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusResponseFC43() : The Modbus Response FC43 PDU
        """
        try:
            # Layout: FC(1) + MEI type(1) + MEI data bytes.
            data_count = len(stream) - 2

            pdu_format = cls.PDU_FORMAT.format(data_count)

            # Unpack the pdu
            pdu = struct.unpack(pdu_format, stream)

            # Get the MEI type
            mei_type = pdu[1]

            # Get the MEI data
            mei_data = pdu[2:]

        except struct.error as e:
            message = f"Error deserializing the FC43 Response PDU: {e}"
            raise ModbusPacketError(message) from e

        # Return new instance
        return cls(mei_type=mei_type, mei_data=mei_data)


################################################################################
# MODBUS RTU PACKETS
################################################################################

# Low byte first, unlike every other multi-byte field in Modbus. See
# PLAYBOOK, how the RTU checksum works.
CRC_FMT = "<H"

# Width of the checksum on the wire, in bytes.
CRC_SIZE = struct.calcsize(CRC_FMT)


def calc_crc16(data: bytes | bytearray) -> int:
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


def validate_crc(stream: bytes, packet_name: str) -> int:
    """Check the trailing CRC of an RTU ADU against its own payload.

    Args:
        stream (bytes)      : The complete RTU ADU, checksum included
        packet_name (str)   : The packet description used in the error message

    Returns:
        int : The CRC carried by the frame

    Raises:
        ModbusPacketError : If the frame contradicts its own checksum
    """
    # The shortest ADU is a slave id, a function code and the checksum.
    # Anything shorter has no checksum to slice out.
    if len(stream) < 2 + CRC_SIZE:
        message = (
            f"The {packet_name} is {len(stream)} byte(s) long, too short to carry a slave id, a function code and a CRC"
        )
        raise ModbusPacketError(message)

    (received,) = struct.unpack(CRC_FMT, stream[-CRC_SIZE:])
    expected = calc_crc16(stream[:-CRC_SIZE])

    if received != expected:
        message = (
            f"The {packet_name} carries CRC 0x{received:04X} but its payload "
            f"computes to 0x{expected:04X}, so the frame is corrupt"
        )
        raise ModbusPacketError(message)

    return int(received)


class ModbusRtuRequest(ModbusPacketAbc):
    """Modbus RTU Request.

    The Modbus RTU ADU consists of the slave address, the PDU and the CRC.

    Args:
        slave_id (int)      : The slave id
        pdu (ModbusPdu) : The Modbus Request PDU

    Example:
        >>> pdu = ModbusRequestFC1(start_addr=1, quantity=2)
        >>> request1 = ModbusRtuRequest(slave_id=1, pdu=pdu)
        >>> stream = request1.serialize()
        >>> request2 = ModbusRtuRequest.deserialize(stream)
        >>> assert request1 == request2
    """

    _pdu_parser: ClassVar[type[ModbusPduParserAbc]] = ModbusPduParser

    # Modicon Modbus Protocol Reference Guide PI-MBUS-300: 0 is the broadcast
    # every device recognises, 1 to 247 address one, and 248 to 255 are invalid.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"slave_id": (0x00, 0xF7)}

    # The ADU carries a PDU, whose findings travel with its own.
    PARTS: ClassVar[tuple[str, ...]] = ("pdu",)

    def __init__(self, slave_id: int, pdu: ModbusPdu) -> None:
        """Initialize the Modbus RTU Request Packet."""
        # Set the instance attributes
        self.slave_id = slave_id
        self.pdu = pdu
        self.crc = 0xFFFF

    def __str__(self) -> str:
        """Return a string representation of the Modbus RTU Request Packet."""
        msg = "MODBUS RTU REQ: (Slave ID: {0}, {1}, CRC: {2})"
        return msg.format(self.slave_id, self.pdu, self.crc)

    @classmethod
    def get_parser(cls) -> type[ModbusPduParserAbc]:
        """Get the PDU parser.

        Returns:
            ModbusPduParser : The PDU parser
        """
        return cls._pdu_parser

    @classmethod
    def set_parser(cls, parser: type[ModbusPduParserAbc]) -> None:
        """Set the PDU parser.

        Args:
            parser (type) : The PDU parser
        """
        if not issubclass(parser, ModbusPduParserAbc):
            message = "The parser must be a subclass of ModbusPduParserAbc"
            raise ModbusPacketError(message)

        cls._pdu_parser = parser

    def set_crc(self, value: int) -> None:
        """Set the Modbus CRC."""
        self.crc = value

    def calc_crc(self) -> int:
        """Calculate the Modbus CRC over the slave id and the PDU.

        The checksum covers everything ahead of it in the ADU. The result is
        stored on the packet and returned.

        Returns:
            int : The CRC value
        """
        self.crc = calc_crc16(bytearray([self.slave_id]) + self.pdu.serialize())

        return self.crc

    def serialize(self) -> bytes:
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

        except (ModbusPacketError, struct.error) as e:
            message = f"Error serializing the RTU Request PDU: {e}"
            raise ModbusPacketError(message) from e

        # Return the packed bytes
        return slave_id + pdu + crc

    @classmethod
    def deserialize(cls, stream: bytes, verify_crc: bool = True) -> ModbusRtuRequest:
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

        except (ModbusPacketError, struct.error) as e:
            message = f"Error deserializing the RTU Request PDU: {e}"
            raise ModbusPacketError(message) from e

        # Return the packet
        return packet


class ModbusRtuResponse(ModbusPacketAbc):
    """Modbus RTU Response.

    The Modbus RTU ADU consists of the slave address, the PDU and the CRC.

    Args:
        slave_id (int)      : The slave id
        pdu (ModbusPdu) : The Modbus Response PDU

    Example:
        >>> pdu = ModbusResponseFC1(byte_count=2, output_status=(1, 2))
        >>> request1 = ModbusRtuResponse(slave_id=1, pdu=pdu)
        >>> stream = request1.serialize()
        >>> request2 = ModbusRtuResponse.deserialize(stream)
        >>> assert request1 == request2
    """

    _pdu_parser: ClassVar[type[ModbusPduParserAbc]] = ModbusPduParser

    # Modicon Modbus Protocol Reference Guide PI-MBUS-300: 0 is the broadcast
    # every device recognises, 1 to 247 address one, and 248 to 255 are invalid.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"slave_id": (0x00, 0xF7)}

    # The ADU carries a PDU, whose findings travel with its own.
    PARTS: ClassVar[tuple[str, ...]] = ("pdu",)

    def __init__(self, slave_id: int, pdu: ModbusPdu) -> None:
        """Initialize the Modbus RTU Response Packet."""
        # Set the instance attributes
        self.slave_id = slave_id
        self.pdu = pdu
        self.crc = 0xFFFF

    def __str__(self) -> str:
        """Return a string representation of the Modbus RTU Response Packet."""
        msg = "MODBUS RTU RSP: (Slave ID: {0}, {1}, CRC: {2})"
        return msg.format(self.slave_id, self.pdu, self.crc)

    @classmethod
    def get_parser(cls) -> type[ModbusPduParserAbc]:
        """Get the PDU parser.

        Returns:
            type : The PDU parser
        """
        return cls._pdu_parser

    @classmethod
    def set_parser(cls, parser: type[ModbusPduParserAbc]) -> None:
        """Set the PDU parser.

        Args:
            parser (type) : The PDU parser
        """
        if not issubclass(parser, ModbusPduParserAbc):
            message = "The parser must be a subclass of ModbusPduParserAbc"
            raise ModbusPacketError(message)

        cls._pdu_parser = parser

    def set_crc(self, value: int) -> None:
        """Set the Modbus CRC."""
        self.crc = value

    def calc_crc(self) -> int:
        """Calculate the Modbus CRC over the slave id and the PDU.

        The checksum covers everything ahead of it in the ADU. The result is
        stored on the packet and returned.

        Returns:
            int : The CRC value
        """
        self.crc = calc_crc16(bytearray([self.slave_id]) + self.pdu.serialize())

        return self.crc

    def serialize(self) -> bytes:
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

        except (ModbusPacketError, struct.error) as e:
            message = f"Error serializing the RTU Response PDU: {e}"
            raise ModbusPacketError(message) from e

        # Return the packed bytes
        return slave_id + pdu + crc

    @classmethod
    def deserialize(cls, stream: bytes, verify_crc: bool = True) -> ModbusRtuResponse:
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

        except (ModbusPacketError, struct.error) as e:
            message = f"Error deserializing the RTU Response PDU: {e}"
            raise ModbusPacketError(message) from e

        # Return the packet
        return packet


################################################################################
# MODBUS TCP PACKETS
################################################################################


def validate_mbap_length(header: ModbusHeader, stream: bytes) -> None:
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
            f"MBAP length field declares {header.length} byte(s) after the protocol "
            f"identifier, implying an ADU of {expected} byte(s), but {len(stream)} byte(s) "
            "were received"
        )
        raise ModbusPacketError(message)


class ModbusTcpPacket(ModbusPacketAbc):
    """Generic Modbus TCP Packet.

    This is a generic packet that manages serialization and deserialization. It
    is intented to be used by components that do not differentiate between a
    request and a response, such as sniffers, proxies or gateways. In this
    case the message is just forwarded without any processing.

    Args:
        header (ModbusHeader) : The Modbus TCP Header
        pdu (ModbusPdu)       : The Modbus Request PDU

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

    # The ADU carries a header and a PDU, whose findings travel with its own.
    PARTS: ClassVar[tuple[str, ...]] = ("header", "pdu")

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}

    def __init__(self, header: ModbusHeader, pdu: ModbusPdu) -> None:
        """Initialize the Modbus TCP Packet."""
        # Set the instance attributes
        self.header = header
        self.pdu = pdu

    def __str__(self) -> str:
        """Return a string representation of the Modbus TCP Request Packet."""
        msg = "MODBUS TCP PCKT -> | {0} | {1}"
        return msg.format(self.header, self.pdu)

    def serialize(self) -> bytes:
        """Serialize the generic Modbus TCP Packet to a stream of bytes.

        Returns:
            bytes : The serialized Modbus TCP Packet
        """
        try:
            header_bytes = self.header.serialize()
            pdu_bytes = self.pdu.serialize()

        except (AttributeError, ModbusPacketError) as e:
            message = f"Error serializing the TCP Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return header_bytes + pdu_bytes

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusTcpPacket:
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

        except ModbusPacketError as e:
            message = f"Error deserializing the TCP Request PDU: {e}"
            raise ModbusPacketError(message) from e

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
        header (ModbusHeader) : The Modbus TCP Header
        pdu (ModbusPdu)       : The Modbus Request PDU

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

    _pdu_parser: ClassVar[type[ModbusPduParserAbc]] = ModbusPduParser

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}

    # The ADU carries a header and a PDU, whose findings travel with its own.
    PARTS: ClassVar[tuple[str, ...]] = ("header", "pdu")

    def __init__(self, header: ModbusHeader, pdu: ModbusPdu) -> None:
        """Initialize the Modbus TCP Request Packet."""
        # Set the instance attributes
        self.header = header
        self.pdu = pdu

    def __str__(self) -> str:
        """Return a string representation of the Modbus TCP Request Packet."""
        msg = "MODBUS TCP REQ -> | {0} | {1}"
        return msg.format(self.header, self.pdu)

    @classmethod
    def get_parser(cls) -> type[ModbusPduParserAbc]:
        """Get the PDU parser.

        Returns:
            type : The PDU parser
        """
        return cls._pdu_parser

    @classmethod
    def set_parser(cls, parser: type[ModbusPduParserAbc]) -> None:
        """Set the PDU parser.

        Args:
            parser (type) : The PDU parser
        """
        if not issubclass(parser, ModbusPduParserAbc):
            message = "The parser must be a subclass of ModbusPduParserAbc"
            raise ModbusPacketError(message)

        cls._pdu_parser = parser

    def serialize(self) -> bytes:
        """Serialize the Modbus TCP Packet to a stream of bytes.

        Returns:
            bytes : The serialized Modbus TCP Packet
        """
        try:
            header_bytes = self.header.serialize()
            pdu_bytes = self.pdu.serialize()

        except (AttributeError, ModbusPacketError) as e:
            message = f"Error serializing the TCP Request PDU: {e}"
            raise ModbusPacketError(message) from e

        return header_bytes + pdu_bytes

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusTcpRequest:
        """Deserialize the Modbus TCP Packet.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusTcpRequest() : The Modbus TCP Request Packet
        """
        try:
            # Get the header
            header = ModbusHeader.deserialize(stream[: ModbusHeader.SIZE])

            # A length field that contradicts the ADU puts the frame boundary
            # in doubt, so nothing after the header is usable.
            validate_mbap_length(header, stream)

        except ModbusPacketError as e:
            message = f"Error deserializing the TCP Request header: {e}"
            raise ModbusPacketError(message) from e

        pdu_bytes = stream[ModbusHeader.SIZE :]

        try:
            # Get the concrete request PDU
            pdu = cls._pdu_parser.parse_request(pdu_bytes)

        except ModbusPacketError as e:
            message = f"Error deserializing the TCP Request PDU: {e}"

            # An empty PDU names no function code, so an exception response
            # has nothing to report and the caller can only drop the peer.
            if not pdu_bytes:
                raise ModbusPacketError(message) from e

            raise ModbusPduParseError(message, header=header, fc=pdu_bytes[0]) from e

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
        header (ModbusHeader) : The Modbus TCP Header
        pdu (ModbusPdu)       : The Modbus Response PDU

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

    _pdu_parser: ClassVar[type[ModbusPduParserAbc]] = ModbusPduParser

    # The specification states no bound on this packet's fields.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}

    # The ADU carries a header and a PDU, whose findings travel with its own.
    PARTS: ClassVar[tuple[str, ...]] = ("header", "pdu")

    def __init__(self, header: ModbusHeader, pdu: ModbusPdu) -> None:
        """Initialize the Modbus TCP Response Packet."""
        # Set the instance attributes
        self.header = header
        self.pdu = pdu

    def __str__(self) -> str:
        """Return a string representation of the Modbus TCP Response Packet."""
        msg = "MODBUS TCP RSP -> | {0} | {1}"
        return msg.format(self.header, self.pdu)

    @classmethod
    def get_parser(cls) -> type[ModbusPduParserAbc]:
        """Get the PDU parser.

        Returns:
            type : The PDU parser
        """
        return cls._pdu_parser

    @classmethod
    def set_parser(cls, parser: type[ModbusPduParserAbc]) -> None:
        """Set the PDU parser.

        Args:
            parser (type) : The PDU parser
        """
        if not issubclass(parser, ModbusPduParserAbc):
            message = "The parser must be a subclass of ModbusPduParserAbc"
            raise ModbusPacketError(message)

        cls._pdu_parser = parser

    def serialize(self) -> bytes:
        """Serialize the Modbus TCP Packet to a stream of bytes.

        Returns:
            bytes : The serialized Modbus TCP Packet
        """
        try:
            header_bytes = self.header.serialize()
            pdu_bytes = self.pdu.serialize()

        except (AttributeError, ModbusPacketError) as e:
            message = f"Error serializing the TCP Response PDU: {e}"
            raise ModbusPacketError(message) from e

        return header_bytes + pdu_bytes

    @classmethod
    def deserialize(cls, stream: bytes) -> ModbusTcpResponse:
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

        except ModbusPacketError as e:
            message = f"Error deserializing the TCP Response PDU: {e}"
            raise ModbusPacketError(message) from e

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
