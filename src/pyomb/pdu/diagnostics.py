"""Diagnostics function codes.

The exception status poll and the sub-function-driven diagnostic loopback.
"""

from __future__ import annotations

import struct
from typing import ClassVar

from pyomb.errors import ModbusPacketError
from pyomb.pdu.common import ModbusPdu, ModbusPduParser, ModbusViolation


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


# Modbus Application Protocol v1.1b3 section 6.8.1 enumerates the Diagnostics
# sub-function codes. Every value the table does not list is reserved.
_DIAGNOSTIC_SUB_FUNCTIONS = frozenset(
    {0x00, 0x01, 0x02, 0x03, 0x04, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x14}
)

# The set as the table renders it, so a finding reads back against the
# document rather than against a list of fifteen numbers.
_DIAGNOSTIC_SUB_FUNCTION_RULE = "0x0000 to 0x0004, 0x000A to 0x0012, or 0x0014"

# Return Query Data echoes whatever the client sent, so its data field has no
# stated width. Every other listed sub-function carries one 16-bit word.
_DIAGNOSTIC_ECHO_SUB_FUNCTION = 0x0000

# The function code, the sub-function, and that single data word.
_DIAGNOSTIC_SIZE = struct.calcsize(">BHH")


def _diagnostic_size_from_prefix(name: str, prefix: bytes) -> int | None:
    """Size a Diagnostics PDU from the sub-function ahead of its data.

    Args:
        name (str)     : The class being sized, named in a refusal
        prefix (bytes) : The frame from the function code onwards

    Returns:
        int  : The size of the PDU in bytes
        None : If the prefix stops before the sub-function

    Raises:
        ModbusPacketError : If the sub-function states no width, so no byte
            of the prefix says where the frame ends
    """
    head = struct.calcsize(">BH")

    if len(prefix) < head:
        return None

    sub_func = struct.unpack(">H", prefix[1:head])[0]

    # A reserved sub-function is sized by nothing: the table is the only
    # statement of what the data field holds.
    if sub_func == _DIAGNOSTIC_ECHO_SUB_FUNCTION:
        reason = "echoes the query data back"

    elif sub_func not in _DIAGNOSTIC_SUB_FUNCTIONS:
        reason = f"carries sub-function 0x{sub_func:04X}, which is reserved"

    else:
        return _DIAGNOSTIC_SIZE

    message = f"{name} {reason}, so its size cannot be read from a prefix"
    raise ModbusPacketError(message)


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

    # The specification's rule here names a value set, so it lives in
    # violations() below rather than in a range.
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

    @classmethod
    def expected_size(cls, prefix: bytes) -> int | None:
        """Report how many bytes this PDU occupies, read from a frame's start.

        Modbus Application Protocol v1.1b3 section 6.8: the sub-function
        discriminates rather than counts, so the base class refuses. The table
        it is checked against states a width for all but one of them.

        Args:
            prefix (bytes) : The frame from the function code onwards

        Returns:
            int  : The size of the PDU in bytes
            None : If the prefix stops before the sub-function

        Raises:
            ModbusPacketError : If the sub-function states no width
        """
        return _diagnostic_size_from_prefix(cls.__name__, prefix)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the sub-function set the specification enumerates.

        Modbus Application Protocol v1.1b3 section 6.8.1: the table lists the
        sub-function codes; every other value in the field is reserved.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        found = list(super().violations())

        if self.sub_func not in _DIAGNOSTIC_SUB_FUNCTIONS:
            found.append(self._finding("sub_func", _DIAGNOSTIC_SUB_FUNCTION_RULE))

        return tuple(found)

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

    # The specification's rule here names a value set, so it lives in
    # violations() below rather than in a range.
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

    @classmethod
    def expected_size(cls, prefix: bytes) -> int | None:
        """Report how many bytes this PDU occupies, read from a frame's start.

        Modbus Application Protocol v1.1b3 section 6.8: the sub-function
        discriminates rather than counts, so the base class refuses. The table
        it is checked against states a width for all but one of them.

        Args:
            prefix (bytes) : The frame from the function code onwards

        Returns:
            int  : The size of the PDU in bytes
            None : If the prefix stops before the sub-function

        Raises:
            ModbusPacketError : If the sub-function states no width
        """
        return _diagnostic_size_from_prefix(cls.__name__, prefix)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report the bounds, and the sub-function set the specification enumerates.

        Modbus Application Protocol v1.1b3 section 6.8.1: the table lists the
        sub-function codes; every other value in the field is reserved.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        found = list(super().violations())

        if self.sub_func not in _DIAGNOSTIC_SUB_FUNCTIONS:
            found.append(self._finding("sub_func", _DIAGNOSTIC_SUB_FUNCTION_RULE))

        return tuple(found)

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


ModbusPduParser.register(ModbusRequestFC7)
ModbusPduParser.register(ModbusResponseFC7)
ModbusPduParser.register(ModbusRequestFC8)
ModbusPduParser.register(ModbusResponseFC8)
