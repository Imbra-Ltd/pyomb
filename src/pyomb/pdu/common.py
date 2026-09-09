"""Constraints, the abstract packet bases, and the shared PDU classes.

A finding, the base every packet component descends from, the parser
interface, and the base every function-code class descends from. Nothing
here knows a function code or a transport.
"""

from __future__ import annotations

import struct
import warnings
from abc import ABCMeta, abstractmethod
from typing import ClassVar

from pyomb.errors import ModbusPacketError

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
        >>> from pyomb.pdu import ModbusRequestFC3
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

    # The field counting the payload bytes that follow it, always the last of
    # PDU_FIELDS. None where the layout carries no such count.
    PDU_COUNT: ClassVar[str | None] = None

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

    @classmethod
    def expected_size(cls, prefix: bytes) -> int | None:
        """Report how many bytes this PDU occupies, read from a frame's start.

        An RTU frame declares no length, so a reader splitting a stream works
        the boundary out from the content instead. This answers from the
        declared layout, where __len__ answers from a parsed instance -- which
        is the thing a reader is still trying to establish it can do.

        Args:
            prefix (bytes) : The frame from the function code onwards, whether
                             or not it is complete

        Returns:
            int  : The size of the PDU in bytes
            None : If the prefix stops before the count field, so the caller
                   has to read more bytes and ask again

        Raises:
            ModbusPacketError : If the layout states no size. The Diagnostics
                and Encapsulated Interface PDUs lead with a sub-function and
                an MEI type, which discriminate rather than count, so no byte
                of the prefix says where the frame ends
        """
        if "{0}" not in cls.PDU_FORMAT:
            return struct.calcsize(cls.PDU_FORMAT)

        if cls.PDU_COUNT is None:
            message = f"{cls.__name__} carries no count field, so its size cannot be read from a prefix"
            raise ModbusPacketError(message)

        head = struct.calcsize(cls.PDU_FORMAT.split("{0}")[0])

        if len(prefix) < head:
            return None

        # The count sits immediately ahead of the payload, so it is the last
        # byte of the head, and it counts bytes rather than items.
        return head + prefix[head - 1]

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
        >>> from pyomb.pdu import ModbusRequestFC1
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
