# Open Modbus Protocol

## 1. Definitions

    ADU             : Application data unit (the complete message that is sent on the bus)
    PDU             : Protocol data unit (contains the function code and data)
    HEADER          : Contains transaction-Id, Protocol-Id, Length, Unit-Id (only Modbus TCP)
    ADDR            : Node Address (only Modbus RTU)
    CRC             : The 16-bit Cyclic Redundancy Check (only Modbus RTU)
    FC              : Function Code that defines the action to be taken
    DATA            : The data field of the PDU with its own format
    CLIENT          : The device that initiates the request (former master)
    SERVER          : The device that responds to the request (former slave)
    POINT-TO-POINT  : Only two devices connected to the same bus
    MULTI-DROP      : Multiple devices connected to the same bus

## 2. Physical Layer

The communication is point-to-point or multi-drop. The master device sends requests and the
slave device responds. Data Encoding on Bus is Big-Endian (MSB first).

    Modbus RTU  : RS-232 (p2p), RS-422 (multi-drop), RS-485 (multi-point)
    Modbus TCP  : Ethernet

The wiring of a serial line determines whether the protocol works at all. The faults that belong
to this layer are described in 7.4 to 7.13.

## 3. Frame Format

The frame format is different for Modbus RTU and Modbus TCP. The Modbus RTU frame is used for
serial communication and the Modbus TCP frame is used for Ethernet communication. Both frames
contain the same PDU and differ only in the fields around it.

### 3.1. Protocol Data Unit

The PDU is common to both transports. It contains the function code and the data field.

    +----------------------+
    | Function Code        |  1 byte
    +----------------------+
    | Data                 |  0 .. 252 bytes
    +----------------------+
                              max 253 bytes

The maximum size of the PDU is 253 bytes. It is derived from the serial ADU, which is limited to
256 bytes, minus one byte for the address and two bytes for the checksum. Modbus TCP uses the
same limit, so that a gateway can forward a message between the two transports without changing
its size.

### 3.2. Modbus RTU

The Modbus RTU ADU contains the address, the PDU and the checksum.

    +----------------------+
    | Address              |  1 byte
    +----------------------+
    | Function Code        |  1 byte
    +----------------------+
    | Data                 |  0 .. 252 bytes
    +----------------------+
    | CRC-16               |  2 bytes
    +----------------------+
                              max 256 bytes

    Address : From 1 to 247 (0 for broadcasting, from 248 to 255 reserved)
    CRC-16  : CRC-16/MODBUS over the address and the PDU, low byte first

The frame is delimited by an idle line and not by a length field. The line is idle for at least
3.5 character times before and after the frame and a gap inside the frame is not longer than 1.5
character times. A receiver that detects a longer gap treats the frame as complete. The CRC is
used to verify that the frame is received without corruption.

An example for a request that reads 2 holding registers from address 0 of server 17:

    11 03 00 00 00 02 C6 9B

    Address : 11
    PDU     : 03 00 00 00 02
    CRC-16  : C6 9B

### 3.3. Modbus TCP

The Modbus TCP ADU contains the MBAP header and the PDU. The header is 7 bytes long and replaces
the address and the checksum of the serial frame. A checksum is not required, because TCP
verifies the integrity of the data.

    +----------------------+
    | Transaction Id       |  2 bytes
    +----------------------+
    | Protocol Id          |  2 bytes
    +----------------------+
    | Length               |  2 bytes
    +----------------------+
    | Unit Id              |  1 byte
    +----------------------+
    | Function Code        |  1 byte
    +----------------------+
    | Data                 |  0 .. 252 bytes
    +----------------------+
                              max 260 bytes

    Transaction Id : Message identifier for each request and response
    Protocol Id    : Zero for the Modbus TCP protocol
    Length         : Number of following bytes, including the unit id
    Unit Id        : Node address in Modbus RTU or other serial networks

The length field contains the number of bytes that follow it. These are the unit id and the PDU.
The transaction id, the protocol id and the length field itself are not counted and occupy the
first 6 bytes of the frame. The total size of the frame is therefore 6 + Length. See 7.2.

