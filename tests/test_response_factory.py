"""The value shaping behind each response, checked one function code at a time.

The dispatch tests confirm that a request of a given function code comes back
as the matching response class. That says nothing about the contents, which is
where the arithmetic lives: byte counts derived from a requested quantity, and
the echo fields a write response is required to return unchanged. Both are
easy to get subtly wrong and impossible to notice from the client, because the
client believes whatever the server reports.
"""

import unittest

from pyomb.omb_server import ResponseFactory
from pyomb.packets import ModbusRequestFC1
from pyomb.packets import ModbusRequestFC2
from pyomb.packets import ModbusRequestFC3
from pyomb.packets import ModbusRequestFC4
from pyomb.packets import ModbusRequestFC5
from pyomb.packets import ModbusRequestFC6
from pyomb.packets import ModbusRequestFC15
from pyomb.packets import ModbusRequestFC16
from pyomb.packets import ModbusRequestFC22
from pyomb.packets import ModbusRequestFC23
from pyomb.packets import ModbusRequestFC43


class TestBitReadByteCounts(unittest.TestCase):
    """FC1 and FC2 pack bits, so the byte count rounds up."""

    def test_fc1_rounds_the_byte_count_up(self):
        for quantity, expected in ((1, 1), (7, 1), (8, 1), (9, 2), (16, 2), (17, 3), (2000, 250)):
            with self.subTest(quantity=quantity):
                pdu = ResponseFactory.create_fc1_rsp(ModbusRequestFC1(start_addr=0, quantity=quantity))

                self.assertEqual(pdu.byte_count, expected)
                self.assertEqual(len(pdu.output_status), expected)

    def test_fc2_rounds_the_byte_count_up(self):
        for quantity, expected in ((1, 1), (8, 1), (9, 2), (17, 3)):
            with self.subTest(quantity=quantity):
                pdu = ResponseFactory.create_fc2_rsp(ModbusRequestFC2(start_addr=0, quantity=quantity))

                self.assertEqual(pdu.byte_count, expected)
                self.assertEqual(len(pdu.input_status), expected)

    def test_fc1_fills_with_the_requested_coil_value(self):
        pdu = ResponseFactory.create_fc1_rsp(ModbusRequestFC1(start_addr=0, quantity=16), coil_value=0xA5)

        self.assertEqual(pdu.output_status, (0xA5, 0xA5))


class TestRegisterReadByteCounts(unittest.TestCase):
    """FC3, FC4 and FC23 return whole registers, so the count doubles."""

    def test_fc3_counts_two_bytes_per_register(self):
        for quantity in (1, 2, 10, 125):
            with self.subTest(quantity=quantity):
                pdu = ResponseFactory.create_fc3_rsp(ModbusRequestFC3(start_addr=0, quantity=quantity))

                self.assertEqual(pdu.byte_count, 2 * quantity)
                self.assertEqual(len(pdu.values), quantity)

    def test_fc4_counts_two_bytes_per_register(self):
        for quantity in (1, 2, 10, 125):
            with self.subTest(quantity=quantity):
                pdu = ResponseFactory.create_fc4_rsp(ModbusRequestFC4(start_addr=0, quantity=quantity))

                self.assertEqual(pdu.byte_count, 2 * quantity)
                self.assertEqual(len(pdu.values), quantity)

    def test_fc23_counts_the_read_quantity_not_the_write_quantity(self):
        # The read and write halves have separate counts, and the response
        # carries only what was read.
        pdu = ResponseFactory.create_fc23_rsp(
            ModbusRequestFC23(
                read_start_addr=0,
                read_quantity=3,
                write_start_addr=8,
                write_quantity=1,
                write_byte_count=2,
                write_values=[0xABCD],
            )
        )

        self.assertEqual(pdu.byte_count, 6)
        self.assertEqual(len(pdu.values), 3)

    def test_fc3_fills_with_the_requested_register_value(self):
        pdu = ResponseFactory.create_fc3_rsp(ModbusRequestFC3(start_addr=0, quantity=2), register_value=0x1234)

        self.assertEqual(pdu.values, (0x1234, 0x1234))


