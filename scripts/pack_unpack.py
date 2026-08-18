import struct


def pack_data(format_string, *data):
    try:
        return struct.pack(format_string, *data)
    except Exception as e:
        raise Exception("Error serializing data: {0}".format(e))


def unpack_data(format_string, stream):
    try:
        return struct.unpack(format_string, stream)
    except Exception as e:
        raise Exception("Error deserializing data: {0}".format(e))