An example for the same request over TCP to unit 17 with the transaction id 1:

    00 01 00 00 00 06 11 03 00 00 00 02

    Transaction Id : 00 01
    Protocol Id    : 00 00
    Length         : 00 06 (the unit id and the 5 bytes of the PDU that follow)
    Unit Id        : 11
    PDU            : 03 00 00 00 02

The frame is 12 bytes long, which is 6 + 6.

## 4. Data Model

### 4.1. Discrete Input (Status)

The discrete input is a single bit that can be read. Each bit has its own address. An example for
a discrete input is a sensor that can be on or off.

### 4.2. Discrete Output (Coils)

The discrete output is a single bit that can be read or written. Each bit has its own address.
An example for a discrete output is a relay that can be turned on or off.



### 4.3. Analog Inputs (Input Register)

The analog input is a 16-bit value that can be read. Each value has its own address. An example
for an analog input is a temperature sensor that returns the temperature in degrees Celsius.

### 4.4. Analog Output (Holding Register)

The analog output is a 16-bit value that can be read or written. Each value has its own address.
An example for an analog output is a position controller that can be set to a specific position.


## 5. Addressing Model

### 5.1. Overview

* The protocol reserves 2 bytes for the register/coil address in the PDU.
* The addressing on the bus starts from 0 and the logical addressing of the data starts from 1.
* The mapping between logical and physical addresses is vendor-specific.
* The conversion between the two is described in 5.4.


### 5.2. Modbus Addressing

The official Modbus addressing model is dividing the data into groups and each group has its own
range of addresses. The protocol doesn't define how the data is stored in the device.

                                            MIN  :  MAX
    Discrete Input (Status)             ->     1 : 65536  
    Discrete Output (Coils)             ->     1 : 65536
    Analog Inputs (Input Register)      ->     1 : 65536
    Analog Output (Holding Register)    ->     1 : 65536

These are the item numbers of the data model and they start from 1. The same items are addressed
from 0 to 65535 in the protocol frame. The item 1 is transmitted as the address 0. See 5.4.

When the data is overlapping we can access the same data using different function codes. For
example, we can read the same data as discrete inputs or analog inputs. The data model is
vendor-specific and the mapping between logical and physical addresses is not standardized.

### 5.3. Modicon Addressing

The Modicon addressing model is dividing the data into groups and each group has its own range
of addresses.

                                           GROUP    MIN   :   MAX
    Discrete Output (Coils)             -> 0        00001 : 09999
    Discrete Input (Status)             -> 1        10001 : 19999
    Analog Inputs (Input Register)      -> 3        30001 : 39999
    Analog Output (Holding Register)    -> 4        40001 : 49999

Each group starts from 1 and not from 0. The register 40000 does not exist. The first holding
register is 40001 and it is transmitted as the PDU address 0.

The function code is used to select the group and the address within the group. In this way it
is guaranteed that the address spaces of the groups do not overlap.

The limit of 9999 items per group is a property of the 5-digit notation and not of the protocol.
The PDU contains a 16-bit address and can reach 65536 items. The 6-digit notation
(400001 : 465536) covers the complete range.

### 5.4. Logical vs PDU Address

Both models number the items from 1 and the PDU numbers them from 0. The conversion between them
is a subtraction of 1.

    logical (Modicon)      PDU address       reached by
    -----------------      -----------       ----------
    40001                  0x0000            FC 3, offset 0
    40002                  0x0001            FC 3, offset 1
    00001                  0x0000            FC 1, offset 0
    30001                  0x0000            FC 4, offset 0

The group digit is part of the notation and is not transmitted in the frame. It determines the
function code and the remaining digits minus 1 are the address. The holding register 40001 and
the coil 00001 are both the address 0 in the frame and are distinguished by the function code.

The client software is supposed to subtract 1 when transmitting and to add 1 when displaying.
Some applications differ in this behavior.

 1. Required logical address = 1
 2. Master doesn't conform to the specification and sends 1 without conversion
 3. According to the specification PDU address corresponds to logical address 2
 4. Slave conforms to the specification and sends register 2 instead of 1

The result is an offset of one register for every value that is read or written. See 7.1.

### 5.5. Vendor Notation

Not all vendors use the models above. Some publish register maps that are addressed from 0, in
the same way as the protocol frame. Others number the items from 1 without a group prefix. The
number alone does not determine the notation.

