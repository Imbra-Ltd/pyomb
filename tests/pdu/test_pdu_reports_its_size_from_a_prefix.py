"""A PDU class states its own size before anything has parsed it.

An RTU frame declares no length, so a reader splitting a stream has to work
the boundary out from the content it has so far. `__len__` cannot answer that
question: it reads the count off a constructed instance, which is the thing
the reader is still trying to establish it can build.

The vectors are the worked examples of the Modbus Application Protocol
v1.1b3, sections 6.3, 6.11 and 6.12, so the sizes are anchored outside this
library.
"""

import unittest

from pyomb.errors import ModbusPacketError
from pyomb.packets import (
    ModbusError,
    ModbusPdu,
    ModbusPduParser,
    ModbusRequestFC1,
    ModbusRequestFC3,
    ModbusRequestFC7,
    ModbusRequestFC8,
    ModbusRequestFC15,
    ModbusRequestFC16,
    ModbusRequestFC22,
    ModbusRequestFC43,
    ModbusResponseFC3,
    ModbusResponseFC8,
    ModbusResponseFC43,
)

# Section 6.3, read registers 108 to 110: the request is fixed at five bytes
# and the response carries a byte count of six.
FC3_REQUEST = b"\x03\x00\x6b\x00\x03"
FC3_RESPONSE = b"\x03\x06\x02\x2b\x00\x00\x00\x64"

# Section 6.11, write ten coils from coil 20. The byte count is 2 and the
# payload is two bytes.
FC15_REQUEST = b"\x0f\x00\x13\x00\x0a\x02\xcd\x01"

# Section 6.12, write two registers from register 2. The byte count is 4 and
# the payload is two registers, so the count is bytes rather than items.
FC16_REQUEST = b"\x10\x00\x01\x00\x02\x04\x00\x0a\x01\x02"

# A registry of this size is what the library ships; the floor sits below it
# so retiring a class does not fail an unrelated rule.
REGISTERED_FLOOR = 20


class TestAFixedLayoutSizesItself(unittest.TestCase):
    def test_a_read_request_is_five_bytes(self):
        self.assertEqual(ModbusRequestFC3.expected_size(FC3_REQUEST), len(FC3_REQUEST))
        self.assertEqual(ModbusRequestFC1.expected_size(b""), 5)

    def test_a_mask_write_request_is_seven_bytes(self):
        self.assertEqual(ModbusRequestFC22.expected_size(b""), 7)

    def test_a_function_code_alone_is_one_byte(self):
        self.assertEqual(ModbusRequestFC7.expected_size(b""), 1)

    def test_an_exception_response_is_two_bytes(self):
        self.assertEqual(ModbusError.expected_size(b""), 2)

    def test_no_prefix_is_needed(self):
        # Nothing in the frame is read, so a fixed class answers before any
        # payload has arrived.
        self.assertEqual(ModbusRequestFC3.expected_size(b""), 5)


class TestACountFieldSizesTheRest(unittest.TestCase):
    def test_a_read_response_is_sized_by_its_byte_count(self):
        self.assertEqual(ModbusResponseFC3.expected_size(FC3_RESPONSE), len(FC3_RESPONSE))

    def test_only_the_count_field_has_to_have_arrived(self):
        self.assertEqual(ModbusResponseFC3.expected_size(FC3_RESPONSE[:2]), 8)

    def test_a_coil_write_request_is_sized_by_its_byte_count(self):
        self.assertEqual(ModbusRequestFC15.expected_size(FC15_REQUEST), len(FC15_REQUEST))

    def test_the_count_is_bytes_and_not_items(self):
        # Four bytes of payload arrive as two registers. A count read as items
        # would size this frame at eight.
        self.assertEqual(ModbusRequestFC16.expected_size(FC16_REQUEST), 10)

    def test_bytes_beyond_the_frame_do_not_change_the_answer(self):
        stream = FC3_RESPONSE + b"\x11\x03\x00\x00\x00\x02\xc6\x9b"

        self.assertEqual(ModbusResponseFC3.expected_size(stream), len(FC3_RESPONSE))


class TestAPrefixTooShortToDecide(unittest.TestCase):
    def test_the_function_code_alone_is_not_enough(self):
        self.assertIsNone(ModbusResponseFC3.expected_size(b"\x03"))

    def test_a_prefix_stopping_before_the_count_is_not_enough(self):
        self.assertIsNone(ModbusRequestFC15.expected_size(FC15_REQUEST[:5]))

    def test_an_empty_prefix_is_not_enough(self):
        self.assertIsNone(ModbusResponseFC3.expected_size(b""))


class TestALayoutThatStatesNoSize(unittest.TestCase):
    def test_the_generic_pdu_refuses(self):
        # It models no function code, so its payload has no declared shape.
        with self.assertRaises(ModbusPacketError):
            ModbusPdu.expected_size(b"\x01\x02\x03")

    def test_diagnostics_and_the_encapsulated_interface_refuse(self):
        # Both lead with a discriminator -- a sub-function and an MEI type --
        # rather than a count, so no byte of the prefix says where they end.
        for cls in (ModbusRequestFC8, ModbusResponseFC8, ModbusRequestFC43, ModbusResponseFC43):
            with self.subTest(pdu=cls.__name__), self.assertRaises(ModbusPacketError):
                cls.expected_size(b"\xff" * 8)

    def test_the_refusal_names_the_class(self):
        with self.assertRaises(ModbusPacketError) as caught:
            ModbusRequestFC43.expected_size(b"\xff" * 8)

        self.assertIn("ModbusRequestFC43", str(caught.exception))


class TestTheDeclarationsAgree(unittest.TestCase):
    """The size is read from PDU_COUNT, so its position is load-bearing."""

    def setUp(self):
        self.registered = sorted(ModbusPduParser.get_registry().values(), key=lambda cls: cls.__name__)

    def test_the_registry_was_read(self):
        self.assertGreaterEqual(len(self.registered), REGISTERED_FLOOR)

    def test_a_count_field_is_the_last_declared_field(self):
        # expected_size() reads the byte immediately ahead of the payload, so
        # a count declared anywhere else would size every frame wrongly.
        counted = [cls for cls in self.registered if cls.PDU_COUNT is not None]

        self.assertNotEqual(counted, [])
        for cls in counted:
            with self.subTest(pdu=cls.__name__):
                self.assertEqual(cls.PDU_COUNT, (cls.PDU_FIELDS or ())[-1])
                self.assertTrue(cls.PDU_FORMAT.split("{0}")[0].endswith("B"))

    def test_every_registered_class_either_sizes_or_refuses(self):
        sized, refused = [], []

        for cls in self.registered:
            try:
                size = cls.expected_size(b"\x04" * 16)
            except ModbusPacketError:
                refused.append(cls.__name__)
                continue
            with self.subTest(pdu=cls.__name__):
                self.assertIsInstance(size, int)
            sized.append(cls.__name__)

        self.assertNotEqual(sized, [])
        self.assertEqual(refused, ["ModbusRequestFC43", "ModbusRequestFC8", "ModbusResponseFC43", "ModbusResponseFC8"])


if __name__ == "__main__":
    unittest.main()
