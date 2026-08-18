class Modbus(object):
    def __init__(self, protocol="RTU"):
        self.protocol = protocol

    @classmethod
    def get_protocol(self):
        return self.protocol

    @classmethod
    def set_protocol(self, protocol):
        self.protocol = protocol

    @classmethod
    def read_coils(cls, start_address, quantity):
        pass

    @classmethod
    def read_discrete_inputs(cls, start_address, quantity):
        pass

    @classmethod
    def read_holding_registers(cls, start_address, quantity):
        pass

    @classmethod
    def read_input_registers(cls, start_address, quantity):
        pass

    @staticmethod
    def write_single_coil(cls, address, value):
        pass

    @classmethod
    def write_single_register(cls, address, value):
        pass

    @classmethod
    def write_multiple_coils(cls, start_address, quantity, values):
        pass

    @classmethod
    def write_multiple_registers(cls, start_address, quantity, values):
        pass

    @classmethod
    def mask_write_register(cls, address, and_mask, or_mask):
        pass

    @classmethod
    def read_write_multiple_registers(cls, read_address, read_quantity, write_address, write_quantity, values):
        pass

    @classmethod
    def read_device_identification(cls, object_id, object_length):
        pass
