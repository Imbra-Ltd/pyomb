# encoding: utf-8

"""pyomb -- Open Modbus protocol library.

Serialization and deserialization of Modbus TCP and RTU packets, fragmented
stream transport, and a scriptable server/client pair for testing Modbus
implementations.

The names re-exported here are the supported public API. Function-code packet
classes (ModbusRequestFC1, ModbusResponseFC3, ...) are numerous and remain
available from pyomb.packets.

The simulators are deliberately not imported here: they pull in socket, ssl,
and threading, which a caller who only needs the codec should not pay for.
Import them from pyomb.omb_client and pyomb.omb_server.
"""

from .errors import ModbusAcknowledge
from .errors import ModbusBaseError
from .errors import ModbusGatewayPathUnavailable
from .errors import ModbusGatewayTargetDeviceFailedToRespond
from .errors import ModbusIllegalDataAddress
from .errors import ModbusIllegalDataValue
from .errors import ModbusIllegalFunction
from .errors import ModbusMemoryParityError
from .errors import ModbusNetworkError
from .errors import ModbusPacketError
from .errors import ModbusProtocolError
from .errors import ModbusSlaveDeviceBusy
from .errors import ModbusSlaveDeviceFailure
from .logger import Logger
from .packets import ModbusError
from .packets import ModbusHeader
from .packets import ModbusPdu
from .packets import ModbusPduParser
from .packets import ModbusRtuRequest
from .packets import ModbusRtuResponse
from .packets import ModbusTcpPacket
from .packets import ModbusTcpRequest
from .packets import ModbusTcpResponse
from .stream import ModbusFragmenter
from .stream import ModbusTcpReceiver
from .stream import ModbusTcpSender
from .stream import ModbusTcpStream

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Packets
    "ModbusHeader",
    "ModbusPdu",
    "ModbusPduParser",
    "ModbusError",
    "ModbusTcpPacket",
    "ModbusTcpRequest",
    "ModbusTcpResponse",
    "ModbusRtuRequest",
    "ModbusRtuResponse",
    # Stream
    "ModbusTcpStream",
    "ModbusTcpSender",
    "ModbusTcpReceiver",
    "ModbusFragmenter",
    # Errors
    "ModbusBaseError",
    "ModbusProtocolError",
    "ModbusNetworkError",
    "ModbusPacketError",
    "ModbusIllegalFunction",
    "ModbusIllegalDataAddress",
    "ModbusIllegalDataValue",
    "ModbusSlaveDeviceFailure",
    "ModbusAcknowledge",
    "ModbusSlaveDeviceBusy",
    "ModbusMemoryParityError",
    "ModbusGatewayPathUnavailable",
    "ModbusGatewayTargetDeviceFailedToRespond",
    # Logging
    "Logger",
]
