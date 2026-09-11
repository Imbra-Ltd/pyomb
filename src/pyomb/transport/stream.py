"""Modbus TCP streaming services.

Sending, receiving, fragmenting and reassembling Modbus messages over a TCP
socket. The banners below divide the module into the abstract contracts, the
fragmenter, and the three streaming classes a caller uses.

A frame does not arrive one per recv(). The only thing saying where one ends
is the length field in its own header, which is what the fragmenter reads.
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from abc import ABCMeta, abstractmethod
from collections.abc import Iterable

from ..adu import ModbusHeader, ModbusTcpPacket
from ..errors import ModbusBaseError, ModbusNetworkError, ModbusPacketError

# Modbus MBAP header size
HEADER_SIZE = ModbusHeader.SIZE

# A null handler, so importing this module writes nothing: where a host's
# output goes is the host's decision. Each class below takes a logger.
_LOG = logging.getLogger(__name__)
_LOG.addHandler(logging.NullHandler())


################################################################################
# ABSTRACT BASE CLASSES
################################################################################


class ModbusSenderAbc(metaclass=ABCMeta):
    """Abstract base class for sending Modbus messages."""

    # Burst is a property of the sender rather than of one run: it sets
    # TCP_NODELAY on the socket the sender owns, so it is not a parameter here.
    @abstractmethod
    def run_once(self) -> None:
        """Sends the Modbus messages."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stops sending messages."""
        raise NotImplementedError


class ModbusReceiverAbc(metaclass=ABCMeta):
    """Abstract base class for receiving Modbus messages."""

    @abstractmethod
    def run_once(self) -> list[ModbusTcpPacket]:
        """Starts receiving Modbus messages."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stops receiving messages."""
        raise NotImplementedError


class ModbusFragmenterAbc(metaclass=ABCMeta):
    """Abstract base class for fragmenting/reassembling Modbus messages."""

    @abstractmethod
    def fragment(self, message: bytes, frag_size: int = 7) -> list[bytes]:
        """Fragments a Modbus message into smaller pieces."""
        raise NotImplementedError

    @abstractmethod
    def assemble(self, fragments: Iterable[bytes]) -> bytes:
        """Assembles fragmented Modbus messages into a complete message."""
        raise NotImplementedError


class ModbusStreamAbc(metaclass=ABCMeta):
    """Abstract base class for sending and receiving Modbus messages."""

    # Named for what every caller passes -- the serialized bytes, not the
    # packet they came from. A supertype's keyword binds every subtype.
    @abstractmethod
    def send(self, message: bytes) -> None:
        """Sends a serialized packet."""
        raise NotImplementedError

    @abstractmethod
    def receive(self) -> bytes:
        """Receives a serialized packet."""
        raise NotImplementedError


################################################################################
# FRAGMENTATION AND REASSEMBLY
################################################################################


