def validate_read_request(self):

    # Validate the starting address type
    if not isinstance(self.starting_address, int):
        raise ValueError("Starting address must be an integer")

    # Validate range of the starting address
    elif self.starting_address < 0 or self.starting_address > 0xFFFF:
        raise ValueError("Starting address must be between 0 and 0xFFFF")

    # Validate the quantity type
    if not isinstance(self.quantity, int):
        raise ValueError("Quantity must be an integer")

    # Validate the quantity range
    elif self.quantity < 0 or self.quantity > 2000:
        raise ValueError("Quantity must be between 0 and 0x7D0")


def validate_read_response(self):

    # Validate the type of byte count
    if not isinstance(self.byte_count, int):
        raise ValueError("Byte count must be an integer")

    # Validate that byte count is in range
    elif self.byte_count < 0 or self.byte_count > 0xFF:
        raise ValueError("Byte count must be between 0 and 0xFF")

    # Validate that input status is an iterable
    elif not isinstance(self.output_status, (list, tuple, set)):
        raise ValueError("Input status must be an iterable")

    # Validate the length of the input status
    elif len(self.output_status) != self.byte_count:
        raise ValueError("Input status count must match byte count")

    # Validate the type of input status elements
    elif not all([isinstance(i, int) for i in self.output_status]):
        raise ValueError("Input status must be integers")

    # Check that none of the input status values are out of range
    elif any([i < 0 or i > 0xFF for i in self.output_status]):
        raise ValueError("Input status values must be between 0 and 0xFF")
