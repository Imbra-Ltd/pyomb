"""Packet constraints are declared per class and queried, never a mode.

The codec checked two things, both structural: the RTU checksum and the TCP
header's declared length. No function-code field limit was written down
anywhere, so a frame carrying a quantity no device will honour was built and
emitted without complaint -- well formed, correct checksum, and wrong.

The bounds now sit on the class carrying the field, as `LIMITS`, and two
methods read them: `violations()` returns findings, `validate()` raises.
`serialize()` calls neither, because building a frame a device rejects is
the point of a simulator rather than an accident to prevent.

Each bound below is anchored to the published specification rather than to
this library's output: the boundary values come from the Modbus Application
Protocol v1.1b3, and two cases use that document's own worked examples.
"""

import ast
import inspect
import pathlib
import unittest

import pyomb.packets as packets
from pyomb.errors import ModbusPacketError
from pyomb.packets import (
    ModbusHeader,
    ModbusPdu,
    ModbusRequestFC1,
    ModbusRequestFC3,
    ModbusRequestFC5,
    ModbusRequestFC15,
    ModbusRequestFC16,
    ModbusRequestFC23,
    ModbusRequestFC43,
    ModbusResponseFC3,
    ModbusRtuRequest,
    ModbusTcpRequest,
    ModbusViolation,
)

SOURCE = pathlib.Path(packets.__file__)


class ASpecificationExampleIsConforming(unittest.TestCase):
    """The document's own worked examples report nothing."""

    def test_the_read_holding_registers_example(self):
        # Modbus Application Protocol v1.1b3: read 3 registers from 0x006B.
        request = ModbusRequestFC3(start_addr=0x006B, quantity=3)

        self.assertEqual(request.violations(), ())

    def test_the_write_multiple_coils_example(self):
        # Modbus Application Protocol v1.1b3: write 10 coils from 0x0013,
        # with a byte count of 2. That example is what fixes the rounding
        # rule -- 10 coils occupy two whole bytes.
        request = ModbusRequestFC15(
            start_addr=0x0013,
            quantity=10,
            byte_count=2,
            values=[0xCD, 0x01],
        )

        self.assertEqual(request.violations(), ())


class AQuantityIsBoundedByTheFunctionCode(unittest.TestCase):
    """One format string, several bounds -- the class carries which."""

    def test_read_coils_caps_at_two_thousand(self):
        self.assertEqual(ModbusRequestFC1(start_addr=0, quantity=2000).violations(), ())

        past = ModbusRequestFC1(start_addr=0, quantity=2001).violations()

        self.assertEqual(len(past), 1)
        self.assertEqual(past[0].field, "quantity")

    def test_read_holding_registers_caps_at_one_hundred_and_twenty_five(self):
        # The same format string as Read Coils, and one sixteenth the cap.
        # That pair is why the bound cannot be read off the format.
        self.assertEqual(ModbusRequestFC3(start_addr=0, quantity=125).violations(), ())
        self.assertEqual(len(ModbusRequestFC3(start_addr=0, quantity=126).violations()), 1)

    def test_write_multiple_coils_caps_at_one_thousand_nine_hundred_and_sixty_eight(self):
        conforming = ModbusRequestFC15(start_addr=0, quantity=1968, byte_count=246, values=[0] * 246)

        self.assertEqual(conforming.violations(), ())

        past = ModbusRequestFC15(start_addr=0, quantity=1969, byte_count=247, values=[0] * 247)

        self.assertEqual([finding.field for finding in past.violations()], ["quantity"])

    def test_write_multiple_registers_caps_at_one_hundred_and_twenty_three(self):
        conforming = ModbusRequestFC16(start_addr=0, quantity=123, byte_count=246, values=[0] * 123)

        self.assertEqual(conforming.violations(), ())

        past = ModbusRequestFC16(start_addr=0, quantity=124, byte_count=248, values=[0] * 124)

        self.assertEqual([finding.field for finding in past.violations()], ["quantity"])

    def test_read_write_multiple_registers_bounds_both_quantities(self):
        past = ModbusRequestFC23(
            read_start_addr=0,
            read_quantity=126,
            write_start_addr=0,
            write_quantity=122,
            write_byte_count=244,
            write_values=[0] * 122,
        )

        # Both quantities break, and both are reported -- a raise would stop
        # at the first, which is why violations() returns data.
        self.assertEqual(
            sorted(finding.field for finding in past.violations()),
            ["read_quantity", "write_quantity"],
        )