class ModbusFragmenter(ModbusFragmenterAbc):
    """A class for Modbus message fragmentation and reassembly.

     - Fragment 0: MBAP Header
     - Fragment 1: PDU (m Bytes)
     - Fragment 2: PDU (m Bytes)
     - Fragment 3: PDU (m Bytes)
     - ...
     - Fragment n: PDU (m Bytes)

    Example:
        >>> from pyomb.adu import ModbusHeader, ModbusTcpRequest
        >>> from pyomb.pdu import ModbusRequestFC1
        >>> from pyomb.transport import ModbusFragmenter
        >>>
        >>> # Create a Modbus PDU
        >>> pdu = ModbusRequestFC1(start_addr=0, quantity=1)
        >>>
        >>> # Create the Modbus header and set the length (Unit-ID + PDU)
        >>> header = ModbusHeader(length=len(pdu)+1)
        >>>
        >>> # Create the Modbus ADU
        >>> adu = ModbusTcpRequest(header=header, pdu=pdu)
        >>>
        >>> # Serialize the packet
        >>> message1 = adu.serialize()
        >>>
        >>> # Create the Modbus fragmenter
        >>> fragmenter = ModbusFragmenter()
        >>>
        >>> # Fragment the message
        >>> fragments = fragmenter.fragment(message1, frag_size=7)
        >>>
        >>> # Assemble the fragments
        >>> message2 = fragmenter.assemble(fragments)
        >>>
        >>> # Check if the messages are equal
        >>> assert message1 == message2
    """

    @staticmethod
    def get_message_length(message: bytes) -> int:
        """Gets the length of a Modbus message from the MBAP header.

        Args:
           message (bytes): A Modbus message.
        """
        # Deserialize the header
        header = ModbusHeader.deserialize(message[:HEADER_SIZE])

        # The length field counts the unit identifier, which HEADER_SIZE
        # already covers, so it contributes length - 1 bytes beyond the header.
        packet_len = HEADER_SIZE + header.length - 1

        return packet_len

    @staticmethod
    def fragment(message: bytes, frag_size: int = 7) -> list[bytes]:
        """Fragments a Modbus message into smaller pieces.

        If the fragment size is 0, the message is not fragmented. If the
        fragment size is greater than the message length, the message is
        fragmented into two pieces: the MBAP header and the PDU.

        Args:
            message (bytes): A Modbus message.
            frag_size (int): The size of the fragments.
        """
        # Check if the fragment size is valid
        if frag_size < 0:
            reason = "The allowed fragment size is greater or equal to 0."
            raise ModbusPacketError(reason)

        # Disable fragmentation if the fragment size is 0
        elif frag_size == 0:
            return [message]

        # Fragment the message into smaller pieces
        try:
            # The first fragment is the MBAP header
            header = message[:HEADER_SIZE]

            # The remaining fragments are the PDU
            pdu = message[HEADER_SIZE:]

            # Add the header to the fragments list
            fragments = [header]

            # Fragment the PDU into smaller pieces
            while pdu:
                fragments.append(pdu[:frag_size])
                pdu = pdu[frag_size:]

        except TypeError as e:
            reason = f"Error fragmenting the Modbus packet: {e!s}"
            raise ModbusPacketError(reason) from e

        else:
            # Return the fragments
            return fragments

    @staticmethod
    def assemble(fragments: Iterable[bytes]) -> bytes:
        """Assembles message fragments into a complete message.

        Arguments:
            fragments (iterable): A list of message fragments.

        Returns:
            bytes: A complete Modbus message.
        """
        return b"".join(fragments)


################################################################################
# STREAMING SERVICES
################################################################################


