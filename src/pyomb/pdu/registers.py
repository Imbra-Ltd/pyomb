"""Register-access function codes.

Read or write a single holding or input register, or several of them in
one request.
"""

from __future__ import annotations

import struct
from typing import ClassVar

from pyomb.errors import ModbusPacketError
from pyomb.pdu.common import ModbusPdu, ModbusPduParser, ModbusViolation


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
    PDU_COUNT = "byte_count"

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
    PDU_COUNT = "byte_count"

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
    PDU_COUNT = "byte_count"

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
    PDU_COUNT = "write_byte_count"

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
    PDU_COUNT = "byte_count"

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


ModbusPduParser.register(ModbusRequestFC3)
ModbusPduParser.register(ModbusResponseFC3)
ModbusPduParser.register(ModbusRequestFC4)
ModbusPduParser.register(ModbusResponseFC4)
ModbusPduParser.register(ModbusRequestFC6)
ModbusPduParser.register(ModbusResponseFC6)
ModbusPduParser.register(ModbusRequestFC16)
ModbusPduParser.register(ModbusResponseFC16)
ModbusPduParser.register(ModbusRequestFC22)
ModbusPduParser.register(ModbusResponseFC22)
ModbusPduParser.register(ModbusRequestFC23)
ModbusPduParser.register(ModbusResponseFC23)
