"""Modbus RTU over any byte port.

An RTU frame declares no length, so a reader works out where each one ends
from the content: the PDU class the function code names states the size, and
the checksum at that boundary confirms or rejects it. The splitter does that
over bytes pushed in; the stream drives the same sizing from a port the
caller opened, reading only as many bytes as the next verdict needs.

The port is whatever the caller hands over. This module opens none and
imports no serial library; docs/decisions records why.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Protocol

from ..adu import ModbusRtuPacket
from ..adu.rtu import CRC_SIZE
from ..errors import ModbusNetworkError, ModbusPacketError, ModbusTimeoutError
from ..pdu import ModbusError, ModbusPdu, ModbusPduParser
from .stream import ModbusStreamAbc

# A null handler, so importing this module writes nothing: where a host's
# output goes is the host's decision. The stream below takes a logger.
_LOG = logging.getLogger(__name__)
_LOG.addHandler(logging.NullHandler())

# A slave id, a function code and the checksum. Nothing shorter can carry a
# frame, so nothing shorter is worth sizing.
MIN_RTU_FRAME = 1 + 1 + CRC_SIZE

# Modbus Application Protocol V1.1b3, 4.1: a serial-line ADU is at most 256
# bytes, which is what bounds a frame read by silence rather than by content.
MAX_RTU_FRAME = 256


class BytePort(Protocol):
    """What the stream needs from the port a caller opened.

    pyserial's Serial satisfies it unchanged, and so does the file object a
    socket's makefile("rwb", buffering=0) returns. The port's own read timeout
    is the response timeout: read() blocks until size bytes are held or that
    timeout elapses, then returns fewer, possibly none. A port that raises
    TimeoutError instead is treated the same way. Two settings are
    unsupported: no timeout at all blocks forever, and a zero timeout reports
    silence whenever nothing is waiting.
    """

    def read(self, size: int) -> bytes:
        """Return between one and size bytes, or none once the timeout elapses."""
        ...

    def write(self, data: bytes) -> int:
        """Write the bytes and return how many were written."""
        ...


class RtuSide(enum.Enum):
    """Which direction the frames in a stream are travelling.

    A normal response echoes the request's function code, so the byte says
    nothing about direction while the two directions size differently. A
    reader is therefore told which side it decodes rather than inferring it.
    """

    REQUEST = "request"
    RESPONSE = "response"


@dataclass(frozen=True)
class RtuRead:
    """What reading the head of a buffer as one direction produced.

    A packet means a frame was read and length says how long it was. No
    packet means none starts here: incomplete says whether more bytes could
    change that and wanted says how many, and sizable is False where the
    layout states no size at all, so no byte of content ever will.
    """

    packet: ModbusRtuPacket | None
    length: int
    incomplete: bool
    wanted: int
    sizable: bool


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


def read_rtu_frame(stream: bytes, side: RtuSide) -> RtuRead:
    """Read the frame at the head of a buffer as one direction.

    Args:
        stream (bytes) : The bytes held, starting at a candidate frame
        side (RtuSide) : The direction to size the frame as

    Returns:
        RtuRead : The frame where one was read, and why not where none was
    """
    if len(stream) < MIN_RTU_FRAME:
        return RtuRead(packet=None, length=0, incomplete=True, wanted=MIN_RTU_FRAME - len(stream), sizable=True)

    prefix = stream[1:]

    try:
        size = _pdu_class(prefix[0], side).expected_size(prefix)

    except ModbusPacketError:
        # The layout states no size, so no boundary can be computed from this
        # position at all, and no further byte changes that.
        return RtuRead(packet=None, length=0, incomplete=False, wanted=0, sizable=False)

    # The count field has not arrived, so the size is not yet knowable.
    if size is None:
        return RtuRead(packet=None, length=0, incomplete=True, wanted=1, sizable=True)

    end = 1 + size + CRC_SIZE

    if len(stream) < end:
        return RtuRead(packet=None, length=0, incomplete=True, wanted=end - len(stream), sizable=True)

    try:
        packet = ModbusRtuPacket.deserialize(stream[:end])

    except ModbusPacketError:
        # The checksum did not land where the size said it would, so a frame
        # did not start at this byte.
        return RtuRead(packet=None, length=0, incomplete=False, wanted=0, sizable=True)

    return RtuRead(packet=packet, length=end, incomplete=False, wanted=0, sizable=True)


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
        >>> from pyomb.adu import ModbusRtuRequest
        >>> from pyomb.pdu import ModbusRequestFC3
        >>> from pyomb.transport import ModbusRtuSplitter, RtuSide
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
            read = read_rtu_frame(bytes(self._buffer), self.side)

            if read.packet is not None:
                del self._buffer[: read.length]
                return read.packet

            if read.incomplete:
                return None

            self._discard()

        return None


class ModbusRtuStream(ModbusStreamAbc):
    r"""Send and receive RTU frames over a port the caller opened.

    receive() reads only what the next verdict needs, so a short frame on a
    port with a long timeout comes back as soon as it has arrived. Silence
    with nothing held is the peer not answering. Silence with bytes held means
    no more are coming, so what is held is scanned once more and then dropped.
    A layout the registry cannot size is read until the port goes quiet
    instead, bounded at the largest frame the specification allows.

    Args:
        port (BytePort) : An open port; its read timeout is the response timeout
        side (RtuSide)  : The direction of the frames this end reads
        echo (bool)     : Read back and verify each frame written, for an RS-485
                          transceiver that echoes what it sends
        log (Logger)    : Where to report; silent by default

    Example:
        >>> from pyomb.transport import ModbusRtuStream, RtuSide
        >>>
        >>> class Port:
        ...     def __init__(self, inbox):
        ...         self.inbox = bytearray(inbox)
        ...     def read(self, size):
        ...         chunk, self.inbox = bytes(self.inbox[:size]), self.inbox[size:]
        ...         return chunk
        ...     def write(self, data):
        ...         return len(data)
        >>>
        >>> # The published reply to a read of three holding registers.
        >>> reply = b"\x11\x03\x06\xae\x41\x56\x52\x43\x40\x49\xad"
        >>> stream = ModbusRtuStream(port=Port(reply), side=RtuSide.RESPONSE)
        >>> assert stream.receive() == reply
    """

    def __init__(
        self,
        port: BytePort,
        side: RtuSide,
        echo: bool = False,
        log: logging.Logger | None = None,
    ) -> None:
        """Bind the port, the side this end reads, and the echo setting."""
        # Injected so a caller keeps control of where the transport's output
        # goes; the fallback is silent.
        self.log = log or _LOG

        self.port = port
        self.side = side
        self.echo = echo
        self._buffer = bytearray()
        self._resyncs = 0

        # Bytes discarded within this receive. An unsizable head is read by
        # silence only before any discard; after one it is noise, and goes too.
        self._noise = 0

    @property
    def resyncs(self) -> int:
        """Return the count of bytes discarded resynchronising."""
        return self._resyncs

    def _read(self, size: int) -> bytes:
        """Read up to size bytes; empty once the port's timeout elapses.

        Args:
            size (int) : The most bytes to read

        Returns:
            bytes : What arrived, empty on silence

        Raises:
            ModbusNetworkError : If the port itself failed
        """
        try:
            return self.port.read(size)

        # A port that raises on its timeout rather than returning short is
        # reporting the same silence; ordered first because it is an OSError.
        except TimeoutError:
            return b""

        except OSError as e:
            self.log.warning("read failed: %s", e)
            reason = f"Error reading from the port: {e!s}"
            raise ModbusNetworkError(message=reason) from e

    def _read_exactly(self, size: int) -> bytes:
        """Read until size bytes are held or the port goes quiet.

        Args:
            size (int) : The number of bytes to read

        Returns:
            bytes : The bytes read, short only if the port went quiet first
        """
        chunks = []
        pending = size

        while pending > 0:
            chunk = self._read(pending)

            if not chunk:
                break

            chunks.append(chunk)
            pending -= len(chunk)

        return b"".join(chunks)

    def _drain(self) -> None:
        """Read and discard until the port goes quiet, and forget what was held."""
        while self._read(MAX_RTU_FRAME):
            pass

        self._buffer.clear()

    def send(self, message: bytes) -> None:
        """Write one frame, and read it back where the transceiver echoes.

        Args:
            message (bytes) : A serialized RTU frame

        Raises:
            ModbusNetworkError : If the port failed, wrote short, or read back
                                 something other than the frame written
        """
        try:
            written = self.port.write(message)

        except OSError as e:
            self.log.warning("write failed: %s", e)
            reason = f"Error writing to the port: {e!s}"
            raise ModbusNetworkError(message=reason) from e

        if written != len(message):
            reason = f"The port wrote {written} of {len(message)} byte(s)"
            raise ModbusNetworkError(message=reason)

        self.log.debug("sent a frame of %d byte(s)", len(message))

        if not self.echo:
            return

        heard = self._read_exactly(len(message))

        if heard != message:
            # Whatever else is on the line belongs to this failure, not to the
            # next frame, so it goes with it.
            self._drain()
            reason = (
                f"The port read back {heard.hex()} where the frame written was "
                f"{message.hex()}: a bus collision, or a stale reply ahead of the echo"
            )
            raise ModbusNetworkError(message=reason)

    def _discard(self) -> None:
        """Drop the leading byte and count it against the resynchronisations."""
        del self._buffer[:1]
        self._resyncs += 1
        self._noise += 1

    def _take(self, length: int) -> bytes:
        """Return the leading bytes of the buffer and drop them from it."""
        frame = bytes(self._buffer[:length])
        del self._buffer[:length]

        return frame

    def _receive_by_silence(self) -> bytes:
        """Read until the port goes quiet, then let the checksum adjudicate.

        Returns:
            bytes : The frame, where a checksum accepts what arrived

        Raises:
            ModbusPacketError : If what arrived before the silence is no frame
        """
        while len(self._buffer) < MAX_RTU_FRAME:
            chunk = self._read(MAX_RTU_FRAME - len(self._buffer))

            if not chunk:
                break

            self._buffer.extend(chunk)

        # The whole buffer is the one candidate first: an unsizable frame that
        # arrived alone is accepted or rejected on one checksum, not on many.
        try:
            ModbusRtuPacket.deserialize(bytes(self._buffer))

        except ModbusPacketError:
            return self._receive_after_silence()

        return self._take(len(self._buffer))

    def _receive_after_silence(self) -> bytes:
        """Scan what was held once more, now that no more bytes are coming.

        Returns:
            bytes : A frame, where one was hiding behind a stray byte

        Raises:
            ModbusTimeoutError : If nothing at all arrived
            ModbusPacketError  : If bytes arrived and none of them framed
        """
        if not self._buffer:
            raise ModbusTimeoutError(message="Nothing arrived before the port's timeout elapsed")

        arrived = len(self._buffer)

        # Silence is a frame boundary, so an incomplete verdict is now a
        # rejection: the count field it waited for is never coming.
        while len(self._buffer) >= MIN_RTU_FRAME:
            read = read_rtu_frame(bytes(self._buffer), self.side)

            if read.packet is not None:
                return self._take(read.length)

            self._discard()

        discarded = arrived - len(self._buffer)
        self._buffer.clear()
        reason = f"The line went quiet with {arrived} byte(s) that framed to nothing, {discarded} discarded"
        raise ModbusPacketError(reason)

    def receive(self) -> bytes:
        """Receive one complete RTU frame from the port.

        Returns:
            bytes : One frame, checksum verified

        Raises:
            ModbusTimeoutError : If nothing arrived before the port's timeout
            ModbusPacketError  : If what arrived framed to nothing
            ModbusNetworkError : If the port itself failed
        """
        self._noise = 0

        while True:
            read = read_rtu_frame(bytes(self._buffer), self.side)

            if read.packet is not None:
                return self._take(read.length)

            if not read.sizable and self._noise == 0:
                return self._receive_by_silence()

            if not read.incomplete:
                self._discard()
                continue

            chunk = self._read(read.wanted)

            if not chunk:
                return self._receive_after_silence()

            self._buffer.extend(chunk)
