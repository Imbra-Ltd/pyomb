import unittest

from pyomb.stream import ModbusFragmenter


class TestFragmenter(unittest.TestCase):
    def test_fragmentation(self):

        # Test message
        test_message = b"0123456789"

        # No fragmentation
        fragments = ModbusFragmenter.fragment(test_message, 0)
        self.assertEqual(fragments, [b"0123456789"])

        # Fragmentation (header is 7 bytes, so 3 bytes are left for the data)
        fragments = ModbusFragmenter.fragment(test_message, 1)
        self.assertEqual(fragments, [b"0123456", b"7", b"8", b"9"])

        # Fragmentation (header is 7 bytes, so 3 bytes are left for the data)
        fragments = ModbusFragmenter.fragment(test_message, 2)
        self.assertEqual(fragments, [b"0123456", b"78", b"9"])

        # Fragmentation (header is 7 bytes, so 3 bytes are left for the data)
        fragments = ModbusFragmenter.fragment(test_message, 3)
        self.assertEqual(fragments, [b"0123456", b"789"])

        # Fragmentation (header is 7 bytes, so 3 bytes are left for the data)
        fragments = ModbusFragmenter.fragment(test_message, 256)
        self.assertEqual(fragments, [b"0123456", b"789"])

    def test_reassembly(self):

        # Test message
        test_message = b"0123456789"

        # Fragmentation (header is 7 bytes, so 3 bytes are left for the data)
        fragments = ModbusFragmenter.fragment(test_message, 1)

        # Reassemble the fragments
        reassembled = ModbusFragmenter.assemble(fragments)
        self.assertEqual(reassembled, test_message)

        # Fragmentation (header is 7 bytes, so 3 bytes are left for the data)
        fragments = ModbusFragmenter.fragment(test_message, 3)

        # Reassemble the fragments
        reassembled = ModbusFragmenter.assemble(fragments)
        self.assertEqual(reassembled, test_message)