class ARuleAcrossFieldsIsNotABound(unittest.TestCase):
    """A byte count is fixed by the fields beside it, not by a range."""

    def test_write_multiple_coils_rounds_the_quantity_up_to_whole_bytes(self):
        # 8 coils occupy one byte; 9 occupy two. The rounding is the rule.
        self.assertEqual(
            ModbusRequestFC15(start_addr=0, quantity=8, byte_count=1, values=[0]).violations(),
            (),
        )

        wrong = ModbusRequestFC15(start_addr=0, quantity=9, byte_count=1, values=[0])

        self.assertEqual([finding.field for finding in wrong.violations()], ["byte_count"])

    def test_write_multiple_registers_doubles_the_quantity(self):
        self.assertEqual(
            ModbusRequestFC16(start_addr=0, quantity=2, byte_count=4, values=[1, 2]).violations(),
            (),
        )

        wrong = ModbusRequestFC16(start_addr=0, quantity=2, byte_count=3, values=[1, 2])

        self.assertEqual([finding.field for finding in wrong.violations()], ["byte_count"])

    def test_a_read_response_counts_two_bytes_per_register(self):
        self.assertEqual(ModbusResponseFC3(byte_count=4, values=[1, 2]).violations(), ())

        wrong = ModbusResponseFC3(byte_count=5, values=[1, 2])

        self.assertEqual([finding.field for finding in wrong.violations()], ["byte_count"])

    def test_a_coil_takes_one_of_two_values(self):
        # Write Single Coil states a value set rather than a range, which no
        # LIMITS entry can express.
        for legal in (0x0000, 0xFF00):
            self.assertEqual(ModbusRequestFC5(output_address=0, output_value=legal).violations(), ())

        wrong = ModbusRequestFC5(output_address=0, output_value=0x0001)

        self.assertEqual([finding.field for finding in wrong.violations()], ["output_value"])

    def test_device_identification_names_one_mei_type(self):
        self.assertEqual(ModbusRequestFC43(mei_type=0x0E, mei_data=[1]).violations(), ())
        self.assertEqual(len(ModbusRequestFC43(mei_type=0x0D, mei_data=[1]).violations()), 1)


class ConstraintsReachBeyondThePdu(unittest.TestCase):
    """The header and the slave address carry bounds the specification states."""

    def test_the_protocol_identifier_is_zero(self):
        self.assertEqual(ModbusHeader(trans_id=1, prot_id=0, length=6, unit_id=1).violations(), ())

        wrong = ModbusHeader(trans_id=1, prot_id=2, length=6, unit_id=1)

        self.assertEqual([finding.field for finding in wrong.violations()], ["prot_id"])

    def test_the_slave_address_runs_to_two_hundred_and_forty_seven(self):
        pdu = ModbusRequestFC3(start_addr=0, quantity=1)

        # Zero is the broadcast address every device recognises, so it is a
        # legal address rather than the absence of one.
        for legal in (0, 1, 247):
            self.assertEqual(ModbusRtuRequest(slave_id=legal, pdu=pdu).violations(), ())

        wrong = ModbusRtuRequest(slave_id=248, pdu=pdu)

        self.assertEqual([finding.field for finding in wrong.violations()], ["slave_id"])

    def test_a_packet_reports_for_the_parts_it_holds(self):
        header = ModbusHeader(trans_id=1, prot_id=2, length=6, unit_id=1)
        pdu = ModbusRequestFC3(start_addr=0, quantity=126)

        findings = ModbusTcpRequest(header=header, pdu=pdu).violations()

        # One question, both answers. Without this a caller has to know the
        # shape of what it holds, which is the knowledge the classes carry.
        self.assertEqual(
            sorted(finding.source for finding in findings),
            ["ModbusHeader", "ModbusRequestFC3"],
        )


