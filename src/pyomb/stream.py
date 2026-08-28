# encoding: utf-8
"""Modbus TCP Straming Services

This Python module provides comprehensive tools for handling Modbus TCP
communications, including classes for sending, receiving, fragmenting, and
reassembling Modbus messages.

Features:

- ModbusSenderAbc   : Abstract base classes defining the contract for sending
- ModbusReceiverAbc : Abstract base classes defining the contract for receiving
- ModbusFragmenter  : Handles the fragmentation/reassembly of Modbus messages
- ModbusTcpStream   : Wraps the sending and receiving of Modbus messages
- ModbusTcpSender   : Buffered sender for Modbus messages over TCP/IP
- ModbusTcpReceiver : Buffered receiver for Modbus messages over TCP/IP
"""

from __future__ import print_function
from __future__ import unicode_literals

import threading
import time
import socket

from abc import ABCMeta, abstractmethod

from .packets import ModbusHeader
from .packets import ModbusTcpPacket
from .errors import ModbusNetworkError, ModbusPacketError, ModbusBaseError

# Modbus MBAP header size
HEADER_SIZE = ModbusHeader.SIZE


################################################################################
# ABSTRACT BASE CLASSES
################################################################################


class ModbusSenderAbc(metaclass=ABCMeta):
    """Abstract base class for sending Modbus messages."""

    # Burst is a property of the sender, not of one run: it sets TCP_NODELAY
    # on the socket the sender owns. The only implementation carries it as
    # state, set through the constructor or set_burst_mode, and no caller has
    # ever passed it here. Declaring it on the operation promised a per-call
    # choice that nothing honours; see ADR-009 for the same defect settled in
    # the packet hierarchy.
    @abstractmethod
    def run_once(self):
        """Sends the Modbus messages."""
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """Stops sending messages."""
        raise NotImplementedError


class ModbusReceiverAbc(metaclass=ABCMeta):
    """Abstract base class for receiving Modbus messages."""

    @abstractmethod
    def run_once(self):
        """Starts receiving Modbus messages."""
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """Stops receiving messages."""
        raise NotImplementedError


class ModbusFragmenterAbc(metaclass=ABCMeta):
    """Abstract base class for fragmenting/reassembling Modbus messages."""

    @abstractmethod
    def fragment(self, message, frag_size=7):
        """Fragments a Modbus message into smaller pieces."""
        raise NotImplementedError

    @abstractmethod
    def assemble(self, fragments):
        """Assembles fragmented Modbus messages into a complete message."""
        raise NotImplementedError