The first holding register is written in five different ways:

    Notation                          Written as    Conversion to the frame address
    --------                          ----------    -------------------------------
    5-digit Modicon                   40001         subtract 40001
    6-digit Modicon                   400001        subtract 400001
    Modicon with an explicit group    4x0001        subtract 1 from the digits after the x
    No prefix, numbered from 1        1             subtract 1
    No prefix, numbered from 0        0             none

All five refer to the same register, which is the address 0 in the frame. The other groups are
converted in the same way with their own first reference, for example 00001 for the coils.

The notation is recognised by the first entry of the map. A map that starts at 0 is numbered
from 0 and a map that starts at 1, 40001 or 4x0001 is numbered from 1. A reference above 65535
is always a prefixed notation, because the address in the frame is limited to 16 bits.

If the map does not state the base, a register with a known value is read and it is checked
whether the value is returned from the neighbouring address.

The conversion is applied only once. An address that is already numbered from 0 is transmitted
unchanged.

This library uses PDU addresses. The parameter start_addr is transmitted without an offset and
start_addr=0 is the first item of a group.

## 6. Function Codes

Тhe function code is used to determine the action to be taken by the server. The response
contains the same function code as the request in case of success. If an exception occurs, the
server copies the function code and sets the MSB bit to 1 (adds 0x80). The data field contains
the exception.

### 6.1. General Definitions

    # Zero is an invalid function code
    # The valid range is from 1 to 127
    # The MSB bit is set to 1 for exceptions, e.g 0x81 is an exception for function code 1
    # The data field might contain sub-function codes and additional information.

### 6.2. Behavior on Exceptions

    # The server copies the function code and sets the MSB bit to 1 (adds 0x80)
    # The data field contains the exception

### 6.3. Function Code Groups

    # PUBLIC      : [1..61], [73..99], [111...127]
    # CUSTOM      : [62 ..72], [100..110]
    # RESERVED    : [128..255]

### 6.4. Bit Access Functions

#### 6.4.1. FC 01 (Read Discrete Outputs)

**Request**

    ARGS :
        START_ADDR      (2 Bytes)
        QUANTITY        (2 Bytes)

**Response**

    ARGS :
        BYTE_COUNT      (1 Byte)
        OUTPUT_VALUES   (N Bytes)

#### 6.4.2. FC 02 (Read Discrete Inputs)

**Request**

    ARGS :
        START_ADDR      (2 Bytes)
        QUANTITY        (2 Bytes)


**Response**

    ARGS :
        BYTE_COUNT      (1 Byte)
        INPUT_VALUES    (N Bytes)

#### 6.4.3. FC 05 (Write Single Discrete Output)

**Request**

    ARGS :
        OUTPUT_ADDR     (2 Bytes)
        OUTPUT_VALUE    (2 Bytes)

**Response**

    ARGS :
        OUTPUT_ADDR     (2 Bytes)
        OUTPUT_VALUE    (2 Bytes)

#### 6.4.4. FC 15 (Write Multiple Discrete Outputs)

**Request**

    ARGS :
        START_ADDR      (2 Bytes)
        QUANTITY        (2 Bytes)
        BYTE_COUNT      (1 Byte)
        OUTPUT_VALUES   (N Bytes)

**Response**

    ARGS :
        START_ADDR      (2 Bytes)
        QUANTITY        (2 Bytes)

### 6.5. Word Access Functions

#### 6.5.1. FC 03 (Read Analog Inputs)

**Request**

    ARGS :
        START_ADDR      (2 Bytes)
        QUANTITY        (2 Bytes)

**Response**

    ARGS :
        BYTE_COUNT      (1 Byte)
        INPUT_VALUES    (N Bytes)

#### 6.5.2. FC 04 (Read Analog Outputs)

**Request**

    ARGS :
        START_ADDR      (2 Bytes)
        QUANTITY        (2 Bytes)

**Response**

    ARGS :
        BYTE_COUNT      (1 Byte)
        OUTPUT_VALUES   (N Bytes)

#### 6.5.3. FC 06 (Write Single Analog Output)

**Request**

    ARGS :
        OUTPUT_ADDR     (2 Bytes)
        OUTPUT_VALUE    (2 Bytes)


**Response**

    ARGS :
        OUTPUT_ADDR     (2 Bytes)
        OUTPUT_VALUE    (2 Bytes)