class TheTwoMethodsDifferInWhatTheyReturn(unittest.TestCase):
    """One reports findings, the other raises; serialization does neither."""

    def test_violations_names_the_rule_and_the_value(self):
        finding = ModbusRequestFC3(start_addr=0, quantity=126).violations()[0]

        self.assertIsInstance(finding, ModbusViolation)
        self.assertEqual(finding.source, "ModbusRequestFC3")
        self.assertEqual(finding.field, "quantity")
        self.assertEqual(finding.value, 126)
        self.assertIn("0x007D", finding.rule)

    def test_validate_raises_and_names_every_finding(self):
        header = ModbusHeader(trans_id=1, prot_id=2, length=6, unit_id=1)
        pdu = ModbusRequestFC3(start_addr=0, quantity=126)

        with self.assertRaises(ModbusPacketError) as caught:
            ModbusTcpRequest(header=header, pdu=pdu).validate()

        self.assertIn("prot_id", str(caught.exception))
        self.assertIn("quantity", str(caught.exception))

    def test_validate_is_silent_on_a_conforming_packet(self):
        self.assertIsNone(ModbusRequestFC3(start_addr=0, quantity=125).validate())

    def test_serialize_never_validates(self):
        # A simulator exists to send the frame a device rejects and grade the
        # answer. Refusing to build it would forfeit the product.
        request = ModbusRequestFC3(start_addr=0, quantity=126)

        self.assertEqual(request.serialize().hex(), "030000007e")
        self.assertNotEqual(request.violations(), ())

    def test_a_generic_pdu_carries_no_bound(self):
        self.assertEqual(ModbusPdu(fc=1, data=(1, 2)).violations(), ())


class EveryPacketClassStatesWhatItWasReadFor(unittest.TestCase):
    """The coverage assertion: an unaudited class must not look audited."""

    # What the module held when this floor was set: 32 concrete packet
    # classes, each declaring LIMITS in its own body. The count is a floor
    # with a margin rather than the exact number, so retiring one class does
    # not fail a rule about specification coverage. Any way the enumeration
    # breaks returns nothing at all, so a floor above zero catches all of
    # them and the margin costs no detection.
    CLASSES_AT_LEAST = 28

    @classmethod
    def setUpClass(cls):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

        cls.declared = set()

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                named = isinstance(item, ast.AnnAssign) and getattr(item.target, "id", "") == "LIMITS"
                if named:
                    cls.declared.add(node.name)

        cls.concrete = [
            name
            for name, value in inspect.getmembers(packets, inspect.isclass)
            if issubclass(value, packets.ModbusPacketAbc) and value is not packets.ModbusPacketAbc
        ]

    def test_the_enumeration_reached_the_classes(self):
        """A pass means the rule was applied, not that nothing was read."""

        self.assertGreaterEqual(
            len(self.concrete),
            self.CLASSES_AT_LEAST,
            f"found {len(self.concrete)} concrete packet class(es) where the "
            f"module holds at least {self.CLASSES_AT_LEAST}; the enumeration "
            "is broken rather than the module being small.",
        )

    def test_every_concrete_class_declares_its_own_limits(self):
        """Inheriting an empty mapping would read as an audited class."""

        # The base declares an empty LIMITS, so a class that never declared
        # one inherits it and reports no violations -- indistinguishable from
        # a class the specification genuinely bounds in no way. Declaring it
        # per class is what separates "unbounded" from "nobody has looked".
        silent = sorted(name for name in self.concrete if name not in self.declared)

        self.assertEqual(
            silent,
            [],
            "concrete packet classes that inherit LIMITS instead of declaring "
            "it, so an unread specification is indistinguishable from a field "
            f"with no bound: {silent}",
        )


if __name__ == "__main__":
    unittest.main()