class ModbusStreamAbc(metaclass=ABCMeta):
    """Abstract base class for sending and receiving Modbus messages."""

    # Named for what every caller passes, which is the serialized bytes rather
    # than the packet object they came from. The implementation always called
    # it message; a supertype promising a different keyword is a promise its
    # own subtype breaks.
    @abstractmethod
    def send(self, message):
        """Sends a serialized packet"""
        raise NotImplementedError

    @abstractmethod
    def receive(self):
        """Receives a serialized packet"""
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
        >>> from pyomb.packets import ModbusHeader, ModbusRequestFC1
        >>> from pyomb.packets import ModbusTcpRequest
        >>> from pyomb.stream import ModbusFragmenter
        >>>
        >>> # Create a Modbus message
        >>> pdu = ModbusRequestFC1(start_addr=0, quantity=1)
        >>>
        >>> # Create the Modbus header and set the length (Unit-ID + PDU)
        >>> header = ModbusHeader(length=len(pdu)+1)
        >>>
        >>> # Create the Modbus packet
        >>> packet = ModbusTcpRequest(header=header, pdu=pdu)
        >>>
        >>> # Serialize the packet
        >>> message1 = packet.serialize()
        >>>
        >>> # Create the Modbus fragmenter
        >>> fragmenter = ModbusFragmenter()
        >>>
        >>> # Fragment the message
        >>> fragments = fragmenter.fragment(message1)
        >>>
        >>> # Assemble the fragments
        >>> message2 = fragmenter.assemble(fragments)
        >>>
        >>> # Check if the messages are equal
        >>> assert message1 == message2
    """

    @staticmethod
    def get_message_length(message):
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
    def fragment(message, frag_size=7):
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
            message = "The allowed fragment size is greater or equal to 0."
            raise ModbusPacketError(message)

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

            # Return the fragments
            return fragments

        except Exception as e:
            message = "Error fragmenting the Modbus packet: {0}".format(str(e))
            raise ModbusPacketError(message)

    @staticmethod
    def assemble(fragments):
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

    Example:
        >>> from pyomb.packets import ModbusRequestFC1, ModbusHeader, ModbusTcpRequest
        >>>
        >>> # Send a Modbus message to a Modbus server
        >>> sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        >>> sock.connect(('localhost', 502))
        >>>
        >>> # Create the desired PDU
        >>> pdu = ModbusRequestFC1(start_addr=0, quantity=1)
        >>>
        >>> # Create the Modbus header and set the length (Unit-ID + PDU)
        >>> header = ModbusHeader(length=len(pdu)+1)
        >>>
        >>> # Create the Modbus message
        >>> packet = ModbusTcpRequest(header=header, pdu=pdu)
        >>>
        >>> # Create the Modbus stream and send the message
        >>> stream = ModbusTcpStream(sock)
        >>> stream.send(packet.serialize())
    """

    def __init__(self, sock, fragmenter=ModbusFragmenter(), frag_delay=0, frag_size=0, burst=False):

        # If no TCP socket is provided, create a new one
        self.sock = sock or socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Create the fragmenter instance
        self.fragmenter = fragmenter

        # Set the fragmentation delay in seconds
        self.frag_delay = frag_delay

        # Set the fragmentation size in bytes
        self.frag_size = frag_size

        # Set the burst mode (send TCP packet without delay)
        self.burst = burst

    def send(self, message):
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
                time.sleep(self.frag_delay)

        except Exception as e:
            message = "Error sending Modbus message: {0}".format(str(e))
            raise ModbusNetworkError(message=message)

    def _recv_exactly(self, count):
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

    def receive(self):
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
            header_bytes = self._recv_exactly(HEADER_SIZE)

            # A clean close between frames, as opposed to during one
            if not header_bytes:
                return b""

            if len(header_bytes) < HEADER_SIZE:
                message = ("The peer closed the connection after {0} of the {1} header byte(s)").format(
                    len(header_bytes), HEADER_SIZE
                )
                raise ModbusNetworkError(message=message)

            # Deserialize the header
            header = ModbusHeader.deserialize(header_bytes)

            # The header read above already consumed the unit identifier, which
            # the length field counts, so length - 1 PDU bytes remain.
            pdu_length = header.length - 1

            # The field arrives from the network and is never trusted on its
            # own. A length of zero or less describes no frame at all.
            if pdu_length < 0:
                message = ("The MBAP length field declares {0} byte(s), too few to cover the unit identifier").format(
                    header.length
                )
                raise ModbusPacketError(message)

            # Add the header to the fragments list
            fragments = [header_bytes]
            pending = pdu_length

            # Read the PDU, in fragment-sized reads where a fragment size is
            # configured and in one read otherwise. The split changes how the
            # bytes are collected, never how many.
            while pending > 0:
                chunk_size = min(self.frag_size, pending) if self.frag_size else pending
                chunk = self._recv_exactly(chunk_size)

                if len(chunk) < chunk_size:
                    message = (
                        "The peer closed the connection {0} byte(s) into a frame declaring {1} byte(s) of PDU"
                    ).format(pdu_length - pending + len(chunk), pdu_length)
                    raise ModbusNetworkError(message=message)

                fragments.append(chunk)
                pending -= len(chunk)

            # Assemble the fragments into a complete message
            message = self.fragmenter.assemble(fragments)

            return message

        # Raised deliberately above, and already carrying the reason. Wrapping
        # them again would bury a framing fault inside a transport error.
        except ModbusBaseError:
            raise

        except Exception as e:
            message = "Error receiving Modbus message: {0}".format(str(e))
            raise ModbusNetworkError(message=message)