class ModbusTcpStream(ModbusStreamAbc):
    """A class for sending and receiving Modbus messages over TCP.

    This class is used to send and receive Modbus messages over TCP. The
    class provides methods for sending and receiving Modbus messages in
    a fragmented manner. The fragmentation size and delay can be set by
    the user.

    The class can be used to send and receive Modbus messages in burst
    mode. In burst mode, the TCP_NODELAY option is set to True, which
    disables the Nagle's algorithm. This mode is useful for sending
    multiple Modbus messages in a short period of time.

    Args:
        sock (socket.socket)                : A TCP socket.
        fragmenter (ModbusFragmenterAbc)    : A Modbus fragmenter
        frag_delay (numeric)                : A delay between fragments
        frag_size (int)                     : The size of the fragments
        burst (bool)                        : Burst mode.

    Usage:
        This class needs a connected socket, so the demonstration lives in
        `examples/fragmented_send.py` rather than here. It starts this
        project's own server simulator on a port the operating system picks,
        sends a request in 8-byte pieces, and reassembles the reply by the
        length its header declares. CI runs it on every pull request.
    """

    def __init__(
        self,
        sock: socket.socket | None,
        fragmenter: ModbusFragmenterAbc | None = None,
        frag_delay: float = 0,
        frag_size: int = 0,
        burst: bool = False,
        log: logging.Logger | None = None,
    ) -> None:
        """Bind the socket and the fragmentation settings this stream sends under."""
        # Injected so a caller keeps control of where the transport's output
        # goes; the fallback is silent.
        self.log = log or _LOG

        # If no TCP socket is provided, create a new one
        self.sock = sock or socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Constructed here rather than in the signature, where one instance
        # would be built at import time and shared by every caller.
        self.fragmenter = ModbusFragmenter() if fragmenter is None else fragmenter

        # Set the fragmentation delay in seconds
        self.frag_delay = frag_delay

        # Set the fragmentation size in bytes
        self.frag_size = frag_size

        # Set the burst mode (send TCP packet without delay)
        self.burst = burst

    def send(self, message: bytes) -> None:
        """Sends a Modbus message to the connected socket.

        Args:
            message (bytes): A Modbus message.
        """
        try:
            # Set the burst mode if requested, no matter of the packets
            if self.burst:
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)

            # Makes the fragmentation if necessary
            fragments = self.fragmenter.fragment(message=message, frag_size=self.frag_size)

            # Iterate through the fragments and sends them one by one
            for fragment in fragments:
                self.sock.send(fragment)
                self.log.debug("sent a fragment of %d byte(s)", len(fragment))
                time.sleep(self.frag_delay)

        # Raised by the fragmenter and already carrying the reason; wrapping
        # it again would bury a framing fault inside a transport error.
        except ModbusBaseError:
            raise

        except OSError as e:
            self.log.warning("send failed: %s", e)
            reason = f"Error sending Modbus message: {e!s}"
            raise ModbusNetworkError(message=reason) from e

    def _recv_exactly(self, count: int) -> bytes:
        """Reads a fixed number of bytes from the socket.

        A read returns the bytes that have arrived, which is at most the number
        asked for and often fewer. This keeps reading until the count is met.

        Args:
            count (int): The number of bytes to read.

        Returns:
            bytes: The bytes read, short only if the peer closed the
                   connection first.
        """
        chunks = []
        pending = count

        while pending > 0:
            chunk = self.sock.recv(pending)

            # An empty read is the peer closing the connection, and no amount
            # of further reading will produce the missing bytes.
            if not chunk:
                break

            chunks.append(chunk)
            pending -= len(chunk)

        return b"".join(chunks)

    def _receive_header(self) -> bytes:
        """Read the MBAP header, or nothing where the peer closed cleanly.

        Returns:
            bytes: The header, or empty where nothing arrived at all

        Raises:
            ModbusNetworkError: If the peer closed part way through the header
        """
        header_bytes = self._recv_exactly(HEADER_SIZE)

        # A clean close between frames, as opposed to during one
        if not header_bytes:
            return b""

        if len(header_bytes) < HEADER_SIZE:
            reason = f"The peer closed the connection after {len(header_bytes)} of the {HEADER_SIZE} header byte(s)"
            raise ModbusNetworkError(message=reason)

        return header_bytes

    @staticmethod
    def _pdu_length(header_bytes: bytes) -> int:
        """Return how many PDU bytes the header says follow it.

        Args:
            header_bytes (bytes): A complete MBAP header

        Returns:
            int: The PDU byte count

        Raises:
            ModbusPacketError: If the declared length describes no frame
        """
        header = ModbusHeader.deserialize(header_bytes)

        # The header read already consumed the unit identifier, which the
        # length field counts, so length - 1 PDU bytes remain.
        pdu_length = header.length - 1

        # The field arrives from the network and is never trusted on its own.
        # A length of zero or less describes no frame at all.
        if pdu_length < 0:
            reason = f"The MBAP length field declares {header.length} byte(s), too few to cover the unit identifier"
            raise ModbusPacketError(reason)

        return pdu_length

    def _receive_pdu(self, pdu_length: int) -> list[bytes]:
        """Read the PDU, fragment-sized where one is configured.

        The split never changes how many bytes arrive.

        Args:
            pdu_length (int): The byte count the header declared

        Returns:
            list: The chunks read, in arrival order

        Raises:
            ModbusNetworkError: If the peer closed part way through the PDU
        """
        fragments = []
        pending = pdu_length

        while pending > 0:
            chunk_size = min(self.frag_size, pending) if self.frag_size else pending
            chunk = self._recv_exactly(chunk_size)

            if len(chunk) < chunk_size:
                reason = (
                    "The peer closed the connection "
                    f"{pdu_length - pending + len(chunk)} byte(s) into a "
                    f"frame declaring {pdu_length} byte(s) of PDU"
                )
                raise ModbusNetworkError(message=reason)

            fragments.append(chunk)
            pending -= len(chunk)

        return fragments

    def receive(self) -> bytes:
        """Receives one complete Modbus message from the connected socket.

        TCP carries a byte stream rather than a sequence of messages, so a read
        can produce part of an ADU, exactly one, or several back to back. The
        MBAP length field says how long the frame is, and this method returns
        only once that many bytes have arrived. It therefore blocks until the
        frame completes, the socket times out, or the peer disconnects.

        Returns:
            bytes: One complete Modbus message, or an empty string if the peer
                   closed the connection before sending anything.

        Raises:
            ModbusNetworkError: On a socket error, or if the peer disconnects
                                part way through a frame.
            ModbusPacketError: If the header does not describe a frame.
        """
        try:
            # A frame always opens with the MBAP header, which carries the
            # length needed to find where the frame ends.
            header_bytes = self._receive_header()

            # A clean close between frames, as opposed to during one
            if not header_bytes:
                return b""

            pdu_length = self._pdu_length(header_bytes)
            fragments = [header_bytes, *self._receive_pdu(pdu_length)]

            # Assemble the fragments into a complete message
            message = self.fragmenter.assemble(fragments)

        # Raised deliberately above, and already carrying the reason. Wrapping
        # them again would bury a framing fault inside a transport error.
        except ModbusBaseError:
            raise

        except OSError as e:
            self.log.warning("receive failed: %s", e)
            reason = f"Error receiving Modbus message: {e!s}"
            raise ModbusNetworkError(message=reason) from e

        else:
            return message


