import unittest

from pyomb.packets import (
    ModbusError,
    ModbusHeader,
    ModbusPdu,
    ModbusPduParser,
    ModbusRequestFC1,
    ModbusRequestFC2,
    ModbusRequestFC3,
    ModbusRequestFC4,
    ModbusRequestFC5,
    ModbusRequestFC6,
    ModbusRequestFC7,
    ModbusRequestFC8,
    ModbusRequestFC15,
    ModbusRequestFC16,
    ModbusRequestFC23,
    ModbusRequestFC43,
    ModbusResponseFC1,
    ModbusResponseFC2,
    ModbusResponseFC3,
    ModbusResponseFC4,
    ModbusResponseFC5,
    ModbusResponseFC6,
    ModbusResponseFC7,
    ModbusResponseFC8,
    ModbusResponseFC15,
    ModbusResponseFC16,
    ModbusResponseFC23,
    ModbusResponseFC43,
    ModbusRtuRequest,
    ModbusRtuResponse,
    ModbusTcpRequest,
    ModbusTcpResponse,
)


class TestPacketApi(unittest.TestCase):
    @staticmethod
    def test_modbus_header():

        print("Test ModbusHeader")

        # Create a Modbus TCP header
        header1 = ModbusHeader(trans_id=1, prot_id=2, length=3, unit_id=4)
        print(header1)

        # Serialize the header
        stream = header1.serialize()

        # Deserialize the header
        header2 = ModbusHeader.deserialize(stream)
        print(header2)

        # Assert the headers are equal
        assert header1 == header2

    @staticmethod
    def test_modbus_pdu():

        print("Test ModbusPdu")

        # Create a Modbus PDU
        pdu1 = ModbusPdu(fc=1, data=(1, 2, 3, 4, 5))
        print(pdu1)

        # Serialize the PDU
        stream = pdu1.pack(">B5B")

        # Deserialize the PDU
        pdu2 = ModbusPdu.unpack(stream, ">B5B")
        print(pdu2)

        # Assert the PDUs are equal
        assert pdu1 == pdu2

    @staticmethod
    def test_modbus_pdu_parser():

        print("Test ModbusPduParser")

        # Define the expected PDU
        expected_pdu = ModbusRequestFC1(start_addr=2, quantity=3)

        # Assemble the test pdu
        test_pdu = ModbusPdu(fc=1, data=(0, 2, 0, 3))

        # Serialize the test pdu
        stream = test_pdu.pack(">B4B")

        # Parse the request pdu
        parsed_pdu = ModbusPduParser.parse_request(stream)

        # Check that the parsed pdu is an instance of ModbusRequestFC1
        assert isinstance(parsed_pdu, ModbusRequestFC1)

        # Assert the expected and parsed PDUs are equal
        assert expected_pdu == parsed_pdu

    @staticmethod
    def test_modbus_error():

        print("Test ModbusError")

        # Create a Modbus Error PDU
        pdu1 = ModbusError(fc=1, exc_code=2)
        print(pdu1)

        # Serialize the PDU
        stream = pdu1.serialize()

        # Deserialize the PDU
        pdu2 = ModbusError.deserialize(stream)
        print(pdu2)

        # Assert the PDUs are equal
        assert pdu1 == pdu2

    @staticmethod
    def test_modbus_pdu_fc1_req():

        print("Test ModbusRequestFC1")

        # Create a Modbus PDU
        req1 = ModbusRequestFC1(start_addr=10, quantity=5)
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC1.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc1_rsp():

        print("Test ModbusResponseFC1")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC1(byte_count=2, output_status=(0xFF, 0x00))
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC1.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc2_req():

        print("Test ModbusRequestFC2")

        # Create a Modbus PDU
        req1 = ModbusRequestFC2(start_addr=10, quantity=5)
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC2.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc2_rsp():

        print("Test ModbusResponseFC2")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC2(byte_count=2, input_status=(0xFF, 0x00))
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC2.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc3_req():

        print("Test ModbusRequestFC3")

        # Create a Modbus PDU
        req1 = ModbusRequestFC3(start_addr=10, quantity=5)
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC3.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc3_rsp():

        print("Test ModbusResponseFC3")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC3(byte_count=2, values=(0x0001, 0x0002))
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC3.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc4_req():

        print("Test ModbusRequestFC4")

        # Create a Modbus PDU
        req1 = ModbusRequestFC4(start_addr=10, quantity=5)
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC4.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc4_rsp():

        print("Test ModbusResponseFC4")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC4(byte_count=2, values=(0x0001, 0x0002))
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC4.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc5_req():

        print("Test ModbusRequestFC5")

        # Create a Modbus PDU
        req1 = ModbusRequestFC5(output_address=10, output_value=1)
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC5.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc5_rsp():

        print("Test ModbusResponseFC5")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC5(output_address=10, output_value=1)
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC5.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc6_req():

        print("Test ModbusRequestFC6")

        # Create a Modbus PDU
        req1 = ModbusRequestFC6(output_address=10, output_value=1)
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC6.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc6_rsp():
        # Create a Modbus PDU
        rsp1 = ModbusResponseFC6(output_address=10, output_value=1)
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC6.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc7_req():

        print("Test ModbusRequestFC7")

        # Create a Modbus PDU
        req1 = ModbusRequestFC7()
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC7.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc7_rsp():

        print("Test ModbusResponseFC7")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC7(status=0x01)
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC7.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc8_req():

        print("Test ModbusRequestFC8")

        # Create a Modbus PDU
        req1 = ModbusRequestFC8(sub_func=0x01, subfunc_data=(0x01, 0x02))
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC8.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc8_rsp():

        print("Test ModbusResponseFC8")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC8(sub_func=0x01, subfunc_data=(0x01, 0x02))
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC8.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc15_req():

        print("Test ModbusRequestFC15")

        # Create a Modbus PDU
        req1 = ModbusRequestFC15(start_addr=10, quantity=5, byte_count=1, values=(1,))
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC15.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc15_rsp():

        print("Test ModbusResponseFC15")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC15(start_addr=10, quantity=5)
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC15.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc16_req():

        print("Test ModbusRequestFC16")

        # Create a Modbus PDU
        req1 = ModbusRequestFC16(start_addr=10, quantity=5, byte_count=1, values=(1,))
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC16.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc16_rsp():

        print("Test ModbusResponseFC16")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC16(start_addr=10, quantity=5)
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC16.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc23_req():

        print("Test ModbusRequestFC23")

        # Create a Modbus PDU
        req1 = ModbusRequestFC23(
            read_start_addr=10,
            read_quantity=5,
            write_start_addr=20,
            write_quantity=5,
            write_byte_count=1,
            write_values=(1,),
        )
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC23.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc23_rsp():

        print("Test ModbusResponseFC23")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC23(byte_count=2, values=(0x0001, 0x0002))
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC23.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_pdu_fc43_req():

        print("Test ModbusRequestFC43")

        # Create a Modbus PDU
        req1 = ModbusRequestFC43(mei_type=0x0E, mei_data=(0x01, 0x02))
        print(req1)

        # Serialize the PDU
        stream = req1.serialize()

        # Deserialize the PDU
        req2 = ModbusRequestFC43.deserialize(stream)
        print(req2)

        # Assert the PDUs are equal
        assert req1 == req2

    @staticmethod
    def test_modbus_pdu_fc43_rsp():

        print("Test ModbusResponseFC43")

        # Create a Modbus PDU
        rsp1 = ModbusResponseFC43(mei_type=0x0E, mei_data=(0x01, 0x02))
        print(rsp1)

        # Serialize the PDU
        stream = rsp1.serialize()

        # Deserialize the PDU
        rsp2 = ModbusResponseFC43.deserialize(stream)
        print(rsp2)

        # Assert the PDUs are equal
        assert rsp1 == rsp2

    @staticmethod
    def test_modbus_tcp_request():

        print("Test ModbusTcpRequest")

        # Define header and pdu
        pdu = ModbusRequestFC1(start_addr=10, quantity=5)
        header = ModbusHeader(trans_id=1, prot_id=2, length=len(pdu) + 1, unit_id=4)

        # Assemble a Modbus TCP packet
        msg1 = ModbusTcpRequest(header, pdu)
        print(msg1)

        # Serialize the packet
        stream = msg1.serialize()

        # Deserialize the packet
        msg2 = ModbusTcpRequest.deserialize(stream)
        print(msg2)

        # Assert the packets are equal
        assert msg1 == msg2

    @staticmethod
    def test_modbus_tcp_response():

        print("Test ModbusTcpResponse")

        # Define header and pdu
        pdu = ModbusResponseFC1(byte_count=2, output_status=(0xFF, 0x00))
        header = ModbusHeader(trans_id=1, prot_id=2, length=len(pdu) + 1, unit_id=4)

        # Assemble a Modbus TCP packet
        msg1 = ModbusTcpResponse(header, pdu)
        print(msg1)

        # Serialize the packet
        stream = msg1.serialize()

        # Deserialize the packet
        msg2 = ModbusTcpResponse.deserialize(stream)
        print(msg2)

        # Assert the packets are equal
        assert msg1 == msg2

    @staticmethod
    def test_modbus_rtu_request():

        print("Test ModbusRtuRequest")

        # Define the PDU
        pdu = ModbusRequestFC1(start_addr=10, quantity=5)

        # Assemble a Modbus RTU packet
        msg1 = ModbusRtuRequest(slave_id=1, pdu=pdu)

        # Calculate the CRC over the slave id and pdu (default value is 0xFFFF)
        msg1.calc_crc()
        print(msg1)

        # Serialize the packet
        stream = msg1.serialize()

        # Deserialize the packet
        msg2 = ModbusRtuRequest.deserialize(stream)
        print(msg2)

        # Assert the packets are equal
        assert msg1 == msg2

    @staticmethod
    def test_modbus_rtu_response():

        print("Test ModbusRtuResponse")

        # Define the PDU
        pdu = ModbusResponseFC1(byte_count=2, output_status=(0xFF, 0x00))

        # Assemble a Modbus RTU packet
        msg1 = ModbusRtuResponse(slave_id=1, pdu=pdu)

        # Calculate the CRC over the slave id and pdu (default value is 0xFFFF)
        msg1.calc_crc()
        print(msg1)

        # Serialize the packet
        stream = msg1.serialize()

        # Deserialize the packet
        msg2 = ModbusRtuResponse.deserialize(stream)
        print(msg2)

        # Assert the packets are equal
        assert msg1 == msg2


if __name__ == "__main__":
    unittest.main()
