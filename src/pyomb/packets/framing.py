"""Framing: how a PDU is represented on a transport.

The MBAP header and the TCP ADU classes, the RTU ADU classes and the
checksum they carry. Each class reads and writes exactly one complete frame,
and the RTU splitter finds those frames in a stream arriving in pieces.
"""

from __future__ import annotations

import enum
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from pyomb.errors import ModbusPacketError, ModbusPduParseError
from pyomb.packets.base import ModbusPacketAbc, ModbusPduParserAbc
from pyomb.packets.pdu import ModbusError, ModbusPdu, ModbusPduParser


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
        >>> from pyomb.packets import ModbusRequestFC1
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
        >>> from pyomb.packets import ModbusResponseFC1
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
        >>> from pyomb.packets import ModbusRequestFC1
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


################################################################################
# MODBUS TCP PACKETS
################################################################################


class RtuSide(enum.Enum):
    """Which direction the frames in a stream are travelling.

    A normal response echoes the request's function code, so the byte says
    nothing about direction while the two directions size differently. A
    reader is therefore told which side it decodes rather than inferring it.
    """

    REQUEST = "request"
    RESPONSE = "response"


# A slave id, a function code and the checksum. Nothing shorter can carry a
# frame, so nothing shorter is worth sizing.
MIN_RTU_FRAME = 1 + 1 + CRC_SIZE


@dataclass(frozen=True)
class _RtuRead:
    """What reading the head of a buffer as one direction produced.

    A packet means a frame was read and length says how long it was. No
    packet means none starts here, and incomplete says whether more bytes
    could change that.
    """

    packet: ModbusRtuPacket | None
    length: int
    incomplete: bool


def _pdu_class(func_code: int, side: RtuSide) -> type[ModbusPdu]:
    """Return the PDU class a side reads a function code as."""
    registry = ModbusPduParser.get_registry()

    if side is RtuSide.REQUEST:
        return registry.get(func_code, ModbusPdu)

    # An exception is the one function code that states its own direction,
    # and the error PDU is what 0x8000 answers for.
    if func_code >= 0x80:
        return ModbusError

    return registry.get(func_code + 0x8000, ModbusPdu)


def _read_rtu_frame(stream: bytes, side: RtuSide) -> _RtuRead:
    """Read the frame at the head of a buffer as one direction.

    Args:
        stream (bytes) : The bytes held, starting at a candidate frame
        side (RtuSide) : The direction to size the frame as

    Returns:
        _RtuRead : The frame where one was read, and why not where none was
    """
    if len(stream) < MIN_RTU_FRAME:
        return _RtuRead(packet=None, length=0, incomplete=True)

    prefix = stream[1:]

    try:
        size = _pdu_class(prefix[0], side).expected_size(prefix)

    except ModbusPacketError:
        # The layout states no size, so no boundary can be computed from this
        # position at all, and no further byte changes that.
        return _RtuRead(packet=None, length=0, incomplete=False)

    # The count field has not arrived, so the size is not yet knowable.
    if size is None:
        return _RtuRead(packet=None, length=0, incomplete=True)

    end = 1 + size + CRC_SIZE

    if len(stream) < end:
        return _RtuRead(packet=None, length=0, incomplete=True)

    try:
        packet = ModbusRtuPacket.deserialize(stream[:end])

    except ModbusPacketError:
        # The checksum did not land where the size said it would, so a frame
        # did not start at this byte.
        return _RtuRead(packet=None, length=0, incomplete=False)

    return _RtuRead(packet=packet, length=end, incomplete=False)