class TestWriteEchoes(unittest.TestCase):
    """A write response repeats the request, which is how a client confirms it."""

    def test_fc5_echoes_the_address_and_the_value(self):
        pdu = ResponseFactory.create_fc5_rsp(ModbusRequestFC5(output_address=0x0003, output_value=0xFF00))

        self.assertEqual(pdu.output_address, 0x0003)
        self.assertEqual(pdu.output_value, 0xFF00)

    def test_fc6_echoes_the_address_and_the_value(self):
        # The value used to come back as a copy of the address, so a write of
        # 0xABCD to register 3 was confirmed as a write of 0x0003.
        pdu = ResponseFactory.create_fc6_rsp(ModbusRequestFC6(output_address=0x0003, output_value=0xABCD))

        self.assertEqual(pdu.output_address, 0x0003)
        self.assertEqual(pdu.output_value, 0xABCD)

    def test_fc6_echo_distinguishes_address_from_value(self):
        # Guards the shape of the defect rather than one example of it: an
        # address and a value that differ must stay distinguishable.
        pdu = ResponseFactory.create_fc6_rsp(ModbusRequestFC6(output_address=0x0011, output_value=0x0022))

        self.assertNotEqual(pdu.output_value, pdu.output_address)

    def test_fc15_echoes_the_address_and_the_quantity(self):
        pdu = ResponseFactory.create_fc15_rsp(
            ModbusRequestFC15(start_addr=0x0013, quantity=10, byte_count=2, values=[0xCD, 0x01])
        )

        self.assertEqual(pdu.start_addr, 0x0013)
        self.assertEqual(pdu.quantity, 10)

    def test_fc16_echoes_the_address_and_the_quantity(self):
        pdu = ResponseFactory.create_fc16_rsp(
            ModbusRequestFC16(start_addr=0x0001, quantity=2, byte_count=4, values=[0x000A, 0x0102])
        )

        self.assertEqual(pdu.start_addr, 0x0001)
        self.assertEqual(pdu.quantity, 2)

    def test_fc22_echoes_the_reference_and_both_masks(self):
        pdu = ResponseFactory.create_fc22_rsp(ModbusRequestFC22(ref_addr=0x0004, and_mask=0x00F2, or_mask=0x0025))

        self.assertEqual(pdu.ref_addr, 0x0004)
        self.assertEqual(pdu.and_mask, 0x00F2)
        self.assertEqual(pdu.or_mask, 0x0025)

    def test_fc43_echoes_the_mei_type_and_data(self):
        pdu = ResponseFactory.create_fc43_rsp(ModbusRequestFC43(mei_type=0x0E, mei_data=(1, 2, 3)))

        self.assertEqual(pdu.mei_type, 0x0E)
        self.assertEqual(tuple(pdu.mei_data), (1, 2, 3))


class TestStatusAndErrorResponses(unittest.TestCase):
    def test_fc7_reports_the_given_status(self):
        self.assertEqual(ResponseFactory.create_fc7_rsp().status, 0x00)
        self.assertEqual(ResponseFactory.create_fc7_rsp(0x11).status, 0x11)

    def test_error_response_keeps_the_requested_function_code(self):
        pdu = ResponseFactory.create_err_rsp(3)

        self.assertEqual(pdu.fc, 3)
        self.assertEqual(pdu.exc_code, 0x04)

    def test_error_response_sets_the_high_bit_on_the_wire(self):
        # The function code is stored unmasked and the mask is applied when
        # serialising, which is what marks the frame as an exception.
        self.assertEqual(ResponseFactory.create_err_rsp(3).serialize(), b"\x83\x04")


if __name__ == "__main__":
    unittest.main()