#### 6.5.4. FC 16 (Write Multiple Analog Outputs)

**Request**

    ARGS :
        START_ADDR      (2 Bytes)
        QUANTITY        (2 Bytes)
        BYTE_COUNT      (1 Byte)
        OUTPUT_VALUES   (N Bytes)

**Response**

    ARGS :
        START_ADDR      (2 Bytes)
        QUANTITY        (2 Bytes)


#### 6.5.5. FC 22 (Mask Write Register)

**Request**

    ARGS :
        REFERENCE_ADDR  (2 Bytes)
        AND_MASK        (2 Bytes)
        OR_MASK         (2 Bytes)

**Response**

    ARGS :
        REFERENCE_ADDR  (2 Bytes)
        AND_MASK        (2 Bytes)
        OR_MASK         (2 Bytes)


#### 6.5.5. FC 23 (Read Write Multiple Registers)

**Request**

    ARGS :
        READ_START_ADDR     (2 Bytes)
        READ_QUANTITY       (2 Bytes)
        WRITE_START_ADDR    (2 Bytes)
        WRITE_QUANTITY      (2 Bytes)
        BYTE_COUNT          (1 Byte)
        WRITE_VALUES        (N Bytes)

**Response**

    ARGS :
        READ_BYTE_COUNT     (1 Byte)
        READ_VALUES         (N Bytes)


#### 6.5.6. FC 24 (Read FIFO Queue)

**Request**

    ARGS :
        FIFO_ADDR       (2 Bytes)
        FIFO_COUNT      (2 Bytes)


**Response**

    ARGS :
        BYTE_COUNT      (1 Byte)
        FIFO_VALUES     (N Bytes)

### 6.6. Diagnostic

#### 6.6.1. FC 07 (Read Exception Status)

**Request**

    ARGS :
        NONE

**Response**

    ARGS :
        EXCEPTION_STATUS (1 Byte)

#### 6.6.2. FC 08 (Diagnostics)

**Request**

    ARGS :
        SUB-FUNCTION    (2 Bytes)
        DATA            (N Bytes)


**Response**

    ARGS :
        SUB-FUNCTION    (2 Bytes)
        DATA            (N Bytes)


#### 6.6.3. FC 11 (Get Comm Event Counter)

**Request**

    ARGS :
        NONE

**Response**

    ARGS :
        STATUS          (2 Bytes)
        EVENT_COUNT     (2 Bytes)  

#### 6.6.4. FC 12 (Get Comm Event Log)

**Request**

    ARGS :
        NONE

**Response**

    ARGS :
        STATUS          (2 Bytes)
        EVENT_COUNT     (2 Bytes)
        MESSAGE_COUNT   (2 Bytes)
        EVENTS          (N Bytes)


#### 6.6.5. FC 17 (Report Slave ID)

**Request**

    ARGS :
        NONE

**Response**

    ARGS :
        BYTE_COUNT      (1 Byte)
        SLAVE_ID        (1 Byte)
        RUN_INDICATOR   (1 Byte)
        ADDITIONAL      (N Bytes)


#### 6.6.6. FC 43 (Device Identification)

**Request**

    ARGS :
        OBJECT_ID       (2 Bytes)
        OBJECT_TYPE     (1 Byte)
        OBJECT_INSTANCE (1 Byte)
        OBJECT_COUNT    (1 Byte)


**Response**

    ARGS :
        OBJECT_ID       (2 Bytes)
        OBJECT_TYPE     (1 Byte)
        OBJECT_INSTANCE (1 Byte)
        OBJECT_COUNT    (1 Byte)
        OBJECT_DATA     (N Bytes)

### 6.7. File Access

#### 6.7.1. FC 20 (Read File Record)

**Request**

    ARGS :
        FILE_NUMBER     (2 Bytes)
        RECORD_NUMBER   (2 Bytes)
        RECORD_LENGTH   (2 Bytes)

**Response**

    ARGS :
        BYTE_COUNT      (1 Byte)
        RECORDS         (N Bytes)


#### 6.7.2. FC 21 (Write File Record)

**Request**

    ARGS :
        FILE_NUMBER     (2 Bytes)
        RECORD_NUMBER   (2 Bytes)
        RECORD_LENGTH   (2 Bytes)
        RECORDS         (N Bytes)


