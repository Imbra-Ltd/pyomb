# encoding: utf-8
from __future__ import print_function
from __future__ import unicode_literals

################################################################################

# ModBus protocol parameters

# Define the OMB function codes (FC)
FC_1 = 1  # Read coils
FC_2 = 2  # Read input discretes
FC_3 = 3  # Read multiple registers
FC_4 = 4  # Read input registers
FC_5 = 5  # Write coil
FC_6 = 6  # Write single register
FC_7 = 7  # Read exception status
FC_15 = 15  # Force multiple coils
FC_16 = 16  # Write multiple registers
FC_22 = 22  # Mask Write Register
FC_23 = 23  # Read/Write multiple registers
FC_43 = 43  # Read Device Identification

# Define the Open Modbus (OMB) Exceptions
OMB_EXCEPTION_ILLEGAL_FUNCTION = 0x01
OMB_EXCEPTION_ILLEGAL_DATA_ADDRESS = 0x02
OMB_EXCEPTION_ILLEGAL_DATA_VALUE = 0x03
OMB_EXCEPTION_SLAVE_DEVICE_FAILURE = 0x04
OMB_EXCEPTION_ACKNOWLEDGE = 0x05
OMB_EXCEPTION_SLAVE_DEVICE_BUSY = 0x06
OMB_EXCEPTION_MEMORY_PARITY_ERROR = 0x08
OMB_EXCEPTION_GATEWAY_PATH_UNAVAILABLE = 0x0A
OMB_EXCEPTION_GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND = 0x0B

################################################################################