class ModbusTcpSender(ModbusSenderAbc):
    """Sends a sequence of Modbus messages over TCP.

    Sends several messages in one shot, which is what makes it useful for
    stress, load and denial-of-service testing against a peer.

    Safe to drive from more than one thread: the lock covers the fragment
    settings and the send loop together, so a setter cannot land mid-copy and
    two callers cannot interleave fragments into a malformed frame. The cost
    is that a setter waits for a send in progress. Calling stop() makes the
    next run_once() do nothing.

    Args:
        sock (socket.socket)    : A TCP socket.
        packets (iterable)      : A list of Modbus packets.

    Usage:
        This class needs a connected socket, so the demonstration lives in
        `examples/capture_a_burst_of_packets.py` rather than here. It opens
        both ends in one process, sends three requests in a single shot, and
        captures them with `ModbusTcpReceiver` at the far end. CI runs it on
        every pull request.

        The socket may be either end of a connection. A sender on a client
        socket drives requests at a server; a sender on a connection returned
        by `accept` drives responses back at a client. The class does not
        care which, and the example uses the first.
    """

    def __init__(
        self,
        sock: socket.socket,
        packets: Iterable[ModbusTcpPacket] = (),
        frag_size: int = 0,
        frag_delay: float = 0,
        burst_mode: bool = False,
        log: logging.Logger | None = None,
    ) -> None:
        """Bind the socket, the packets to send, and the fragmentation settings."""
        # Injected so a caller keeps control of where the transport's output
        # goes; the fallback is silent.
        self.log = log or _LOG

        # Set the sender attributes
        self.sock = sock
        self.packets = packets

        # Set the fragmentation attributes
        self._frag_size = frag_size
        self._frag_delay = frag_delay
        self._burst_mode = burst_mode

        # Create the stream instance
        self.stream = ModbusTcpStream(
            sock=self.sock, frag_size=self._frag_size, frag_delay=self._frag_delay, burst=self._burst_mode
        )

        # Create a lock for thread-safety
        self._lock = threading.Lock()

        # Create a stop event
        self._stop = threading.Event()

    def set_frag_size(self, value: int) -> ModbusTcpSender:
        """Sets the fragment size in bytes."""
        with self._lock:
            self._frag_size = value

        return self

    def set_frag_delay(self, value: float) -> ModbusTcpSender:
        """Sets the fragment delay in seconds."""
        with self._lock:
            self._frag_delay = value

        return self

    def set_burst_mode(self, value: bool) -> ModbusTcpSender:
        """Sets the burst mode."""
        with self._lock:
            self._burst_mode = value

        return self

    def run_once(self) -> None:
        """Sends the provided Modbus messages with optional fragmentation."""
        # A stopped sender does no work. Reading the event here is what makes
        # stop() observable rather than a call that changes nothing.
        if self._stop.is_set():
            return

        # Held across the copy and the send loop together: a setter landing
        # between them, or two senders interleaving, malforms a frame.
        with self._lock:
            # Update the stream attributes before sending messages
            self.stream.frag_size = self._frag_size
            self.stream.frag_delay = self._frag_delay
            self.stream.burst = self._burst_mode

            try:
                # Iterate through the packets
                for packet in self.packets:
                    # The MBAP length counts the unit identifier plus the PDU.
                    packet.header.length = len(packet.pdu) + 1

                    # Serialize the packet
                    message = packet.serialize()

                    # Send the message
                    self.stream.send(message)

            # serialize() and send() already raise a specific ModbusBaseError
            # subclass; relabeling it here would discard which one it was.
            except ModbusBaseError as e:
                self.log.warning("buffered send failed: %s", e)
                raise

    def stop(self) -> None:
        """Stops sending messages and closes the socket."""
        self._stop.set()