**Response**

    ARGS :
        FILE_NUMBER     (2 Bytes)
        RECORD_NUMBER   (2 Bytes)
        RECORD_LENGTH   (2 Bytes)
        RECORDS         (N Bytes)

## 7. Troubleshooting

### 7.1. Off-by-One Register Addressing

**Symptom**

Every value that is read or written is offset by one register. A read of 40001 returns the value
of 40002.

**Root cause**

The logical address is transmitted without the subtraction of 1, or the subtraction is applied
twice. The logical address 1 is the address 0 in the frame. Some applications differ in this
behavior, so the cause can be on either side.

**Mitigation**

Determine the convention of the other side before the own conversion is changed. See 5.4 for the
conversion and 5.5 for the notations that are used by vendors.

### 7.2. MBAP Length Off by One

**Symptom**

The receiver waits for a byte that is not sent, or reads one byte too many and treats the first
byte of the next frame as part of the current one. On a fast connection the error is not always
visible, because a socket read returns the available bytes and does not wait for the requested
count.

**Root cause**

The length field contains the number of bytes that follow it, and the unit id is one of them.
The unit id is also the last byte of the 7-byte header. A receiver that reads the header and
then reads Length bytes after it counts the unit id twice.

**Mitigation**

Read Length - 1 bytes after the header. See 3.3 for the position of the field.

    total size of the frame     = 6 + Length
    PDU bytes after the header  = Length - 1

### 7.3. RTU Checksum Rejected

**Symptom**

A serial server does not respond to any request, while the same PDU is accepted over TCP.

**Root cause**

The CRC computed by the server does not match the CRC in the frame. This applies to a CRC that
is rejected on every frame, which is an implementation fault. A CRC that is rejected
intermittently is a signal quality fault and is covered in 7.4.

**Mitigation**

Check the following in this order:

 1. The algorithm is CRC-16/MODBUS with an initial value of 0xFFFF and a reversed polynomial of
    0xA001. Other CRC-16 variants produce a different value for the same bytes.
 2. The CRC covers the address byte and the PDU, and not the PDU alone.
 3. The CRC is transmitted with the low byte first. A frame that contains the two bytes in the
    opposite order contains a correct checksum that is rejected.

Modbus TCP does not contain a checksum. A PDU that is accepted over TCP does not verify the CRC
of the serial frame.

### 7.4. Serial Line Faults

Most faults on a serial line are in the wiring and not in the protocol. The symptom narrows down
the cause before any frame is inspected.

| Symptom                                 | Look at                                 | See            |
| --------------------------------------- | --------------------------------------- | -------------- |
| No response from any device             | Reversed conductors, serial parameters  | 7.6, 7.13      |
| No response from one device only        | Its address, its wiring, its parameters | 7.12, 7.13     |
| Occasional CRC errors without a pattern | Loose terminals, missing common, cable  | 7.5, 7.7, 7.8  |
| Errors increase with baud rate or cable | Termination, topology, cable            | 7.8, 7.9, 7.10 |
| Errors while no device is transmitting  | Biasing of the idle line                | 7.11           |
| Garbled responses to every request      | Two devices with the same address       | 7.12           |

A device that answers some requests and misses others has a different fault from a device that
never answers. The first is a connection or a signal quality problem and the second is usually a
configuration or polarity problem.

### 7.5. Loose Connections

**Symptom**

CRC errors that appear in bursts and then stop, without a pattern in the data. The error rate
changes when the cable is moved, and follows vibration, temperature and the time since the
terminal was last tightened. Retries succeed, which hides the fault from an application that
does not count them.

**Root cause**

A loose screw terminal. It does not silence the device. Enough frames still arrive for the link
to look functional and the rest are lost or corrupted, so the result is an error rate rather
than a failure. Stranded wire that is clamped directly under a screw spreads over time and
loosens.

**Mitigation**

Retighten every terminal on the segment, including those in junction boxes and on devices that
are not suspected, because the fault is on the shared line and not on the device that reports
the error. Check a terminal by pulling each conductor and not by inspection. Fit ferrules on
stranded wire.

### 7.6. Reversed Signal Conductors

**Symptom**

No device answers, although the line is otherwise intact.

