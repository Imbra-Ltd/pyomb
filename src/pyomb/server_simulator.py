"""A scriptable Modbus TCP server, for exercising a client implementation.

The server runs in a thread of its own, multiplexes its clients with select,
and answers each request from a factory with one method per function code.
"""

from __future__ import annotations

import logging
import select
import socket
import ssl
import struct
import sys
import threading
import time
from collections.abc import Callable
from typing import cast

from .defines import OMB_EXCEPTION_ILLEGAL_DATA_VALUE, OMB_EXCEPTION_SLAVE_DEVICE_FAILURE
from .errors import (
    ModbusBaseError,
    ModbusModeError,
    ModbusNetworkError,
    ModbusPduParseError,
    ModbusSlaveDeviceFailureError,
)
from .logger import Logger
from .packets import (
    ModbusError,
    ModbusHeader,
    ModbusPdu,
    ModbusRequestFC1,
    ModbusRequestFC2,
    ModbusRequestFC3,
    ModbusRequestFC4,
    ModbusRequestFC5,
    ModbusRequestFC6,
    ModbusRequestFC15,
    ModbusRequestFC16,
    ModbusRequestFC22,
    ModbusRequestFC23,
    ModbusRequestFC43,
    ModbusResponseFC1,
    ModbusResponseFC2,
    ModbusResponseFC3,
    ModbusResponseFC4,
    ModbusResponseFC5,
    ModbusResponseFC6,
    ModbusResponseFC7,
    ModbusResponseFC15,
    ModbusResponseFC16,
    ModbusResponseFC22,
    ModbusResponseFC23,
    ModbusResponseFC43,
    ModbusTcpRequest,
    ModbusTcpResponse,
)
from .stream import ModbusTcpStream
from .tls import TlsRole, TlsSettings

# What a caller's handler is called with and what its answer means: false
# makes the server answer with an exception response instead of a reply.
DataHandler = Callable[[Logger, ModbusHeader, ModbusTcpRequest, socket.socket], bool]