class ModbusTcpReceiver(ModbusReceiverAbc):
    """Receives a sequence of Modbus messages over TCP.

    Keeps what arrives, which is what makes it useful for monitoring traffic,
    debugging a client, or replaying a capture.

    Safe to drive from more than one thread: the lock covers the collected
    packets and the fragment setting, so a reader never sees a partial append.
    It is taken per append rather than held across the receive loop, so a
    reader is not blocked for as long as the socket stays open. Calling stop()
    ends the loop at the next message boundary.

    Args:
        sock (socket.socket)    : A TCP socket to receive messages.

    Usage:
        This class needs a connected socket, so the demonstration lives in
        `examples/capture_a_burst_of_packets.py` rather than here. It sends
        three requests down one end of a connection and captures them off the
        other. CI runs it on every pull request.

        `run_once` reads until the peer goes away or `stop` is called, so a
        caller that keeps the connection open drives it from its own thread
        and calls `stop` to end the capture. The example takes the simpler
        route and closes the sending end.
    """

    def __init__(self, sock: socket.socket, frag_size: int = 0, log: logging.Logger | None = None) -> None:
        """Bind the socket to receive on and the fragment size to read in."""
        # Injected so a caller keeps control of where the transport's output
        # goes; the fallback is silent.
        self.log = log or _LOG

        # If no socket is provided, create a new one
        self.sock = sock

        # Set the fragmentation attributes
        self._frag_size = frag_size

        # Create the stream instance
        self.stream = ModbusTcpStream(sock=self.sock, frag_size=self._frag_size)

        # Create a lock for thread-safety
        self._lock = threading.Lock()

        # Create a stop event
        self._stop = threading.Event()

        # Create a list to store the received messages
        self.packets: list[ModbusTcpPacket] = []

    def set_frag_size(self, value: int) -> ModbusTcpReceiver:
        """Sets the fragment size in bytes."""
        with self._lock:
            self._frag_size = value

        return self

    def run_once(self) -> list[ModbusTcpPacket]:
        """Receives Modbus messages until no more messages are available."""
        # A stopped receiver does no work, the same way a stopped sender does
        # none. Reading the event is what makes stop() observable.
        if self._stop.is_set():
            return self.packets

        # For the copy alone. The loop below takes it per append, and this lock
        # is not reentrant, so holding it here deadlocks on the first message.
        with self._lock:
            # Update the stream attributes before receiving messages
            self.stream.frag_size = self._frag_size

        try:
            # Iterate until all the packets are received
            while True:
                # A stop arriving mid-loop ends it at the next boundary rather
                # than once the socket happens to drain.
                if self._stop.is_set():
                    break

                # Receive the full message
                message = self.stream.receive()

                # If no message is received, break the loop
                if not message:
                    break

                # Parse the message into packets
                packet = ModbusTcpPacket.deserialize(message)

                with self._lock:
                    self.packets.append(packet)

        # receive() and deserialize() already raise a specific ModbusBaseError
        # subclass; relabeling it here would discard which one it was.
        except ModbusBaseError as e:
            self.log.warning("buffered receive failed: %s", e)
            raise

        # Return the received messages
        return self.packets

    def stop(self) -> None:
        """Stops receiving messages and closes the socket."""
        self._stop.set()