**Root cause**

The two signal conductors are swapped. The naming is not consistent between manufacturers, so a
connection that is labelled correctly can still be reversed.

**Mitigation**

Swap the two conductors on one device. This is a valid test and cannot damage the transceiver.

### 7.7. Missing Common Conductor

**Symptom**

The link works on a bench and fails in an installation where the devices are supplied from
different points.

**Root cause**

A common conductor is required in addition to the two signal conductors. RS-485 receivers
tolerate a common-mode voltage of -7 V to +12 V. Without a common reference the difference in
ground potential between the devices is unconstrained and can exceed that range.

**Mitigation**

Connect a common conductor to every device on the segment.

### 7.8. Unsuitable Cable

**Symptom**

Errors that increase with the length of the cable and in the presence of nearby equipment.

**Root cause**

Flat cable and untwisted conductors couple noise into the pair. A shield that is grounded at
both ends carries current between the two grounds.

**Mitigation**

Use a twisted pair with a characteristic impedance near 120 ohms. Connect the shield to ground
at one end only.

### 7.9. Missing or Excess Termination

**Symptom**

Errors that increase with the length of the cable and with the baud rate. The line works at 9600
baud and fails at 115200 baud.

**Root cause**

A missing terminator produces reflections. A terminator on every device loads the line until the
signal is too weak to be received.

**Mitigation**

Fit a terminator at both ends of the trunk, matching the impedance of the cable and typically
120 ohms. Two terminators are fitted in total, not one per device. A link that is repaired by
lowering the baud rate has a termination or cable fault that has been hidden rather than fixed.

### 7.10. Star Topology and Stubs

**Symptom**

Reflections that remain after the trunk is terminated correctly.

**Root cause**

The devices are not connected in a daisy chain. A star topology and long stubs from the trunk
produce reflections that termination at the ends of the trunk does not remove.

**Mitigation**

Connect the devices in a daisy chain and keep any stub as short as possible.

### 7.11. Missing Bias

**Symptom**

Framing or CRC errors that appear between transactions rather than during them.

**Root cause**

The idle line floats when no device is transmitting, and noise on the floating line is received
as start bits.

**Mitigation**

Hold the idle line in a defined state with a pull-up on one conductor and a pull-down on the
other. One set of bias resistors is fitted per segment.

### 7.12. Duplicate Slave Address

**Symptom**

Garbled responses to every request that is addressed to that device.

**Root cause**

Two devices with the same address answer the same request at the same time and both drive the
line.

**Mitigation**

Remove power from one of the two. If the requests are then answered normally, the address is
duplicated. Assign a unique address to every device on the segment.

The address 0 is the broadcast address. A request that is sent to it is executed by every device
and answered by none, so the absence of a response is expected and is not a fault.

### 7.13. Serial Parameter Mismatch

**Symptom**

One device does not answer, while the others on the same segment are unaffected.

**Root cause**

The baud rate, the parity or the number of stop bits differ from the rest of the segment, so the
device cannot decode a request that is addressed to it. A receiver does not drive the line, so a
device that only listens does not disturb the others. It disturbs them when it transmits, which
happens when the baud rate is correct and only the parity or the stop bits differ, because the
address is then decoded correctly and the device answers with the wrong framing.

**Mitigation**

Set the same parameters on every device on the segment. A Modbus RTU character is 11 bits: one
start bit, 8 data bits, one parity bit and one stop bit. When no parity is used, two stop bits
are sent instead, so the character remains 11 bits.

### 7.14. Network Faults

Modbus TCP has no serial parameters and no shared conductor, so the faults of a serial line do
not apply. A switched network is not a shared medium and the traffic of one device does not
corrupt the frames of another. The faults move to the connection and to the network itself.

| Symptom                                    | Look at                                          | See  |
| ------------------------------------------ | ------------------------------------------------ | ---- |
| Connection refused immediately             | Device off, service not started, wrong port      | 7.15 |
| Connection attempt times out               | Address, routing, a firewall discarding silently | 7.15 |
| First client works, later ones refused     | The connection limit of the server               | 7.15 |
| Connect fails after hours of polling       | Sockets not released, exhausted local ports      | 7.16 |
| Requests time out but the socket is open   | A half-open connection, an idle timeout          | 7.17 |
| Works on a local network, fails remotely   | Frames read without using the length field       | 7.18 |
| Correct answers, tens of milliseconds late | Nagle and delayed acknowledgement                | 7.19 |

