"""Bit-access function codes.

Read or write a single coil or discrete input, or write several of them
in one request.
"""

from __future__ import annotations

import struct
from typing import ClassVar

from pyomb.errors import ModbusPacketError
from pyomb.pdu.common import ModbusPdu, ModbusPduParser, ModbusViolation


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
    PDU_COUNT = "byte_count"

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
    PDU_COUNT = "byte_count"

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
    PDU_COUNT = "byte_count"

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


ModbusPduParser.register(ModbusRequestFC1)
ModbusPduParser.register(ModbusResponseFC1)
ModbusPduParser.register(ModbusRequestFC2)
ModbusPduParser.register(ModbusResponseFC2)
ModbusPduParser.register(ModbusRequestFC5)
ModbusPduParser.register(ModbusResponseFC5)
ModbusPduParser.register(ModbusRequestFC15)
ModbusPduParser.register(ModbusResponseFC15)