class ModbusRtuSplitter:
    """Cut whole RTU frames out of a stream of bytes.

    Bytes are pushed in as they arrive and whole frames come back. An RTU frame
    declares no length, so the boundary is computed from the content: the PDU
    class states how long its frame is, and the checksum at that boundary either
    confirms the answer or rejects it. A rejected frame costs one byte, which is
    discarded before the search resumes.

    Args:
        side (RtuSide) : Which direction the frames travel

    Example:
        >>> from pyomb.packets import ModbusRequestFC3, ModbusRtuRequest
        >>>
        >>> pdu = ModbusRequestFC3(start_addr=0x006B, quantity=3)
        >>> frame = ModbusRtuRequest(slave_id=0x11, pdu=pdu).serialize()
        >>>
        >>> splitter = ModbusRtuSplitter(side=RtuSide.REQUEST)
        >>>
        >>> # Half a frame yields nothing; the rest of it yields the frame.
        >>> assert splitter.push(frame[:4]) == []
        >>> found = splitter.push(frame[4:])
        >>> assert len(found) == 1
        >>> assert found[0].serialize() == frame
    """

    # Kept as the name the class documented; the value has one definition.
    MIN_FRAME = MIN_RTU_FRAME

    def __init__(self, side: RtuSide) -> None:
        """Initialize the Modbus RTU Splitter.

        Args:
            side (RtuSide) : Which direction the frames travel
        """
        self.side = side
        self._buffer = bytearray()
        self._resyncs = 0

    def __str__(self) -> str:
        """Return a string representation of the Modbus RTU Splitter."""
        msg = "MODBUS RTU SPLITTER: (Side: {0}, Pending: {1}, Resyncs: {2})"
        return msg.format(self.side.value, self.pending, self.resyncs)

    @property
    def pending(self) -> int:
        """Return the count of held bytes that are not yet a whole frame."""
        return len(self._buffer)

    @property
    def resyncs(self) -> int:
        """Return the count of bytes discarded resynchronising."""
        return self._resyncs

    def reset(self) -> None:
        """Drop every held byte and zero the resynchronisation count."""
        self._buffer.clear()
        self._resyncs = 0

    def push(self, data: bytes) -> list[ModbusRtuPacket]:
        """Add received bytes and return the whole frames they complete.

        Args:
            data (bytes) : The bytes received since the last call

        Returns:
            list : The frames these bytes completed, in arrival order
        """
        self._buffer.extend(data)
        found: list[ModbusRtuPacket] = []

        while True:
            packet = self._take()

            if packet is None:
                break

            found.append(packet)

        return found

    def _discard(self) -> None:
        """Drop the leading byte and count it against the resynchronisations."""
        del self._buffer[:1]
        self._resyncs += 1

    def _take(self) -> ModbusRtuPacket | None:
        """Return the next whole frame, or None while more bytes are needed."""
        while len(self._buffer) >= MIN_RTU_FRAME:
            read = _read_rtu_frame(bytes(self._buffer), self.side)

            if read.packet is not None:
                del self._buffer[: read.length]
                return read.packet

            if read.incomplete:
                return None

            self._discard()

        return None


class RtuSyncState(enum.Enum):
    """What a sniffer expects the next frame on the bus to be."""

    SYNCING = "syncing"
    EXPECT_REQUEST = "expect_request"
    EXPECT_RESPONSE = "expect_response"


@dataclass(frozen=True)
class RtuSniffedFrame:
    """A frame read off a bus, with the direction it was read as."""

    side: RtuSide
    packet: ModbusRtuPacket