TCP verifies and retransmits the data it carries, so a marginal link does not deliver corrupted
frames to the application. It delivers them late instead. The errors that are visible as CRC
failures on a serial line are visible as timeouts and delay here, and they are diagnosed from
the counters of the switch port rather than from the Modbus error counters.

### 7.15. Connection Not Established

**Symptom**

The connection is refused immediately, or the attempt times out, or the first client connects
and later ones are refused.

**Root cause**

A refusal means the address is reachable and nothing is listening on the port. The device is
switched off, the Modbus service is not started, or the port is wrong. A timeout means the
request is not answered at all: the address is wrong, no route exists, or a firewall discards
the request without sending a rejection. A server accepts a limited number of connections at the
same time, often fewer than ten, and refuses or drops the rest.

**Mitigation**

Distinguish the two by the response to the connection attempt, because they are different
faults. A plain connection uses port 502 and a secure connection uses port 802. Keep one
connection open instead of opening one for every poll, because a single client otherwise reaches
the connection limit on its own.

When the transport is secure, the TCP connection is established first and the handshake fails
afterwards. A failure that occurs after the connection is accepted is a certificate, a chain, a
hostname or a cipher problem and not a connectivity problem.

### 7.16. Sockets Not Released

**Symptom**

A connection fails after hours of polling, although the device and the network are working. A
server that is restarted cannot bind to its port.

**Root cause**

The side that closes a connection first keeps it for twice the maximum segment lifetime, which
is typically between one and four minutes. This state is required so that delayed segments from
the closed connection are not delivered to a new one, and it is not a leak. A client that opens
and closes a connection for every poll accumulates these connections until the local port range
is exhausted.

**Mitigation**

Open the connection once and send all requests over it. Modbus TCP is designed for a connection
that stays open.

For the server, the SO_REUSEADDR option on the listening socket permits the bind while previous
connections are still held. The behaviour depends on the operating system and the fault appears
on Linux and macOS but not on Windows.

The SO_LINGER option with a linger time of zero is not a remedy. It makes a close send a reset
instead of an orderly shutdown, which removes the waiting state but also discards data that has
not been transmitted, so the last response can be lost and the peer reports a connection reset.
It is an abort.

### 7.17. Stale and Half-Open Connections

**Symptom**

The client reports that it is connected, every request times out, and the state persists until
the application closes the connection and opens a new one.

**Root cause**

A device that loses power, and a cable that is disconnected, do not close the connections that
were open, and the other side is not informed. A network address translator or a stateful
firewall discards a connection that has been idle for a few minutes and also does not inform
either side, which produces the same symptom after a pause in the polling.

**Mitigation**

Apply a timeout in the application and reconnect when a request is not answered. TCP keepalive
detects both cases, but the default interval is two hours on most systems, so it is shortened
before it is useful.

### 7.18. Partial and Combined Frames

**Symptom**

The link works on a local network and fails across a router, a virtual private network or a
congested link. The symptom follows the network path and the load, and not a particular device.

**Root cause**

TCP is a stream of bytes and not a sequence of messages. A read returns the bytes that have
arrived, which can be a part of one ADU, exactly one ADU, or several ADUs together. The boundary
between frames is not preserved by the transport. A receiver that performs a single read and
treats the result as a complete frame works only while a frame arrives in one segment.

**Mitigation**

Read the 7-byte header first, take the length field, and then read exactly Length - 1 further
bytes, repeating the read until they have all arrived. See 3.3 and 7.2.

### 7.19. Unexpected Latency

**Symptom**

Requests are answered correctly but late, and the delay is a multiple of tens of milliseconds
rather than a value that varies with the size of the response.

**Root cause**

A Modbus frame is small. Nagle's algorithm holds a small segment until the previous one is
acknowledged, and the delayed acknowledgement of the receiver waits for data to send before it
acknowledges. The two together add a fixed delay to every exchange.

**Mitigation**

Set the TCP_NODELAY option, which disables Nagle's algorithm. Distinguish the delay from the
processing time of the device by measuring on a direct connection, where the network contributes
nothing.
