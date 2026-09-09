"""The TCP ADU: the MBAP header and the three TCP frame classes."""

from __future__ import annotations

import struct
from typing import ClassVar

from pyomb.errors import ModbusPacketError, ModbusPduParseError
from pyomb.pdu import ModbusPacketAbc, ModbusPdu, ModbusPduParser, ModbusPduParserAbc


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
        >>> from pyomb.pdu import ModbusRequestFC1
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
        >>> from pyomb.pdu import ModbusRequestFC1
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
        >>> from pyomb.pdu import ModbusResponseFC1
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
