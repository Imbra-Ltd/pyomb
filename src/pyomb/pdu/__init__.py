"""Modbus Protocol Data Unit classes.

The message itself, independent of the transport that delivers it. Grouped
the way the Modbus Application Protocol groups its function codes: bit
access, register access, diagnostics, and the encapsulated interface
transport, plus one module for the shared parts every group depends on.

A custom PDU subclasses ModbusPdu and registers with ModbusPduParser,
giving its format string, function code and PDU identifier. See
docs/PLAYBOOK.md for the identifier ranges.
"""

from pyomb.pdu.bits import (
    ModbusRequestFC1,
    ModbusRequestFC2,
    ModbusRequestFC5,
    ModbusRequestFC15,
    ModbusResponseFC1,
    ModbusResponseFC2,
    ModbusResponseFC5,
    ModbusResponseFC15,
)
from pyomb.pdu.common import (
    ModbusError,
    ModbusPacketAbc,
    ModbusPdu,
    ModbusPduParser,
    ModbusPduParserAbc,
    ModbusViolation,
)
from pyomb.pdu.diagnostics import (
    ModbusRequestFC7,
    ModbusRequestFC8,
    ModbusResponseFC7,
    ModbusResponseFC8,
)
from pyomb.pdu.encapsulated import ModbusRequestFC43, ModbusResponseFC43
from pyomb.pdu.registers import (
    ModbusRequestFC3,
    ModbusRequestFC4,
    ModbusRequestFC6,
    ModbusRequestFC16,
    ModbusRequestFC22,
    ModbusRequestFC23,
    ModbusResponseFC3,
    ModbusResponseFC4,
    ModbusResponseFC6,
    ModbusResponseFC16,
    ModbusResponseFC22,
    ModbusResponseFC23,
)

__all__ = [
    "ModbusError",
    "ModbusPacketAbc",
    "ModbusPdu",
    "ModbusPduParser",
    "ModbusPduParserAbc",
    "ModbusRequestFC1",
    "ModbusRequestFC2",
    "ModbusRequestFC3",
    "ModbusRequestFC4",
    "ModbusRequestFC5",
    "ModbusRequestFC6",
    "ModbusRequestFC7",
    "ModbusRequestFC8",
    "ModbusRequestFC15",
    "ModbusRequestFC16",
    "ModbusRequestFC22",
    "ModbusRequestFC23",
    "ModbusRequestFC43",
    "ModbusResponseFC1",
    "ModbusResponseFC2",
    "ModbusResponseFC3",
    "ModbusResponseFC4",
    "ModbusResponseFC5",
    "ModbusResponseFC6",
    "ModbusResponseFC7",
    "ModbusResponseFC8",
    "ModbusResponseFC15",
    "ModbusResponseFC16",
    "ModbusResponseFC22",
    "ModbusResponseFC23",
    "ModbusResponseFC43",
    "ModbusViolation",
]
