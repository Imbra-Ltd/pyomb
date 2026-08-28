"""A response has to be matched to the request that caused it.

Every request went out with transaction id 0 and unit id 1, and the reply was
deserialised and returned without comparing anything. While exactly one
request is outstanding that is harmless, because the exchange is serialised by
construction. It stops being harmless once a request times out: the client
moves on, the delayed reply to the abandoned request arrives first, and with
no identifier to tell them apart it is returned as the answer to the current
request. The caller gets a plausible reading belonging to another question.

These tests pin the counter, the correlation and the configurable unit id.
"""

import unittest

from stub_socket import LoopbackSocket

from pyomb.errors import ModbusNetworkError
from pyomb.omb_client import OmbClientSim
from pyomb.packets import ModbusHeader, ModbusResponseFC1, ModbusTcpResponse


def response_frame(trans_id, unit_id=1):
    """Builds a serialised FC1 response carrying the given identifier."""

    pdu = ModbusResponseFC1(byte_count=1, output_status=(1,))
    header = ModbusHeader(trans_id=trans_id, prot_id=0, length=len(pdu) + 1, unit_id=unit_id)

    return ModbusTcpResponse(header=header, pdu=pdu).serialize()


class ClientOnAStubSocket(unittest.TestCase):
    """Builds a client whose socket is a stub rather than a real connection."""

    def make_client(self, inbox=b"", **options):
        client = OmbClientSim(**options)

        # The constructor opens a real socket that is never connected here.
        client.sock.close()
        client.sock = LoopbackSocket(inbox)

        return client

    def sent_headers(self, client):
        return [ModbusHeader.deserialize(frame[: ModbusHeader.SIZE]) for frame in client.sock.sent]


class TestTransactionId(ClientOnAStubSocket):
    def test_identifier_increments_per_request(self):
        # Previously every request went out with trans_id 0.
        client = self.make_client()

        for _ in range(3):
            client.sendRequest(fc=1, readAddress=0, readCount=1)

        self.assertEqual([h.trans_id for h in self.sent_headers(client)], [0, 1, 2])

    def test_identifier_wraps_at_sixteen_bits(self):
        client = self.make_client()
        client._next_trans_id = 0xFFFF

        for _ in range(2):
            client.sendRequest(fc=1, readAddress=0, readCount=1)

        self.assertEqual([h.trans_id for h in self.sent_headers(client)], [0xFFFF, 0])


class TestUnitId(ClientOnAStubSocket):
    def test_defaults_to_one(self):
        client = self.make_client()

        client.sendRequest(fc=1, readAddress=0, readCount=1)

        self.assertEqual(self.sent_headers(client)[0].unit_id, 1)

    def test_comes_from_the_configuration(self):
        # Previously hardcoded, so a device behind a gateway on any other unit
        # id could not be addressed at all.
        client = self.make_client(unit_id=17)

        client.sendRequest(fc=1, readAddress=0, readCount=1)

        self.assertEqual(self.sent_headers(client)[0].unit_id, 17)


class TestResponseCorrelation(ClientOnAStubSocket):
    def test_matching_response_is_returned(self):
        client = self.make_client(inbox=response_frame(trans_id=0))

        client.sendRequest(fc=1, readAddress=0, readCount=1)
        header, pdu = client.waitResponse()

        self.assertEqual(header.trans_id, 0)
        self.assertIsNotNone(pdu)

    def test_late_response_to_an_abandoned_request_is_discarded(self):
        # Request 0 is never answered in time. Request 1 goes out, and the
        # reply to 0 arrives first. Previously it was returned as the answer.
        client = self.make_client(inbox=response_frame(trans_id=0) + response_frame(trans_id=1))

        client.sendRequest(fc=1, readAddress=0, readCount=1)
        client.sendRequest(fc=1, readAddress=0, readCount=1)
        header, _ = client.waitResponse()

        self.assertEqual(header.trans_id, 1)

    def test_unanswerable_stream_of_mismatches_raises(self):
        stale = b"".join(response_frame(trans_id=999) for _ in range(32))
        client = self.make_client(inbox=stale)

        client.sendRequest(fc=1, readAddress=0, readCount=1)

        with self.assertRaises(ModbusNetworkError):
            client.waitResponse()

    def test_closed_connection_reports_no_response(self):
        # Previously raised AttributeError: the empty-response placeholder was
        # a plain tuple, and the return statement asked it for .header.
        client = self.make_client()

        client.sendRequest(fc=1, readAddress=0, readCount=1)

        self.assertEqual(client.waitResponse(), (None, None))


if __name__ == "__main__":
    unittest.main()
