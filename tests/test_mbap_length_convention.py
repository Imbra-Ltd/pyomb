"""One MBAP length convention across the codec and the transport.

The length field counts the unit identifier plus the PDU. packets.py and the
README always did; stream.py counted the PDU alone, so the sender wrote a
length one short and the receiver read one byte too many. The two halves were
self-consistent and therefore invisible until the codec started validating the
field. These tests pin the single convention at both layers.
"""

import unittest

from stub_socket import StubSocket

from pyomb.packets import ModbusHeader, ModbusPduParser, ModbusRequestFC1, ModbusTcpRequest
from pyomb.stream import ModbusFragmenter, ModbusTcpStream


class TestLengthConvention(unittest.TestCase):
    def setUp(self):
        self.saved_registry = dict(ModbusPduParser.get_registry())
        ModbusPduParser.register(ModbusRequestFC1)

        self.pdu = ModbusRequestFC1(start_addr=0, quantity=1)
        self.frame = ModbusTcpRequest(
            header=ModbusHeader(unit_id=1, length=len(self.pdu) + 1), pdu=self.pdu
        ).serialize()

    def tearDown(self):
        ModbusPduParser.set_registry(self.saved_registry)

    def test_fragmenter_measures_the_whole_frame(self):
        # Previously returned len(frame) + 1.
        self.assertEqual(ModbusFragmenter.get_message_length(self.frame), len(self.frame))

    def test_declared_length_matches_unit_id_plus_pdu(self):
        header = ModbusHeader.deserialize(self.frame[: ModbusHeader.SIZE])

        self.assertEqual(header.length, len(self.pdu) + 1)
        self.assertEqual(len(self.frame), ModbusHeader.SIZE + header.length - 1)

    def test_stub_fixture_is_conformant(self):
        header = ModbusHeader.deserialize(StubSocket.DATA[: ModbusHeader.SIZE])
        pdu_bytes = len(StubSocket.DATA) - ModbusHeader.SIZE

        self.assertEqual(header.length, pdu_bytes + 1)

    def test_receive_reassembles_at_every_fragment_size(self):
        for frag_size in (0, 1, 3, 7, 100):
            sock = StubSocket()
            expected = sock.recv_data
            stream = ModbusTcpStream(
                sock=sock, fragmenter=ModbusFragmenter(), frag_delay=0, frag_size=frag_size, burst=False
            )

            self.assertEqual(stream.receive(), expected, f"mismatch at frag_size={frag_size}")

    def test_sender_output_survives_the_codec(self):
        # ModbusTcpSender.run() assigns the length this way before serializing;
        # with the old value the codec rejected its own transport's frames.
        packet = ModbusTcpRequest(header=ModbusHeader(unit_id=1), pdu=self.pdu)
        packet.header.length = len(packet.pdu) + 1

        parsed = ModbusTcpRequest.deserialize(packet.serialize())

        self.assertEqual(parsed.pdu.start_addr, 0)
        self.assertEqual(parsed.pdu.quantity, 1)


if __name__ == "__main__":
    unittest.main()