class ModbusServerSimulator(threading.Thread):
    """Very simple Modbus TCP Server for test purposes.

    This class can be used to simulate a Modbus server for testing or
    development purposes. It supports a variety of Modbus function codes and
    allows for configuration of various parameters such as security,
    connection limits, and delays.

    For plain text communication, the server listens on port 502. For secure
    communication, the server listens on port 802.

    Args:
        log (Logger)             : The logger instance used to log messages.
        host (str)               : The interface to bind. Defaults to "",
                                   which binds every interface. Any form
                                   socket.bind accepts works, so a dotted
                                   quad or a resolvable name both do.
        port (int)               : The port of the server as a 16-bit integer.
                                   Pass 0 to let the operating system choose a
                                   free one; the attribute then reports that
                                   choice once start() returns.
        delay (float)            : The delay time for server response in
                                   seconds.
        frag_size (int)          : The Modbus message fragmentation size in
                                   bytes. 0 sends each message whole.
        frag_delay (float)       : The delay time between fragments.
        connection_limit (int)   : The maximum number of clients allowed to
                                   connect.
        inactive_timeout (float) : The inactivity timeout for a client.
        daemon (bool)            : Kill the server after the caller exits.
        tls (TlsSettings)        : The certificate material and TLS options.
                                   Defaults to None, which is plaintext;
                                   passing an instance is what turns TLS on.
                                   Every weakening it carries is logged at
                                   construction.
    """

    PLAINTEXT_PORT = 502
    ENCRYPTED_PORT = 802

    # Seconds start() waits for the listener before giving up on it.
    STARTUP_TIMEOUT = 10.0

    def __init__(
        self,
        log: Logger | None = None,
        host: str = "",
        port: int = 502,
        delay: float = 0,
        frag_size: int = 0,
        frag_delay: float = 0.0,
        connection_limit: int = 10,
        inactive_timeout: float = 1.0,
        daemon: bool = False,
        tls: TlsSettings | None = None,
    ) -> None:
        """Bind the listener settings, the response timing and the TLS material."""
        # Initialize the thread
        threading.Thread.__init__(self)

        # Set the thread name and logger
        self.name = "ModbusServerSimulator"
        self.log = log or Logger(self.name)
        self.log.addHandler(logging.NullHandler())

        # Set the server parameters
        self.host = host
        self.port = port
        self.delay = delay
        self.frag_size = frag_size
        self.frag_delay = frag_delay
        self.header_size = ModbusHeader.SIZE
        self.connection_limit = connection_limit
        self.inactive_timeout = inactive_timeout
        self.daemon = daemon
        self.quit_event = threading.Event()
        self.started_event = threading.Event()
        self.new_connection_event = threading.Event()
        self.read_list: list[socket.socket] = []
        self.clients: list[socket.socket] = []

        # Recorded per TLS connection and never read back here, so the
        # value is whatever getpeercert() returns for that session.
        self.peercerts: dict[socket.socket, object] = {}
        self.fail = False

        # Captured at accept time: getpeername() fails once a connection is
        # gone, which is when it is wanted. accept() reads it from here.
        self.peer_names: dict[socket.socket, tuple[str, int]] = {}

        self.process_connections = True  # Process connected clients by default
        self.data_handler: DataHandler | None = None

        # The TLS settings, or None for plaintext. One object rather than a
        # flag, so certificates cannot be handed over and silently unused.
        self.tls = tls

        if tls is not None:
            # A secure listener does not run on the plaintext port, so
            # naming no port binds the encrypted one.
            if port == ModbusServerSimulator.PLAINTEXT_PORT:
                self.port = ModbusServerSimulator.ENCRYPTED_PORT

            self.ssl_context = tls.context(TlsRole.SERVER)

            # Said out loud because the arguments cannot: a caller sees what
            # the session carries, not what they thought they set.
            for relaxation in tls.relaxations(TlsRole.SERVER):
                self.log.warning("TLS relaxed: %s", relaxation)

    ############################################################################

    def get_peers(self) -> list[tuple[str, int]]:
        """Get a tuple clients as list of tuples in the form (IP, PORT)."""
        result = []
        for x in self.read_list[1:]:
            result.append(x.getpeername())
        return result

    ############################################################################

    def set_delay(self, delay: float) -> None:
        """Set delay time for modbus response from server."""
        self.delay = delay

    ############################################################################

    def set_connection_limit(self, limit: int) -> None:
        """Set connection limit for modbus clients.

        Args:
            limit (int): The maximum number of clients allowed to connect.
        """
        self.connection_limit = limit

    ############################################################################

    def set_fail(self, fail: bool) -> None:
        """Set fail flag for modbus server to return an exception as response.

        Args:
            fail (bool): The flag to simulate a failure.
        """
        self.fail = fail

    ############################################################################

    def set_data_handler(self, data_handler: DataHandler) -> None:
        """Set a custom data handler.

        Args:
            data_handler (function): The custom data handler
        """
        self.data_handler = data_handler

    ############################################################################

    def disconnect(self, sock: socket.socket) -> None:
        """Graceful shutdown of a socket.

        Args:
            sock (socket.socket): The socket to disconnect.
        """
        try:
            if isinstance(sock, ssl.SSLSocket):
                sock = sock.unwrap()

            # A reset peer leaves nothing to shut down, and Linux reports
            # ENOTCONN where Windows is silent. Ordinary here, not a fault.
            sock.shutdown(socket.SHUT_RDWR)

        except OSError:
            self.log.info("The client doesn't respond with NOTIFY ALERT")

        finally:
            sock.close()

    ############################################################################

    def forget(self, conn: socket.socket, *registers: dict[socket.socket, float]) -> None:
        """Disconnects a client and drops everything recorded about it.

        The read list and the bookkeeping that shadows it have to fall away
        together. Leaving an entry behind in either direction is what turned a
        dropped client into a stale timestamp, and then into a KeyError that
        ended the server thread.

        Args:
            conn (socket.socket)    : The client connection to close.
            registers (dict)        : Per-connection dictionaries to clear.
        """
        self.disconnect(conn)

        if conn in self.read_list:
            self.read_list.remove(conn)

        # The live-client list feeds reset() and accept(), so a gone
        # connection leaves it too or reset() raises on the first dead one.
        if conn in self.clients:
            self.clients.remove(conn)

        self.peer_names.pop(conn, None)
        self.peercerts.pop(conn, None)

        for register in registers:
            register.pop(conn, None)

    ############################################################################

    def run(self) -> None:
        """Run the Modbus server until stopped."""
        self.log.info("Server starting")

        # An empty host binds every interface, deliberately: the device
        # under test is elsewhere. See PLAYBOOK, static analysis.
        srv = socket.socket()
        srv.bind((self.host, self.port))
        srv.setblocking(False)
        srv.listen(self.connection_limit)

        # Port 0 asks for a free one and the caller has no other way to
        # learn which. Assigned before the started event, so waiters see it.
        self.port = srv.getsockname()[1]

        # Add the server socket to the read list
        self.read_list.append(srv)

        # Keyed by the connection itself. getsockname() names the server on
        # every accepted socket, and a peer address is not unique either.
        last_activity_time = {}

        last_print_time = time.time()

        self.log.info("Server listening.")
        self.started_event.set()

        # Run the server until the quit event is set
        while not self.quit_event.is_set():
            # Wait for incoming connections or data from clients
            select_timeout = 1
            # Nothing is ever put on the write or error lists, so select can
            # only ever report readability back.
            ready_to_read, _, _ = select.select(self.read_list, [], [], select_timeout)

            # Check if the server socket is ready to accept a new connection
            current_time = time.time()
            if srv in ready_to_read:
                # The read list holds the listening socket plus one entry per
                # client, so the client count is one short of its length.
                client_count = len(self.read_list) - 1

                # Refuse the connection rather than leave the loop, which
                # let any peer stop the server by exceeding the limit.
                if client_count >= self.connection_limit:
                    refused, refused_addr = srv.accept()
                    self.log.info(f"Connection limit of {self.connection_limit} reached. Refusing {refused_addr}.")
                    refused.close()

                # Wait for a new connection
                else:
                    # Accept the new connection after 3-way handshake
                    conn, addr = srv.accept()
                    self.log.info(f"Connection request from {addr}")
                    # conn.setblocking(False)

                    # If the server is secure, wrap the connection in an SSL context
                    if self.tls is not None:
                        try:
                            conn = self.ssl_context.wrap_socket(conn, server_side=True)
                            self.peercerts[conn] = conn.getpeercert()
                        except ssl.SSLError as e:
                            self.log.info(e)

                    # Recorded in both modes: accept() reports it to a
                    # caller outside the thread, which never enters the list.
                    self.peer_names[conn] = addr

                    # Add the new connection to the read list
                    if self.process_connections:
                        # The connection will be processed by the simulator
                        # otherwise it is just stored and may be later processed from outside
                        self.read_list.append(conn)
                        last_activity_time[conn] = current_time

                    # Notify that a new cleint has connected
                    self.clients.append(conn)
                    self.new_connection_event.set()

            # Process the incoming data from the clients
            for conn in ready_to_read:
                # Only client connections are processed
                if conn is not srv:
                    try:
                        self.log.info(f"Connection.recv() - {self.peer_names.get(conn)}.")

                        # Create a Modbus TCP stream
                        stream = ModbusTcpStream(sock=conn, frag_delay=self.frag_delay, frag_size=self.frag_size)

                        # Receive the data from the client
                        data = stream.receive()

                    # receive() wraps every transport failure in a
                    # ModbusBaseError, which is not an OSError.
                    except (OSError, ModbusBaseError) as e:
                        self.forget(conn, last_activity_time)
                        self.log.info(f"Socket Error - {e}.")

                    # If no exception occurred, process the data
                    else:
                        # If the socket is closed by the peer, disconnect
                        if not data:
                            self.forget(conn, last_activity_time)
                            self.log.info("Connection closed by the peer.")

                        # Process the incoming data. The call needs a guard of
                        # its own: an else: branch is outside the try above it.
                        else:
                            last_activity_time[conn] = current_time

                            try:
                                self.on_data(data, conn)

                            # The top-level loop CLAUDE.md 2.2 carves out: a
                            # data_handler is a caller's and raises anything.
                            except Exception as e:  # noqa: BLE001
                                # Read before forget(), which drops the entry.
                                peer = self.peer_names.get(conn)

                                self.forget(conn, last_activity_time)
                                self.log.info(f"Dropping {peer} - {e}.")

            # Over a copy: closing one removes it from the list being
            # walked, which would skip the entry after it.
            for conn in list(self.read_list):
                if conn is srv:
                    continue

                # A connection the simulator never registered has no activity
                # to measure, so it is left alone rather than timed out.
                last_seen = last_activity_time.get(conn)

                if last_seen is None:
                    continue

                # Check if the connection is inactive for the specified timeout
                if (last_seen + self.inactive_timeout) < current_time:
                    self.log.info(f"{self.peer_names.get(conn)} inactive for {self.inactive_timeout} seconds. Closing.")
                    self.forget(conn, last_activity_time)

            # Print the connections status once in a while
            if (last_print_time + 1 < current_time) and self.process_connections:
                self.log.info(f"{list(self.peer_names.values())}: Clients connected {len(self.get_peers())}")
                last_print_time = current_time

        # After the server is stopped, close all client connections
        for conn in self.read_list:
            if conn is not srv:
                self.log.info(f"Closing client socket {conn.getsockname()}.")
                self.disconnect(conn)

        # Close the server socket
        self.log.info(f"Closing server socket {srv.getsockname()}.")
        srv.close()

        self.started_event.clear()
        self.log.info("Server stopped.")

    ############################################################################
    def on_data(self, data: bytes, conn: socket.socket) -> None:
        """Handles incoming data from a Modbus client connection.

        Parses the incoming data, determines the Modbus function code, and generates
        a corresponding Modbus response. The response is then serialized and sent back
        to the client.

        Args:
            data (bytes): The incoming data from the client connection.
            conn (socket.socket): The socket object representing the client connection.

        Returns:
            None

        Raises:
            ModbusSlaveDeviceFailureError: If an error occurs while processing the request.
            ModbusPacketError: If the header is unreadable, leaving nothing to echo.
        """
        try:
            # Deserialize the incoming data
            request = ModbusTcpRequest.deserialize(data)

        # The header parsed, so the peer can be told what was wrong instead of
        # meeting a closed socket it cannot diagnose.
        except ModbusPduParseError as e:
            self.log.info(f"Answering an unparsable PDU with an exception response: {e}")
            self.answer(e.header, ModbusError(fc=e.fc, exc_code=OMB_EXCEPTION_ILLEGAL_DATA_VALUE), conn)

            return

        self.log.info(request)

        # Call the custom data handler if provided
        rslt_ok = True
        if self.data_handler:
            rslt_ok = self.data_handler(self.log, request.header, request, conn)

        # Delay the response if necessary
        time.sleep(self.delay)

        try:
            response_pdu: ModbusPdu

            # Check if the fail simulate flag is set or the data handler failed
            if self.fail or not rslt_ok:
                response_pdu = ResponseFactory.create_err_rsp(request.pdu.fc)

            else:
                # The function code is a field, not a class, so the
                # registry is what ties the branch to the cast below.

                # Read coils (FC=1)
                if request.pdu.fc == 1:
                    response_pdu = ResponseFactory.create_fc1_rsp(cast("ModbusRequestFC1", request.pdu))

                # Read discrete inputs (FC=2)
                elif request.pdu.fc == 2:
                    response_pdu = ResponseFactory.create_fc2_rsp(cast("ModbusRequestFC2", request.pdu))

                # Read holding registers (FC=3)
                elif request.pdu.fc == 3:
                    response_pdu = ResponseFactory.create_fc3_rsp(cast("ModbusRequestFC3", request.pdu))

                # Read input registers (FC=4)
                elif request.pdu.fc == 4:
                    response_pdu = ResponseFactory.create_fc4_rsp(cast("ModbusRequestFC4", request.pdu))

                # Write single coil (FC=5)
                elif request.pdu.fc == 5:
                    response_pdu = ResponseFactory.create_fc5_rsp(cast("ModbusRequestFC5", request.pdu))

                # Write single register (FC=6)
                elif request.pdu.fc == 6:
                    response_pdu = ResponseFactory.create_fc6_rsp(cast("ModbusRequestFC6", request.pdu))

                # Report slave ID (FC=7)
                elif request.pdu.fc == 7:
                    response_pdu = ResponseFactory.create_fc7_rsp()

                # Write multiple coils (FC=15)
                elif request.pdu.fc == 15:
                    response_pdu = ResponseFactory.create_fc15_rsp(cast("ModbusRequestFC15", request.pdu))

                # Write multiple registers (FC=16)
                elif request.pdu.fc == 16:
                    response_pdu = ResponseFactory.create_fc16_rsp(cast("ModbusRequestFC16", request.pdu))

                # Mask write register (FC=22)
                elif request.pdu.fc == 22:
                    response_pdu = ResponseFactory.create_fc22_rsp(cast("ModbusRequestFC22", request.pdu))

                # Read/write multiple registers (FC=23)
                elif request.pdu.fc == 23:
                    response_pdu = ResponseFactory.create_fc23_rsp(cast("ModbusRequestFC23", request.pdu))

                # Read device identification (FC=43)
                elif request.pdu.fc == 43:
                    response_pdu = ResponseFactory.create_fc43_rsp(cast("ModbusRequestFC43", request.pdu))

                # Generate response on invalid function code
                else:
                    response_pdu = ResponseFactory.create_err_rsp(request.pdu.fc)

            self.answer(request.header, response_pdu, conn)

        # Any failure building or sending the response becomes exception code
        # 0x04, which is what that code means. The cause travels with it.
        except Exception as e:
            self.log.info(f"Error: {e}")
            raise ModbusSlaveDeviceFailureError() from e

    ############################################################################
    def answer(self, request_header: ModbusHeader, response_pdu: ModbusPdu, conn: socket.socket) -> None:
        """Send one response, echoing the identifiers the request carried.

        Args:
            request_header (ModbusHeader)   : The header of the request answered.
            response_pdu (ModbusPdu)        : The PDU to send back.
            conn (socket.socket)            : The connection to answer on.

        Returns:
            None
        """
        # A response echoes the transaction, protocol and unit identifiers
        # unchanged; only the length is its own.
        response_header = ModbusHeader(
            trans_id=request_header.trans_id,
            prot_id=request_header.prot_id,
            length=len(response_pdu) + 1,  # Add 1 for the unit ID
            unit_id=request_header.unit_id,
        )

        # Create the response
        response = ModbusTcpResponse(header=response_header, pdu=response_pdu)

        # Create a Modbus TCP stream and send the response
        sender = ModbusTcpStream(sock=conn, frag_delay=0, frag_size=0, burst=False)

        # Send the response
        sender.send(response.serialize())

    ############################################################################

    def stop(self) -> None:
        """Stop the Modbus server."""
        self.quit_event.set()

    ############################################################################

    def start(self, process_connections: bool = True, timeout: float = STARTUP_TIMEOUT) -> None:
        """Start the Modbus server and wait for its listener to come up.

        Args:
            process_connections (bool)  : Process connected clients.
            timeout (float)             : Seconds to wait for the listener.

        Raises:
            ModbusNetworkError : If the listener does not come up, which a
                                 port already in use is the usual cause of.
        """
        # Set the processing mode
        self.process_connections = process_connections

        # Start the server thread
        super().start()

        # Bounded, with a liveness check. Unbounded, a port already in use
        # hung the caller for good with the reason only on stderr.
        self.log.info("Waiting for the server to start.")
        deadline = time.time() + timeout

        while not self.started_event.is_set():
            if not self.is_alive():
                message = f"The server thread ended before the listener on port {self.port} came up"
                raise ModbusNetworkError(message=message)

            if time.time() >= deadline:
                message = f"The listener on port {self.port} did not come up within {timeout} second(s)"
                raise ModbusNetworkError(message=message)

            time.sleep(0.05)

    ############################################################################

    def reset(self) -> None:
        """Reset the Modbus server."""
        for sock in list(self.clients):
            self.log.info("Reset the client connection...")

            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                sock.close()

            # Already gone. Linger means nothing without a connection, and
            # one client leaving used to make this unusable for the rest.
            except OSError:
                self.log.info("The client connection was already closed")

        self.clients = []
        self.stop()

    ############################################################################

    def accept(self, timeout: float) -> tuple[socket.socket | None, tuple[str, int] | None]:
        """Accept a new client connection.

        Args:
            timeout (float): The timeout for accepting a new connection.

        Returns:
            tuple: The connection and its peer address, or (None, None) if no
                   client arrived within the timeout.
        """
        # The server owns the connections in this mode, so handing one out
        # would give a single socket two owners.
        if self.process_connections:
            raise ModbusModeError(message="accept() is unavailable while the server processes connections itself")

        # If there are no clients, wait for a new connection
        if len(self.clients) == 0:
            # Cleared before the wait, not after: an earlier accept left it
            # set, so the next wait returned at once on a client not yet there.
            self.new_connection_event.clear()
            self.new_connection_event.wait(timeout)

        # If there are clients, return the first one
        for conn in list(self.clients):
            self.clients.remove(conn)

            # The peer address, captured at accept time. getsockname() here
            # names the server and is identical for every client.
            return conn, self.peer_names.get(conn)

        # A timeout is an ordinary outcome, so it is reported as a pair rather
        # than as a bare None that breaks `conn, addr = accept(...)`.
        return None, None

    ############################################################################


