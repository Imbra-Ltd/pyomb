# coding: utf-8
from __future__ import print_function, unicode_literals

import contextlib
import logging
import socket
import ssl
import struct
import sys

from .errors import ModbusIllegalDataValue, ModbusIllegalFunction, ModbusNetworkError
from .logger import Logger
from .packets import (
    ModbusHeader,
    ModbusRequestFC1,
    ModbusRequestFC2,
    ModbusRequestFC3,
    ModbusRequestFC4,
    ModbusRequestFC5,
    ModbusRequestFC6,
    ModbusRequestFC7,
    ModbusRequestFC15,
    ModbusRequestFC16,
    ModbusRequestFC22,
    ModbusRequestFC23,
    ModbusRequestFC43,
    ModbusTcpRequest,
    ModbusTcpResponse,
)
from .stream import ModbusTcpStream


class ModbusClientSimulator(object):
    """Very simple Modbus TCP Client used for testing purposes.

    Args:
        log (Logger):
            External logger.

        host (str):
            The remote host address. Defaults to 'localhost'.

        port (int):
            The remote port number. Defaults to 502.

        unit_id (int):
            The unit identifier addressed by every request. Defaults to 1.
            A device behind a gateway needs the id the gateway routes on.

        frag_count (int):
            Fragmentation size. Defaults to 0.

        frag_delay (int):
            Fragmentation delay. Defaults to 0.

        secure (bool):
            Enable security (SSL context). Defaults to False.

        protocol (int):
            The secure protocol to use. Defaults to ssl.PROTOCOL_TLS_CLIENT.

        cert (bytes):
            The client certificate in DER/PEM format. Defaults to None.

        key (bytes):
            The client private key in DER/PEM format. Defaults to None.

        ca_chain (bytes):
            The certificate chain file in DER/PEM format. Defaults to None.

        ciphers (str):
            Supported ciphers as string in OpenSSL format. Defaults to None,
            meaning the interpreter's secure default suite.

        verify_mode (int):
            The verification mode for the peer certificate. Defaults to
            ssl.CERT_REQUIRED.

        verify_hostname (bool):
            Flag to verify the peer hostname. Defaults to True. Disabling it
            accepts any certificate signed by the configured CA for any host.

        ssl_options (int):
            SSL options OR-ed into the context. Defaults to ssl.OP_ALL. They
            can only add a restriction, so a session may be pinned above
            MINIMUM_TLS_VERSION but never below it.

        timeout (float):
            Socket timeout in seconds, applied to connect and to reads.
            Defaults to DEFAULT_TIMEOUT. None blocks indefinitely.
    """

    # The transaction identifier is a 16-bit field, so the counter wraps here.
    TRANS_ID_MODULO = 0x10000

    # A response carrying an unexpected transaction identifier is dropped and
    # the read repeated, which is how a late reply to an abandoned request is
    # skipped over. The count is bounded so that a peer emitting a steady
    # stream of mismatches ends the exchange instead of holding the caller.
    MAX_STALE_RESPONSES = 8

    # None means "inherit the interpreter's secure default suite". The previous
    # default, 'ALL:', enabled 140 suites against the stdlib default of 17,
    # among them 12 anonymous key-exchange suites (ADH/AECDH) that authenticate
    # no peer at all. Callers testing weak-cipher interoperability pass an
    # explicit OpenSSL cipher string instead.
    DEFAULT_CIPHERS = None

    # Seconds applied to connect and to every subsequent read. A finite default
    # matters because a server that accepts a connection and then never replies
    # would otherwise block the caller forever with no way to recover. Pass
    # None to restore unbounded blocking.
    DEFAULT_TIMEOUT = 10.0

    # The lowest protocol version the transport will negotiate. MB-TCP-Security
    # v21 requires TLS 1.2 or better (R-32) and forbids negotiating down to TLS
    # 1.1, TLS 1.0 or SSL 3.0 (R-34), so the floor is the specification's
    # rather than a preference. Declaring it matters even where OpenSSL already
    # defaults here: that default is a property of the linked library and its
    # security level, so an older or differently configured build answers
    # differently and nothing in this library would notice.
    MINIMUM_TLS_VERSION = ssl.TLSVersion.TLSv1_2

    def __init__(
        self,
        log=None,
        host=b"localhost",
        port=502,
        unit_id=1,
        frag_count=0,
        frag_delay=0,
        secure=False,
        protocol=ssl.PROTOCOL_TLS_CLIENT,
        cert=None,
        key=None,
        ca_chain=None,
        ciphers=DEFAULT_CIPHERS,
        verify_mode=ssl.CERT_REQUIRED,
        verify_hostname=True,
        ssl_options=ssl.OP_ALL,
        timeout=DEFAULT_TIMEOUT,
    ):

        # Initialize the logger
        self.log = log or Logger(name="ModbusClientSimulator")
        self.log.addHandler(logging.NullHandler())

        # Initialize the client parameters
        self.timeout = timeout
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.frag_count = frag_count
        self.frag_delay = frag_delay
        self.header_size = 8

        # The identifier the next request will carry, and the one the pending
        # request carried. They differ once a request is in flight, which is
        # what lets a response be matched to it.
        self._next_trans_id = 0
        self._pending_trans_id = None

        # Security related parameters
        self.secure = secure
        self.ciphers = ciphers
        self.verify_mode = verify_mode
        self.verify_hostname = verify_hostname
        self.ssl_options = ssl_options

        # Initialize the certificates and keys
        self.cert = cert
        self.key = key
        self.ca_chain = ca_chain

        # SSL configuration
        if secure:
            # workaround that would not work if setting port 502 in security mode
            if port == 502:
                self.port = 802

            self.crypto = ssl.SSLContext(protocol)
            self.crypto.load_cert_chain(self.cert, self.key)
            self.crypto.load_verify_locations(self.ca_chain)

            if ciphers is not None:
                self.crypto.set_ciphers(str(ciphers))

            # Hostname checking is cleared before verify_mode is assigned:
            # PROTOCOL_TLS_CLIENT enables it by default, and the ssl module
            # refuses CERT_NONE while it is still on. It is re-applied after.
            self.crypto.check_hostname = False
            self.crypto.verify_mode = verify_mode
            self.crypto.check_hostname = verify_hostname

            self.crypto.options |= ssl_options

            # Applied after the caller's options, which are OR-ed in and so can
            # only add a restriction. ssl_options therefore still pins a session
            # higher than the floor, and neither passing a mask that omits the
            # protocol switches nor passing none at all can drop below it.
            self.crypto.minimum_version = self.MINIMUM_TLS_VERSION

        # Optional because disconnect() clears it. Inferring the type from
        # this first assignment alone claims the attribute is always a socket,
        # which is a claim the teardown path contradicts.
        self.sock: socket.socket | None = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)

    ############################################################################

    def _require_socket(self) -> socket.socket:
        """The client's socket, or a named error when it holds none.

        Returns:
            socket.socket : The socket the client currently holds

        Raises:
            ModbusNetworkError : If the client has been disconnected
        """

        if self.sock is None:
            message = "The client has no socket; call connect() first"
            raise ModbusNetworkError(message=message)

        return self.sock

    ############################################################################

    @property
    def recvbuf_size(self):
        """Get the receive buffer size of the socket."""
        return self._require_socket().getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)

    @recvbuf_size.setter
    def recvbuf_size(self, value):
        """Set the receive buffer size of the socket.

        Args:
            value (int): The buffer size value.
        """
        self._require_socket().setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, value)

    ############################################################################

    def connect(self, host=None, port=None):
        """Connects the client to the specified host and port.

        This method establishes a connection to the remote Modbus server. It
        takes optional arguments for host and port, defaulting to the values
        set during initialization. If no socket exists, a new socket is created.

        Args:
            host (bytes)    : The host address to connect to.
            port (int)      : The port number to connect to.
        """

        # Set the host and port if not provided
        host = self.host if host is None else host
        port = self.port if port is None else port

        # Check if socket still exists
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Applied before connect, so an unreachable peer fails rather than
        # hanging, and inherited by the wrapped socket below.
        self.sock.settimeout(self.timeout)

        # Encrypt socket
        if self.secure:
            self.sock = self.crypto.wrap_socket(self.sock, server_hostname=host)

        # Connect to the host
        try:
            self.sock.connect((host, port))
            self.log.info("Client connected")
        except Exception as e:
            raise e

    ############################################################################

    def disconnect(self):
        """Disconnects the client from the Modbus server and closes the socket.

        This method gracefully disconnects the client from the server and closes
        the underlying socket. It attempts to unwrap the socket from an SSL
        context if secure connection was used. It also handles potential socket
        errors during the shutdown process.
        """

        self.log.info("Disconnecting client...")

        # A caller that cannot tell whether it already disconnected should be
        # able to ask again, so a client holding no socket is done rather than
        # in error. The local is also what carries the narrowing: an attribute
        # stays narrowed only until the next call that could reassign it.
        sock = self.sock

        if sock is None:
            self.log.info("Client socket already closed")
            return

        try:
            # Check if the socket is an encrypted socket
            if isinstance(sock, ssl.SSLSocket):
                # If so unwrap the socket from the SSL context
                sock = sock.unwrap()

            # Send the FIN now and unconditionally. The close below only does
            # so once no other reference to the socket remains, so this is not
            # redundant -- dropping it changes what the peer observes.
            sock.shutdown(socket.SHUT_RDWR)

        except socket.error:
            pass

        finally:
            # A close fails on the same peer a shutdown does: gone away is the
            # ordinary case here, not a fault. Letting it escape would leave
            # the attribute set on a socket already given up on, so the clear
            # runs on every path including this one.
            with contextlib.suppress(socket.error):
                sock.close()

            self.sock = None

        self.log.info("Client socket closed")

    ############################################################################
    def reset(self):
        """Reset the client socket with linger option set to

        This method attempts to reset the client connection by closing the
        socket and setting the SO_LINGER option to (1, 0). The first argument
        enables the option, and the second argument sets the linger time to
        zero.

        Setting SO_LINGER with a linger time of zero instructs the kernel to
        not wait for any unsent data to be acknowledged when the socket is
        closed. This can be useful to force the connection to be terminated
        immediately, potentially improving recovery from errors or
        unexpected disconnections.
        """

        self.log.info("Reset the client connection...")

        sock = self._require_socket()

        # Configure the SO_LINGER option with a linger time of zero
        sock.setsockopt(
            socket.SOL_SOCKET,  # Level is SOL_SOCKET
            socket.SO_LINGER,  # Option is SO_LINGER
            struct.pack("ii", 1, 0),  # Enable flag is 1, Linger time is 0
        )

        # Close the socket
        sock.close()

    ############################################################################

    def _take_trans_id(self):
        """Claims the next transaction identifier for a request.

        The identifier is recorded as pending so that waitResponse() can tell
        the reply to this request from a late reply to an earlier one.

        Returns:
            int : The transaction identifier to send
        """

        trans_id = self._next_trans_id

        self._next_trans_id = (trans_id + 1) % self.TRANS_ID_MODULO
        self._pending_trans_id = trans_id

        return trans_id

    ############################################################################
    def sendRequest(
        self,
        fc,
        readAddress=0,
        readCount=1,
        writeAddress=0,
        writeCount=1,
        values=(0,),
        and_mask=0xFFFF,
        or_mask=0,
    ):
        """Sends a Modbus request to the server.

        This method creates a Modbus request based on the provided function
        code (fc) and arguments, serializes it into a bytearray, and sends it
        to the server using the configured socket.

        This is a very generic multi-purpose method that is very useful for
        testing and debugging purposes. It can be used to send any Modbus
        request to the server, including read and write operations, and
        various other Modbus functions in a burst fashion.
        """

        # Handle values based on function code and data type
        try:
            # Check if values is iterable (list, tuple)
            iter(values)

            # For FC5 and FC6, take the first value only (single value)
            if fc in (5, 6):
                # Taken through a list rather than by subscript, so that an
                # empty sequence is a value this code decides about instead of
                # an IndexError from the subscript, and so that the length is
                # never asked of something that cannot answer -- len() raises
                # TypeError on a generator, which the handler below would
                # quietly treat as a bare scalar.
                selected = list(values)[:1]

                # A write of nothing has no correct reading, so it is refused
                # here rather than sent as whatever the PDU makes of it.
                if not selected:
                    raise ModbusIllegalDataValue(values)

                values = selected[0]

        # If the user provided a single value for `values`
        except TypeError:
            # For FC15, FC16, and FC23, wrap the value in a list
            if fc in (15, 16, 23):
                values = [
                    values,
                ]

        # Read Coils (FC1)
        if fc == 1:
            pdu = RequestFactory.create_fc1_req(read_address=readAddress, read_count=readCount)

        # Read Discrete Inputs (FC2)
        elif fc == 2:
            pdu = RequestFactory.create_fc2_req(read_address=readAddress, read_count=readCount)

        # Read Holding Registers (FC3)
        elif fc == 3:
            pdu = RequestFactory.create_fc3_req(read_address=readAddress, read_count=readCount)

        # Read Input Registers (FC4)
        elif fc == 4:
            pdu = RequestFactory.create_fc4_req(read_address=readAddress, read_count=readCount)

        # Write Single Coil (FC5)
        elif fc == 5:
            pdu = RequestFactory.create_fc5_req(write_address=writeAddress, value=values)

        # Write Single Register (FC6)
        elif fc == 6:
            pdu = RequestFactory.create_fc6_req(write_address=writeAddress, value=values)

        # Read Exception Status (FC7)
        elif fc == 7:
            pdu = RequestFactory.create_fc7_req()

        # Write Multiple Coils (FC15)
        elif fc == 15:
            pdu = RequestFactory.create_fc15_req(write_address=writeAddress, write_count=writeCount, values=values)

        # Write Multiple Registers (FC16)
        elif fc == 16:
            pdu = RequestFactory.create_fc16_req(write_address=writeAddress, write_count=writeCount, values=values)

        # Mask Write Register (FC22)
        elif fc == 22:
            pdu = RequestFactory.create_fc22_req(write_address=writeAddress, and_mask=and_mask, or_mask=or_mask)

        # Read/Write Multiple Registers (FC23)
        elif fc == 23:
            pdu = RequestFactory.create_fc23_req(
                read_addr=readAddress,
                read_count=readCount,
                write_addr=writeAddress,
                write_count=writeCount,
                write_values=values,
            )

        # Read Device Identification (FC43)
        elif fc == 43:
            pdu = RequestFactory.create_fc43_req(mei_type=0x0E, mei_data=b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a")

        # Function code not recognized
        else:
            raise ModbusIllegalFunction(fc)

        # Create Modbus TCP request
        header = ModbusHeader(trans_id=self._take_trans_id(), prot_id=0, length=len(pdu) + 1, unit_id=self.unit_id)
        request = ModbusTcpRequest(header=header, pdu=pdu)

        # Log the request
        self.log.info("{0}".format(request))

        # Create a Modbus TCP stream object
        sender = ModbusTcpStream(sock=self.sock, frag_delay=self.frag_delay, frag_size=self.frag_count)

        # Send the request bytes over the socket
        sender.send(request.serialize())

    ############################################################################
    def waitResponse(self):
        """Waits for the response to the pending request and parses it.

        A response is accepted only when its transaction identifier matches the
        request that is outstanding. One that does not belongs to a request
        this client has already given up on, so it is logged, dropped, and the
        read repeated. Accepting it instead would return a reading taken for a
        different request, which is wrong rather than merely late.

        Returns:
            tuple:
                A tuple containing the parsed header and pdu instances or
                (None, None) if the peer closed the connection.

        Raises:
            ModbusNetworkError: If the peer keeps answering with identifiers
                                that match no outstanding request.
        """

        stream = ModbusTcpStream(sock=self.sock, frag_size=0)

        for _ in range(self.MAX_STALE_RESPONSES + 1):
            # Receive data from the socket
            data = stream.receive()

            # The peer closed the connection rather than answering
            if not data:
                return None, None

            response = ModbusTcpResponse.deserialize(data)
            self.log.info("{0}".format(response))

            # A client that has never sent a request has nothing to match
            # against, so whatever arrives is passed through.
            if self._pending_trans_id is None:
                return response.header, response.pdu

            if response.header.trans_id == self._pending_trans_id:
                self._pending_trans_id = None
                return response.header, response.pdu

            self.log.warning(
                "Discarding a response for transaction {0} while waiting for transaction {1}".format(
                    response.header.trans_id, self._pending_trans_id
                )
            )

        message = ("Received {0} consecutive responses that do not answer transaction {1}").format(
            self.MAX_STALE_RESPONSES + 1, self._pending_trans_id
        )
        raise ModbusNetworkError(message=message)

    ############################################################################

    def request(
        self, fc, readAddress=0, readCount=1, writeAddress=0, writeCount=1, values=(0,), and_mask=0xFFFF, or_mask=0
    ):
        """Sends a Modbus request and waits for the response.

        This methods wraps the `sendRequest` and `waitResponse` methods to send
        a request and wait for the response in a single call. It takes the same
        arguments as the `sendRequest` method and returns the response header
        and PDU instances.

        It is used to simplify the process of sending a request and waiting for
        the response in a single call and its primary use is for testing and
        debugging purposes.

        Args:
            fc (int)            : The function code of the request.
            readAddress (int)   : The starting address to read from.
            readCount (int)     : The number of registers to read.
            writeAddress (int)  : The starting address to write to.
            writeCount (int)    : The number of registers to write.
            values (list)       : The list of values to write.
            and_mask (int)      : The AND mask value.
            or_mask (int)       : The OR mask value.

        """

        self.sendRequest(
            fc=fc,
            readAddress=readAddress,
            readCount=readCount,
            writeAddress=writeAddress,
            writeCount=writeCount,
            values=values,
            and_mask=and_mask,
            or_mask=or_mask,
        )
        response = self.waitResponse()

        return response

    ############################################################################

    def send_raw(self, data=()):
        """Sends raw bytes of data over the established socket connection.

        This method provides a way to send arbitrary byte data directly through
        the client socket, bypassing the Modbus Protocol framing.

        Args:
            data (bytearray): The raw data to send.
        """

        self._require_socket().send(data)

    ############################################################################

    def recv_raw(self, buffer_size=1024):
        """Receives raw bytes of data from the socket connection.

        This method receives a specified number of bytes from the socket and
        returns them as a bytearray.

        Args:
            buffer_size (int): The number of bytes to receive.

        Returns:
            bytearray: The received raw data.
        """
        return self._require_socket().recv(buffer_size)

    ############################################################################

    def set_socket_timeout(self, timeout=None):
        """Sets the timeout value for socket operations.

        This method configures the timeout (in seconds) for socket operations
        like `recv` and `send`.

        - A timeout of `None` disables any timeout, makes the socket blocking.
        - A timeout of zero means non-blocking mode
        - A timeout greater than zero will raise a timeout exception

        Args:
            timeout (float): The timeout value in seconds.
        """
        self._require_socket().settimeout(timeout)

    ############################################################################

    def set_socket_options(self, level, optname, value):
        """Sets specific options on the underlying socket.

        This method allows fine-grained control over socket behavior by
        setting options using the provided level, option name, and value.
        Refer to socket documentation for available options and their meanings.

        The socket library is organized in layers, and each layer has its own
        set of options. The level argument specifies the layer, and the optname
        argument specifies the option name. The value argument is the value to
        set for the option.

        Args:
            level (int)     : The socket option level (socket.SOL_SOCKET).
            optname (int)   : The socket option name (socket.SO_REUSEADDR).
            value           : The value to set for the option.
        """
        self._require_socket().setsockopt(level, optname, value)

    ############################################################################

    def test(self, addr=0, count=16):
        """Quick test of the client."""

        self.connect()

        # Exchange data
        for i in range(1):
            self.request(fc=1, readAddress=addr, readCount=1)
            self.request(fc=2, readAddress=addr, readCount=1)
            self.request(fc=3, readAddress=addr, readCount=1)
            self.request(fc=4, readAddress=addr, readCount=1)
            self.request(fc=5, writeAddress=addr, writeCount=count, values=[i] * count)
            self.request(fc=6, writeAddress=addr, writeCount=count, values=[i] * count)
            self.request(fc=15, writeAddress=addr, writeCount=1, values=[i] * count)
            self.request(fc=16, writeAddress=addr, writeCount=count, values=[i] * count)
            self.request(fc=22, writeAddress=addr, and_mask=0x55, or_mask=0xAA)
            self.request(fc=23, readAddress=addr, readCount=count, writeAddress=0, writeCount=count, values=[i] * count)

        self.disconnect()


class RequestFactory(object):
    """Factory class for creating Modbus request PDUs.

    This class provides static methods for creating various Modbus request PDUs
    based on the function code and arguments. It wraps the creation of the
    request and implements the necessary logic for each function code.
    """

    @staticmethod
    def create_fc1_req(read_address, read_count):
        """Create a Modbus FC1 request PDU.

        Args:
            read_address (int)  : The starting address to read from.
            read_count (int)    : The number of registers to read.
        """

        pdu = ModbusRequestFC1(start_addr=read_address, quantity=read_count)
        return pdu

    @staticmethod
    def create_fc2_req(read_address, read_count):
        """Create a Modbus FC2 request PDU.

        Args:
            read_address (int)  : The starting address to read from.
            read_count (int)    : The number of registers to read.
        """

        pdu = ModbusRequestFC2(start_addr=read_address, quantity=read_count)
        return pdu

    @staticmethod
    def create_fc3_req(read_address, read_count):
        """Create a Modbus FC3 request PDU.

        Args:
            read_address (int)  : The starting address to read from.
            read_count (int)    : The number of registers to read.
        """

        pdu = ModbusRequestFC3(start_addr=read_address, quantity=read_count)
        return pdu

    @staticmethod
    def create_fc4_req(read_address, read_count):
        """Create a Modbus FC4 request PDU.

        Args:
            read_address (int)  : The starting address to read from.
            read_count (int)    : The number of registers to read.
        """

        pdu = ModbusRequestFC4(start_addr=read_address, quantity=read_count)
        return pdu

    @staticmethod
    def create_fc5_req(write_address, value):
        """Create a Modbus FC5 request PDU.

        Args:
            write_address (int) : The address to write to.
            value (int)         : The value to write.
        """

        pdu = ModbusRequestFC5(output_address=write_address, output_value=value)
        return pdu

    @staticmethod
    def create_fc6_req(write_address, value):
        """Create a Modbus FC6 request PDU.

        Args:
            write_address (int) : The address to write to.
            value (int)         : The value to write.
        """

        pdu = ModbusRequestFC6(output_address=write_address, output_value=value)
        return pdu

    @staticmethod
    def create_fc7_req():
        """Create a Modbus FC7 request PDU."""
        pdu = ModbusRequestFC7()
        return pdu

    @staticmethod
    def create_fc15_req(write_address, write_count, values):
        """Create a Modbus FC15 request PDU.

        Args:
            write_address (int) : The starting address to write to.
            write_count (int)   : The number of coils to write.
            values (list)       : The list of coil values to write.
        """

        # Calculate the number of bytes depending on the number of coil values
        if write_count % 8 == 0:
            byte_count = int(write_count // 8)
        else:
            byte_count = int((write_count // 8) + 1)

        # Construct the output values and take only the required number of bytes
        output_values = []
        for i in range(byte_count):
            output_values.append(values[i])

        # Create the Modbus FC15 request PDU
        pdu = ModbusRequestFC15(
            start_addr=write_address, quantity=write_count, byte_count=byte_count, values=output_values
        )

        return pdu

    @staticmethod
    def create_fc16_req(write_address, write_count, values):
        """Create a Modbus FC16 request PDU.

        Args:
            write_address (int) : The starting address to write to.
            write_count (int)   : The number of registers to write.
            values (list)       : The list of register values to write.
        """

        byte_count = 2 * write_count

        pdu = ModbusRequestFC16(
            start_addr=write_address,
            quantity=write_count,
            byte_count=byte_count,
            values=values,
        )

        return pdu

    @staticmethod
    def create_fc22_req(write_address, and_mask, or_mask):
        """Create a Modbus FC22 request PDU.

        Args:
            write_address (int) : The address to write to.
            and_mask (int)      : The AND mask value.
            or_mask (int)       : The OR mask value.
        """

        pdu = ModbusRequestFC22(ref_addr=write_address, and_mask=and_mask, or_mask=or_mask)

        return pdu

    @staticmethod
    def create_fc23_req(read_addr, read_count, write_addr, write_count, write_values):
        """Create a Modbus FC23 request PDU.

        Args:
            read_addr (int)     : The starting address to read from.
            read_count (int)    : The number of registers to read.
            write_addr (int)    : The starting address to write to.
            write_count (int)   : The number of registers to write.
            write_values (list) : The list of register values to write.
        """

        byte_count = 2 * write_count

        pdu = ModbusRequestFC23(
            read_start_addr=read_addr,
            read_quantity=read_count,
            write_start_addr=write_addr,
            write_quantity=write_count,
            write_byte_count=byte_count,
            write_values=write_values,
        )

        return pdu

    @staticmethod
    def create_fc43_req(mei_type, mei_data):
        """Create a Modbus FC43 request PDU.

        Args:
            mei_type (int)  : The MEI type.
            mei_data (bytes): The MEI data.
        """

        pdu = ModbusRequestFC43(mei_type=mei_type, mei_data=mei_data)
        return pdu


def run_client():
    logger = Logger(name="ModbusClientSimulator")
    client = ModbusClientSimulator(
        log=logger,
        host=b"localhost",
        port=502,
        # frag_count=2,
        secure=False,
    )
    client.test()


if __name__ == "__main__":
    # Inside the guard, never at import. Reconfiguring stdout mutates a stream
    # the importing application owns, and this is a library module first; run
    # as a script it is the entry point and the choice is its own to make.
    #
    # The attribute is checked rather than assumed. Only a text stream over a
    # buffer carries reconfigure, and sys.stdout is whatever the host put
    # there -- a capture object under a test runner, and None under a
    # windowed interpreter with no console attached.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    run_client()
