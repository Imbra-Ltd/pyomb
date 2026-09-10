"""The generic RTU packet reads a frame without being told its direction.

A server echoes the request's function code in a normal response, so the byte
is identical in both directions and only an exception response differs by
setting its most significant bit. The two direction-specific RTU classes have
to be told which they hold; this one declines to interpret the PDU at all, the
way the generic TCP packet does.

The frames below are the published vectors the checksum tests already pin, so
the bytes are anchored outside this library.
"""

import unittest

from pyomb.adu import ModbusRtuPacket, ModbusRtuRequest, ModbusRtuResponse
from pyomb.errors import ModbusPacketError
from pyomb.pdu import ModbusPdu, ModbusRequestFC3, ModbusResponseFC4

# 11 03 00 00 00 02 -- read two holding registers from slave 17, checksum C6 9B.
REQUEST_FRAME = b"\x11\x03\x00\x00\x00\x02\xc6\x9b"

# 01 04 02 FF FF -- two bytes of input register data from slave 1, checksum B8 80.
RESPONSE_FRAME = b"\x01\x04\x02\xff\xff\xb8\x80"

# 01 83 02 -- slave 1 refuses an FC3 with ILLEGAL DATA ADDRESS. The exception
# bit is the one case where the function code states a direction.
EXCEPTION_FRAME = b"\x01\x83\x02\xc0\xf1"


class TestReadingWithoutADirection(unittest.TestCase):
    def test_reads_a_request_frame(self):
        packet = ModbusRtuPacket.deserialize(REQUEST_FRAME)

        self.assertEqual(packet.slave_id, 17)
        self.assertEqual(packet.pdu.fc, 3)
        self.assertEqual(packet.pdu.data, (0, 0, 0, 2))
        self.assertEqual(packet.crc, 0x9BC6)

    def test_reads_a_response_frame(self):
        packet = ModbusRtuPacket.deserialize(RESPONSE_FRAME)

        self.assertEqual(packet.slave_id, 1)
        self.assertEqual(packet.pdu.fc, 4)
        self.assertEqual(packet.pdu.data, (2, 255, 255))
        self.assertEqual(packet.crc, 0x80B8)

    def test_reads_an_exception_response(self):
        packet = ModbusRtuPacket.deserialize(EXCEPTION_FRAME)

        self.assertEqual(packet.slave_id, 1)
        self.assertEqual(packet.pdu.fc, 0x83)
        self.assertEqual(packet.pdu.data, (2,))

    def test_the_payload_is_not_interpreted(self):
        # The start address and quantity stay payload bytes rather than
        # becoming fields, which is what lets one class read both directions.
        packet = ModbusRtuPacket.deserialize(REQUEST_FRAME)

        self.assertFalse(hasattr(packet.pdu, "start_addr"))
        self.assertEqual(ModbusPdu(fc=3, data=(0, 0, 0, 2)).serialize(), packet.pdu.serialize())


class TestWritingTheSameBytes(unittest.TestCase):
    def test_writes_what_the_request_class_writes(self):
        pdu = ModbusRequestFC3(start_addr=0, quantity=2)

        generic = ModbusRtuPacket(slave_id=17, pdu=pdu).serialize()

        self.assertEqual(generic, REQUEST_FRAME)
        self.assertEqual(generic, ModbusRtuRequest(slave_id=17, pdu=pdu).serialize())

    def test_writes_what_the_response_class_writes(self):
        pdu = ModbusResponseFC4(byte_count=2, values=(0xFFFF,))

        generic = ModbusRtuPacket(slave_id=1, pdu=pdu).serialize()

        self.assertEqual(generic, RESPONSE_FRAME)
        self.assertEqual(generic, ModbusRtuResponse(slave_id=1, pdu=pdu).serialize())

    def test_a_frame_read_generically_writes_the_bytes_it_arrived_as(self):
        for frame in (REQUEST_FRAME, RESPONSE_FRAME, EXCEPTION_FRAME):
            with self.subTest(frame=frame.hex()):
                self.assertEqual(ModbusRtuPacket.deserialize(frame).serialize(), frame)

    def test_serialize_overrides_an_assigned_checksum(self):
        # set_crc() describes a frame, it does not get to contradict one.
        packet = ModbusRtuPacket(slave_id=17, pdu=ModbusRequestFC3(start_addr=0, quantity=2))
        packet.set_crc(0xDEAD)

        self.assertEqual(packet.serialize(), REQUEST_FRAME)
        self.assertEqual(packet.crc, 0x9BC6)


class TestTheChecksumIsVerified(unittest.TestCase):
    def test_rejects_a_corrupt_frame(self):
        corrupt = REQUEST_FRAME[:-2] + b"\xad\xde"

        with self.assertRaises(ModbusPacketError):
            ModbusRtuPacket.deserialize(corrupt)

    def test_can_be_told_to_skip_the_check(self):
        corrupt = REQUEST_FRAME[:-2] + b"\xad\xde"

        packet = ModbusRtuPacket.deserialize(corrupt, verify_crc=False)

        self.assertEqual(packet.crc, 0xDEAD)
        self.assertEqual(packet.pdu.fc, 3)

    def test_rejects_a_frame_too_short_to_hold_a_checksum(self):
        with self.assertRaises(ModbusPacketError):
            ModbusRtuPacket.deserialize(b"\x01\x03")


if __name__ == "__main__":
    unittest.main()
