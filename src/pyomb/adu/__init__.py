"""Modbus Application Data Unit classes.

The envelope a transport puts around a PDU, one module per envelope kind:
the MBAP header and the three TCP frame classes in tcp.py, the CRC-16
checksum and the three RTU frame classes in rtu.py. Neither module imports
a socket -- the bytes of a complete frame are handed in, never read from a
stream.
"""

from pyomb.adu.rtu import (
    CRC_FMT,
    CRC_SIZE,
    ModbusRtuPacket,
    ModbusRtuRequest,
    ModbusRtuResponse,
    calc_crc16,
    validate_crc,
)
from pyomb.adu.tcp import (
    ModbusHeader,
    ModbusTcpPacket,
    ModbusTcpRequest,
    ModbusTcpResponse,
    validate_mbap_length,
)

__all__ = [
    "CRC_FMT",
    "CRC_SIZE",
    "ModbusHeader",
    "ModbusRtuPacket",
    "ModbusRtuRequest",
    "ModbusRtuResponse",
    "ModbusTcpPacket",
    "ModbusTcpRequest",
    "ModbusTcpResponse",
    "calc_crc16",
    "validate_crc",
    "validate_mbap_length",
]