class ModbusTcpSender(ModbusSenderAbc):
    """Sends a sequence of Modbus messages over TCP.

    Some usecases for this class are:
    - Send multiple Modbus messages in a single shot
    - Simulating DDOS attacks
    - Stress testing the Modbus server to check stability
    - Load testing the Modbus server to check performance

    This class is safe to drive from more than one thread. Its lock covers the
    fragment settings and the send loop together: a setter cannot land between
    two of the three values being copied into the stream, and two callers
    cannot interleave fragments and put a malformed frame on the wire. The
    cost is that a setter waits for a send in progress, including its
    fragment delays. Calling stop() makes the next run_once() do nothing.

    Args:
        sock (socket.socket)    : A TCP socket.
        packets (iterable)      : A list of Modbus packets.

    Example:
        >>> from pyomb.packets import ModbusHeader
        >>> from pyomb.packets import ModbusRequestFC1, ModbusResponseFC1
        >>>
        >>> # Send packets to a Modbus server
        >>> sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        >>> sock.connect(('localhost', 502))
        >>> buf = [ModbusTcpPacket(header=ModbusHeader(), pdu=ModbusRequestFC1(start_addr=0, quantity=1))]
        >>> sender = ModbusTcpSender(sock=sock, packets=buf)
        >>> sender.run_once()
        >>>
        >>> # Send packets to a Modbus client
        >>> sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        >>> sock.bind(('localhost', 502))
        >>> sock.listen(1)
        >>> conn, addr = sock.accept()
        >>> buf = [ModbusTcpPacket(header=ModbusHeader(), pdu=ModbusResponseFC1(byte_count=2, data=(0, 1)))]
        >>> sender = ModbusTcpSender(sock=sock, packets=buf)
        >>> sender.run_once()
    """

    def __init__(self, sock, packets=(), frag_size=0, frag_delay=0, burst_mode=False):

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

    def set_frag_size(self, value):
        """Sets the fragment size in bytes."""

        with self._lock:
            self._frag_size = value

        return self

    def set_frag_delay(self, value):
        """Sets the fragment delay in seconds."""

        with self._lock:
            self._frag_delay = value

        return self

    def set_burst_mode(self, value):
        """Sets the burst mode."""

        with self._lock:
            self._burst_mode = value

        return self

    def run_once(self):
        """Sends the provided Modbus messages with optional fragmentation."""

        # A stopped sender does no work. Reading the event here is what makes
        # stop() observable; setting it and never consulting it left the call
        # changing nothing a later one could see.
        if self._stop.is_set():
            return

        # Held across the copy and the send loop together, not each in turn. A
        # setter landing between two of the three copies configures the stream
        # from two intentions at once, and two senders interleaving fragments
        # put a malformed frame on the wire.
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

            except Exception as e:
                message = "Error sending Modbus message: {0}".format(str(e))
                raise ModbusNetworkError(message=message)

    def stop(self):
        """Stops sending messages and closes the socket."""

        self._stop.set()


class ModbusTcpReceiver(ModbusReceiverAbc):
    """Receives a sequence of Modbus messages over TCP.

    Some usecases for this class are:
    - Store the received messages for further analysis and replay
    - Monitor the Modbus traffic
    - Debug the Modbus client

    This class is safe to drive from more than one thread. Its lock covers the
    collected packets and the fragment setting, so a reader walking the list
    never sees a partial append and a setter cannot land while the value is
    being copied into the stream. The lock is taken per append rather than
    held across the receive loop, so a reader is not blocked for as long as
    the socket stays open. Calling stop() ends the loop at the next message
    boundary and makes the next run_once() do nothing.

    Args:
        sock (socket.socket)    : A TCP socket to receive messages.

    Example:
        >>> # Receive packets from a Modbus server
        >>> sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        >>> sock.connect(('localhost', 502))
        >>> receiver = ModbusTcpReceiver(sock)
        >>> receiver.run_once()
        >>> print(receiver.packets)
        >>>
        >>> # Receive packets from a Modbus client
        >>> sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        >>> sock.bind(('localhost', 502))
        >>> sock.listen(1)
        >>> conn, addr = sock.accept()
        >>> receiver = ModbusTcpReceiver(conn)
        >>> receiver.run_once()
        >>> print(receiver.packets)

    """

    def __init__(self, sock, frag_size=0):

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
        self.packets = []

    def set_frag_size(self, value):
        """Sets the fragment size in bytes."""

        with self._lock:
            self._frag_size = value

        return self

    def run_once(self):
        """Receives Modbus messages until no more messages are available."""

        # A stopped receiver does no work, the same way a stopped sender does
        # none. Reading the event is what makes stop() observable.
        if self._stop.is_set():
            return self.packets

        # Taken for the copy alone rather than held across the loop below,
        # which also takes it per append -- this lock is not reentrant, and
        # holding it here would deadlock on the first message.
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

        except Exception as e:
            raise ModbusBaseError(message=str(e))

        # Return the received messages
        return self.packets

    def stop(self):
        """Stops receiving messages and closes the socket."""

        self._stop.set()
