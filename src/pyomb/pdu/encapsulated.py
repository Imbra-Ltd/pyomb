"""The encapsulated interface transport: device identification, the specification's MEI type 14."""

from __future__ import annotations

import struct
from typing import ClassVar

from pyomb.errors import ModbusPacketError
from pyomb.pdu.common import ModbusPdu, ModbusPduParser


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


ModbusPduParser.register(ModbusRequestFC43)
ModbusPduParser.register(ModbusResponseFC43)