class ResponseFactory:
    """Factory class for generating Modbus Response PDUs.

    This class provides static methods for generating Modbus Response PDUs for
    various Modbus function codes. It wraps the creation of the response and
    implements the necessary logic for each function code.
    """

    @staticmethod
    def create_fc1_rsp(request_pdu: ModbusRequestFC1, coil_value: int = 0xFF) -> ModbusResponseFC1:
        """Create a Modbus Response for Function Code 1 (Read Coils).

        This function takes a Modbus Request PDU (request_pdu) and an optional
        coil_value (default is 0xff).It calculates the byte count based on the
        quantity of coils requested in the request_pdu.

        Then it creates a Modbus Response for Function Code 1 with the calculated
        byte count and a list of coil_value repeated byte_count times.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU
            coil_value (int, optional): The value to return for the coils.

        Returns:
            ModbusResponseFC1(): The Modbus Response PDU for Function Code 1.
        """
        # Calculate the byte count by ensuring that the byte count is rounded up
        byte_count = (request_pdu.quantity + 7) // 8

        # Create the coil values for the response PDU
        values = byte_count * (coil_value,)

        pdu = ModbusResponseFC1(byte_count=byte_count, output_status=values)

        return pdu

    @staticmethod
    def create_fc2_rsp(request_pdu: ModbusRequestFC2, input_value: int = 0xFF) -> ModbusResponseFC2:
        """Create a Modbus Response for Function Code 2 (Read Discrete Inputs).

        This function takes a Modbus Request PDU (request_pdu) and an optional
        coil_value (default is 0xff). It calculates the byte count based on the
        quantity of coils requested in the request_pdu. Then it creates a
        Modbus Response for Function Code 2 with the calculated byte count and
        a list of coil_value repeated byte_count times.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU
            input_value (int): The value to be used for the digital inputs

        Returns:
            ModbusResponseFC2(): The Modbus Response PDU for Function Code 2.
        """
        # Calculate the byte count by ensuring that the byte count is rounded up
        byte_count = (request_pdu.quantity + 7) // 8

        # Create the input status for the response PDU
        values = byte_count * (input_value,)

        pdu = ModbusResponseFC2(byte_count=byte_count, input_status=values)

        return pdu

    @staticmethod
    def create_fc3_rsp(request_pdu: ModbusRequestFC3, register_value: int = 0xFFFF) -> ModbusResponseFC3:
        """Create a Modbus Response for Function Code 3 (Read Holding Registers).

        This function takes a Modbus Request PDU (request_pdu) and an optional
        register_value (default is 0xffff). It calculates the byte count based
        on the quantity of registers requested in the request_pdu. Then it
        creates a Modbus Response for Function Code 3 with the calculated
        byte count and a list of register_value repeated byte_count times.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU containing
            the quantity of registers to be read.
            register_value (int, optional): The value to be used for the
            registers in the response. Defaults to 0xffff.

        Returns:
            ModbusResponseFC3(): The Modbus Response PDU for Function Code 3.
        """
        # Get the quantity of registers to read from the request PDU
        quantity = request_pdu.quantity

        # Calculate the byte count and create the register values
        byte_count = 2 * quantity

        # Create the register values for the response PDU
        register_values = quantity * (register_value,)

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC3(byte_count=byte_count, values=register_values)

        return pdu

    @staticmethod
    def create_fc4_rsp(request_pdu: ModbusRequestFC4, register_value: int = 0xFFFF) -> ModbusResponseFC4:
        """Create a Modbus Response for Function Code 4 (Read Input Registers).

        This function takes a Modbus Request PDU (request_pdu) and an optional
        register_value (default is 0xffff). It calculates the byte count based
        on the quantity of registers requested in the request_pdu. Then it
        creates a Modbus Response for Function Code 4 with the calculated
        byte count and a list of register_value repeated byte_count times.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU
            register_value (int): The register values

        Returns:
            ModbusResponseFC4(): The Modbus Response PDU for Function Code 4.
        """
        # Get the quantity of registers to read from the request PDU
        quantity = request_pdu.quantity

        # Calculate the byte count and create the register values
        byte_count = 2 * quantity

        # Create the register values for the response PDU
        register_values = quantity * (register_value,)

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC4(byte_count=byte_count, values=register_values)

        return pdu

    @staticmethod
    def create_fc5_rsp(request_pdu: ModbusRequestFC5) -> ModbusResponseFC5:
        """Create a Modbus Response for Function Code 5 (Write Single Coil).

        This function takes a Modbus Request PDU (request_pdu) and creates a
        Modbus Response for Function Code 5. The response contains the address
        of the coil that was written and the value that was written.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU

        Returns:
            ModbusResponseFC5(): The Modbus Response PDU for Function Code 5.
        """
        # Get the address and value of the coil to write from the request PDU
        address = request_pdu.output_address
        coil_value = request_pdu.output_value

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC5(output_address=address, output_value=coil_value)

        return pdu

    @staticmethod
    def create_fc6_rsp(request_pdu: ModbusRequestFC6) -> ModbusResponseFC6:
        """Create a Modbus Response for Function Code 6 (Write Single Register).

        This function takes a Modbus Request PDU (request_pdu) and creates a
        Modbus Response for Function Code 6. The response contains the address
        of the register that was written and the value that was written.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU

        Returns:
            ModbusResponseFC6(): The Modbus Response PDU for Function Code 6.
        """
        # Get the address and value of the register to write from the request PDU
        address = request_pdu.output_address
        register_value = request_pdu.output_value

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC6(output_address=address, output_value=register_value)

        return pdu

    @staticmethod
    def create_fc7_rsp(status_code: int = 0x00) -> ModbusResponseFC7:
        """Create a Modbus Response for Function Code 7 (Report Slave ID).

        This function takes an optional status_code parameter (default is 0x00).
        It creates a Modbus Response for Function Code 7 with the provided status_code.
        The response PDU contains the status code and the slave ID.

        Args:
        status_code (int): The status code to be used in the response.

        Returns:
            ModbusResponseFC7(): The Modbus Response PDU for Function Code 7.
        """
        # Create the Modbus Response PDU
        pdu = ModbusResponseFC7(status=status_code)
        return pdu

    @staticmethod
    def create_fc15_rsp(request_pdu: ModbusRequestFC15) -> ModbusResponseFC15:
        """Create a Modbus Response for Function Code 15 (Write Multiple Coils).

        This function takes a Modbus Request PDU (request_pdu) and creates a
        Modbus Response for Function Code 15. The response contains the address
        of the coil that was written and the value that was written.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU containing the
                address of the coil to be written and the value to be written.

        Returns:
            ModbusResponseFC15(): The Modbus Response PDU for Function Code 15.
        """
        # Get the address and quantity of coils to write from the request PDU
        address = request_pdu.start_addr
        coils_quantity = request_pdu.quantity

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC15(start_addr=address, quantity=coils_quantity)

        return pdu

    @staticmethod
    def create_fc16_rsp(request_pdu: ModbusRequestFC16) -> ModbusResponseFC16:
        """Create a Modbus Response for FC16 (Write Multiple Registers).

        This function takes a Modbus Request PDU (request_pdu) and creates a
        Modbus Response for Function Code 16. The response contains the address
        of the register that was written and the value that was written.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU containing the
                address of the register to be written and the value to be written.

        Returns:
            ModbusResponseFC16(): The Modbus Response PDU for Function Code 16.
        """
        # Get the address and quantity of registers to write from the request PDU
        address = request_pdu.start_addr
        registers_quantity = request_pdu.quantity

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC16(start_addr=address, quantity=registers_quantity)

        return pdu

    @staticmethod
    def create_fc22_rsp(request_pdu: ModbusRequestFC22) -> ModbusResponseFC22:
        """Create a Modbus Response for FC22 (Mask Write Register).

        This function takes a Modbus Request PDU (request_pdu) and creates a
        Modbus Response for Function Code 22. The response contains the address
        of the register that was written and the value that was written.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU

        Returns:
            ModbusResponseFC22(): The Modbus Response PDU for Function Code 22.
        """
        # Get the reference address, and mask, and or mask from the request PDU
        ref_address = request_pdu.ref_addr
        and_mask = request_pdu.and_mask
        or_mask = request_pdu.or_mask

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC22(ref_addr=ref_address, and_mask=and_mask, or_mask=or_mask)

        return pdu

    @staticmethod
    def create_fc23_rsp(request_pdu: ModbusRequestFC23, value: int = 0xFFFF) -> ModbusResponseFC23:
        """Create a Modbus Response for FC23 (Read/Write Multiple Registers).

        This function takes a Modbus Request PDU (request_pdu) and an optional
        value (default is 0xffff). It calculates the byte count based on the
        quantity of registers requested in the request_pdu. Then it creates a
        Modbus Response for Function Code 23 with the calculated byte count
        and a list of value repeated byte_count times.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU
            value (int): The value to be used for the registers in the response.

        Returns:
            ModbusResponseFC23(): The Modbus Response PDU for Function Code 23.
        """
        # Get the number of registers to read/write
        read_count = request_pdu.read_quantity

        # Calculate the byte count and create the data
        byte_count = 2 * read_count

        # Create the data for the response
        data = read_count * (value,)

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC23(byte_count=byte_count, values=data)
        return pdu

    @staticmethod
    def create_fc43_rsp(request_pdu: ModbusRequestFC43) -> ModbusResponseFC43:
        """Create a Modbus Response for FC43 (Read Device Identification).

        This function creates a Modbus Response for Function Code 43. The
        response PDU contains the byte count and the values of the registers.

        Args:
            request_pdu (ModbusPdu): The Modbus Request PDU

        Returns:
            ModbusResponseFC43(): The Modbus Response PDU for Function Code 43.
        """
        # Get the MEI type and MEI data from the request PDU
        mei_type = request_pdu.mei_type
        mei_data = request_pdu.mei_data

        # Create the Modbus Response PDU
        pdu = ModbusResponseFC43(mei_type=mei_type, mei_data=mei_data)
        return pdu

    @staticmethod
    def create_err_rsp(request_fc: int) -> ModbusError:
        """Creates the exception response a failed request is answered with.

        Args:
            request_fc (int): The function code the request carried.

        Returns:
            ModbusError(): The exception PDU, carrying code 0x04.
        """
        response_pdu = ModbusError(fc=request_fc, exc_code=OMB_EXCEPTION_SLAVE_DEVICE_FAILURE)

        return response_pdu


def run_server() -> None:
    """Run the Modbus server to simulate a Modbus device."""
    log = Logger("ModbusServerSimulator")
    server_thread = ModbusServerSimulator(
        log=log,
        host="",
        connection_limit=50,
        inactive_timeout=60,
        # frag_size=2,
        frag_delay=0,
    )
    server_thread.start()

    # Python 2's input() evaluated what it read and could raise SyntaxError.
    # Python 3's returns the string, so the guard that stood here never fired.
    input("Press enter to continue")

    server_thread.stop()
    server_thread.join()


if __name__ == "__main__":
    # Inside the guard, never at import: stdout belongs to the application.
    # Checked rather than assumed -- see PLAYBOOK, entry-point output encoding.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    run_server()
