"""The RTU ADU: the CRC-16 checksum and the three RTU frame classes."""

from __future__ import annotations

import struct
from typing import ClassVar

from pyomb.errors import ModbusPacketError
from pyomb.pdu import ModbusPacketAbc, ModbusPdu, ModbusPduParser, ModbusPduParserAbc

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
        >>> from pyomb.pdu import ModbusRequestFC1
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
        >>> from pyomb.pdu import ModbusResponseFC1
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


class ModbusRtuPacket(ModbusPacketAbc):
    """Generic Modbus RTU Packet.

    This is a generic packet that manages serialization and deserialization. It
    is intended to be used by components that do not differentiate between a
    request and a response, such as sniffers, proxies or gateways. In this case
    the message is just forwarded without any processing.

    The function code cannot supply the direction. A server echoes the
    request's function code in a normal response, so the byte is the same in
    both directions, and only an exception response differs by carrying the
    most significant bit set.

    Args:
        slave_id (int)  : The slave id
        pdu (ModbusPdu) : The Modbus PDU, in either direction

    Example:
        >>> # Create the required PDU
        >>> from pyomb.pdu import ModbusRequestFC1
        >>> pdu = ModbusRequestFC1(start_addr=1, quantity=2)
        >>>
        >>> # Create the Modbus RTU Packet
        >>> packet1 = ModbusRtuPacket(slave_id=1, pdu=pdu)
        >>>
        >>> # Serialize the packet
        >>> stream = packet1.serialize()
        >>>
        >>> # Deserialize the packet
        >>> packet2 = ModbusRtuPacket.deserialize(stream)
        >>>
        >>> # Check the frame survives the round trip. Deserializing yields a
        >>> # generic ModbusPdu rather than the ModbusRequestFC1 that went in,
        >>> # which is what this class is for, so compare the bytes and not the
        >>> # objects -- the two hold the same frame in different shapes.
        >>> assert packet2.serialize() == stream
    """

    # The ADU carries a PDU, whose findings travel with its own.
    PARTS: ClassVar[tuple[str, ...]] = ("pdu",)

    # Modicon Modbus Protocol Reference Guide PI-MBUS-300: 0 is the broadcast
    # every device recognises, 1 to 247 address one, and 248 to 255 are invalid.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"slave_id": (0x00, 0xF7)}

    def __init__(self, slave_id: int, pdu: ModbusPdu) -> None:
        """Initialize the Modbus RTU Packet."""
        # Set the instance attributes
        self.slave_id = slave_id
        self.pdu = pdu
        self.crc = 0xFFFF

    def __str__(self) -> str:
        """Return a string representation of the Modbus RTU Packet."""
        msg = "MODBUS RTU PCKT: (Slave ID: {0}, {1}, CRC: {2})"
        return msg.format(self.slave_id, self.pdu, self.crc)

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
        """Serialize the generic Modbus RTU ADU to a stream of bytes.

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
            message = f"Error serializing the RTU Packet: {e}"
            raise ModbusPacketError(message) from e

        # Return the packed bytes
        return slave_id + pdu + crc

    @classmethod
    def deserialize(cls, stream: bytes, verify_crc: bool = True) -> ModbusRtuPacket:
        """Deserialize the generic Modbus RTU Packet from a stream of bytes.

        The PDU is read generically rather than as a request or a response, so
        the caller does not have to know which direction the frame travelled.

        Args:
            stream (bytes)      : The stream of bytes to deserialize
            verify_crc (bool)   : Check the frame against its own checksum.
                                  Pass False to accept a corrupt frame, which
                                  tests constructing one need.

        Returns:
            ModbusRtuPacket() : The Modbus RTU Packet

        Raises:
            ModbusPacketError : If the frame contradicts its own checksum
        """
        # Checked before parsing: a corrupt frame is worth rejecting on the
        # checksum rather than on whatever the damaged bytes decode to.
        if verify_crc:
            validate_crc(stream, "RTU Packet")

        try:
            # The slave id is the first byte
            (slave_id,) = struct.unpack(">B", stream[:1])

            # The crc is the last two bytes, low byte first
            (crc,) = struct.unpack(CRC_FMT, stream[-CRC_SIZE:])

            # Read the PDU without interpreting it, which is what keeps this
            # class direction-free
            pdu = ModbusPdu.deserialize(stream[1:-CRC_SIZE])

            # Create a new instance of the class
            packet = cls(slave_id=slave_id, pdu=pdu)
            packet.set_crc(crc)

        except (ModbusPacketError, struct.error) as e:
            message = f"Error deserializing the RTU Packet: {e}"
            raise ModbusPacketError(message) from e

        # Return the packet
        return packet