class ModbusRtuSniffer:
    r"""Read frames off a bus nobody told the reader about.

    A splitter is told which direction it decodes. A sniffer watching two
    devices talk is told nothing, so it reads each frame both ways and keeps
    whichever the checksum accepts. Where both are accepted the frame is
    genuinely ambiguous, and the bus takes turns, so the expected direction
    decides.

    Args:
        timeout (float)  : Seconds to wait for an answer before expecting a
                           fresh request. Well above driver buffering, which
                           is why this measurement is usable where an
                           inter-frame gap is not
        clock (callable) : The time source, for a suite that does not sleep

    Example:
        >>> sniffer = ModbusRtuSniffer()
        >>>
        >>> # A read of three holding registers, and the answer to it.
        >>> found = sniffer.push(
        ...     b"\x11\x03\x00\x6b\x00\x03\x76\x87"
        ...     b"\x11\x03\x06\xae\x41\x56\x52\x43\x40\x49\xad"
        ... )
        >>>
        >>> assert [frame.side for frame in found] == [
        ...     RtuSide.REQUEST,
        ...     RtuSide.RESPONSE,
        ... ]
    """

    def __init__(self, timeout: float = 1.0, clock: Callable[[], float] | None = None) -> None:
        """Initialize the Modbus RTU Sniffer.

        Args:
            timeout (float)  : Seconds to wait for an answer
            clock (callable) : The time source; the monotonic clock by default
        """
        self.timeout = timeout
        self._clock = clock if clock is not None else time.monotonic
        self._buffer = bytearray()
        self._resyncs = 0
        self._state = RtuSyncState.SYNCING
        self._last_seen = self._clock()

    def __str__(self) -> str:
        """Return a string representation of the Modbus RTU Sniffer."""
        msg = "MODBUS RTU SNIFFER: (State: {0}, Pending: {1}, Resyncs: {2})"
        return msg.format(self._state.value, self.pending, self.resyncs)

    @property
    def state(self) -> RtuSyncState:
        """Return what the next frame is expected to be."""
        return self._state

    @property
    def pending(self) -> int:
        """Return the count of held bytes that are not yet a whole frame."""
        return len(self._buffer)

    @property
    def resyncs(self) -> int:
        """Return the count of bytes discarded resynchronising."""
        return self._resyncs

    def reset(self) -> None:
        """Drop every held byte, the count, and what was expected next."""
        self._buffer.clear()
        self._resyncs = 0
        self._state = RtuSyncState.SYNCING
        self._last_seen = self._clock()

    def push(self, data: bytes) -> list[RtuSniffedFrame]:
        """Add received bytes and return the whole frames they complete.

        Args:
            data (bytes) : The bytes received since the last call

        Returns:
            list : The frames these bytes completed, in arrival order
        """
        self._buffer.extend(data)
        self._expire()
        found: list[RtuSniffedFrame] = []

        while True:
            frame = self._take()

            if frame is None:
                break

            found.append(frame)

        return found

    def _expire(self) -> None:
        """Expect a fresh request where no answer arrived in time."""
        if self._state is not RtuSyncState.EXPECT_RESPONSE:
            return

        if self._clock() - self._last_seen > self.timeout:
            self._state = RtuSyncState.EXPECT_REQUEST

    def _discard(self) -> None:
        """Drop the leading byte and count it against the resynchronisations."""
        del self._buffer[:1]
        self._resyncs += 1

    def _choose(self, landed: list[RtuSide], slave_id: int) -> RtuSide:
        """Pick the direction where more than one read was accepted."""
        if len(landed) == 1:
            return landed[0]

        # Modicon Modbus Protocol Reference Guide PI-MBUS-300: address 0 is the
        # broadcast every device recognises, and no server answers one.
        if slave_id == 0x00:
            return RtuSide.REQUEST

        if self._state is RtuSyncState.EXPECT_RESPONSE:
            return RtuSide.RESPONSE

        return RtuSide.REQUEST

    def _advance(self, side: RtuSide, slave_id: int) -> None:
        """Move to whichever direction the bus should carry next."""
        self._last_seen = self._clock()

        # A broadcast is answered by nobody, so a request follows it.
        if side is RtuSide.RESPONSE or slave_id == 0x00:
            self._state = RtuSyncState.EXPECT_REQUEST
            return

        self._state = RtuSyncState.EXPECT_RESPONSE

    def _take(self) -> RtuSniffedFrame | None:
        """Return the next whole frame, or None while more bytes are needed."""
        while len(self._buffer) >= MIN_RTU_FRAME:
            held = bytes(self._buffer)
            reads = {side: _read_rtu_frame(held, side) for side in RtuSide}
            landed = [side for side, read in reads.items() if read.packet is not None]

            if landed:
                side = self._choose(landed, held[0])
                read = reads[side]

                if read.packet is not None:
                    del self._buffer[: read.length]
                    self._advance(side, held[0])

                    return RtuSniffedFrame(side=side, packet=read.packet)

            if any(read.incomplete for read in reads.values()):
                return None

            self._discard()

        return None


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
        >>> from pyomb.packets import ModbusRequestFC1
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
        >>> from pyomb.packets import ModbusRequestFC1
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
        >>> from pyomb.packets import ModbusResponseFC1
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
