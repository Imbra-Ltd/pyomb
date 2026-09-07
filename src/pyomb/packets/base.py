"""Constraints and the abstract packet bases.

A finding, the base every packet component descends from, and the parser
interface. Nothing here knows a function code or a transport.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from pyomb.errors import ModbusPacketError

# The parser interface is declared here and answers in PDU objects, which are
# defined one layer up. Importing that for real would close a cycle.
if TYPE_CHECKING:
    from pyomb.packets.pdu import ModbusPdu


################################################################################


class ModbusViolation:
    """A constraint a packet component does not satisfy.

    A finding carries the rule's identity rather than only a message, so a
    test grading a peer can assert which bound was crossed. Building a frame
    that breaks a rule stays possible: this reports, it does not prevent.

    Args:
        source (str) : The component that declared the constraint
        field (str)  : The field carrying the offending value
        rule (str)   : The constraint, as the specification states it
        value (int)  : The value that broke it

    Example:
        >>> from pyomb.packets import ModbusRequestFC3
        >>> pdu = ModbusRequestFC3(start_addr=0, quantity=126)
        >>> finding = pdu.violations()[0]
        >>> finding.field
        'quantity'
    """

    def __init__(self, source: str, field: str, rule: str, value: int) -> None:
        """Initialize the violation."""
        self.source = source
        self.field = field
        self.rule = rule
        self.value = value

    def __eq__(self, other: object) -> bool:
        """Check if two violations report the same finding."""
        return self.__dict__ == other.__dict__

    def __ne__(self, other: object) -> bool:
        """Check if two violations report different findings."""
        return not self.__eq__(other)

    def __str__(self) -> str:
        """Return a string representation of the violation."""
        msg = "{0}.{1} is {2}; the specification requires {3}"
        return msg.format(self.source, self.field, self.value, self.rule)

    def __repr__(self) -> str:
        """Return the same text the string form carries."""
        return f"ModbusViolation({self})"


################################################################################
# ABSTRACT CLASSES
################################################################################


class ModbusPacketAbc(metaclass=ABCMeta):
    """Abstract class for Modbus Packets."""

    # Field name to inclusive low and high, from the specification. Empty
    # states that it bounds nothing here, which is not the same as unread.
    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {}

    # The attributes holding components this one carries, so asking a packet
    # for its findings returns the parts' findings too.
    PARTS: ClassVar[tuple[str, ...]] = ()

    def _finding(self, field: str, rule: str) -> ModbusViolation:
        """Build a finding naming this component and one of its fields.

        Args:
            field (str) : The field carrying the offending value
            rule (str)  : The constraint, as the specification states it

        Returns:
            ModbusViolation : The finding
        """
        return ModbusViolation(
            source=type(self).__name__,
            field=field,
            rule=rule,
            value=getattr(self, field),
        )

    def _fixed_count(self, field: str, expected: int, rule: str) -> tuple[ModbusViolation, ...]:
        """Report a count that disagrees with what the other fields imply.

        Args:
            field (str)    : The counting field
            expected (int) : What the other fields fix it at
            rule (str)     : The constraint, as the specification states it

        Returns:
            tuple : One finding, or empty when the count agrees
        """
        if getattr(self, field) == expected:
            return ()

        return (self._finding(field, f"{rule}, which is {expected}"),)

    def violations(self) -> tuple[ModbusViolation, ...]:
        """Report every constraint this packet and its parts break.

        Returns:
            tuple : The findings, empty when the packet is conforming
        """
        found = []

        for field in sorted(self.LIMITS):
            low, high = self.LIMITS[field]
            value = getattr(self, field)

            if not low <= value <= high:
                # A field the specification fixes at one value reads as that
                # value rather than as a range running from it to itself.
                rule = f"0x{low:04X}"

                if low != high:
                    rule = f"{rule} to 0x{high:04X}"

                found.append(self._finding(field, rule))

        for part in self.PARTS:
            component = getattr(self, part, None)

            if component is not None:
                found.extend(component.violations())

        return tuple(found)

    def validate(self) -> None:
        """Raise unless the packet and its parts are conforming.

        Raises:
            ModbusPacketError : If any constraint is broken, naming each one
        """
        found = self.violations()

        if found:
            raise ModbusPacketError("; ".join(str(finding) for finding in found))

    def __eq__(self, other: object) -> bool:
        """Check if two packets are equal."""
        return self.__dict__ == other.__dict__

    def __ne__(self, other: object) -> bool:
        """Check if two packets are not equal."""
        return not self.__eq__(other)

    # No tuning parameters here or below: a packet knows its own wire layout,
    # and a caller handing one in could ask for a frame the spec disallows.
    @abstractmethod
    def serialize(self) -> bytes:
        """Serialize the packet and return a stream of bytes.

        Returns:
            bytes : The serialized packet
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def deserialize(cls, stream: bytes) -> ModbusPacketAbc:
        """Deserialize the packet from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to deserialize

        Returns:
            ModbusPacketAbc : The deserialized packet
        """
        raise NotImplementedError


class ModbusPduParserAbc(metaclass=ABCMeta):
    """Abstract class for Modbus PDU Parser."""

    @classmethod
    @abstractmethod
    def parse_request(cls, stream: bytes) -> ModbusPdu:
        """Parse the Modbus Request PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to parse

        Returns:
            ModbusPdu : The Modbus PDU object
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def parse_response(cls, stream: bytes) -> ModbusPdu:
        """Parse the Modbus Response PDU from a stream of bytes.

        Args:
            stream (bytes): The stream of bytes to parse

        Returns:
            ModbusPdu : The Modbus PDU object
        """
        raise NotImplementedError


################################################################################
# BASE CLASSES
################################################################################
