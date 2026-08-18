import socket


class StubSocket(socket.socket):
    # Trans-ID 0, Prot-ID 0, Length 4, Unit-ID 1, PDU b'\x01\x02\x03'.
    # The length field counts the unit identifier plus the PDU, so a 3-byte
    # PDU is declared as 4.
    DATA = b"\x00\x00\x00\x00\x00\x04\x01\x01\x02\x03"

    def __init__(self):
        self.sent_data = []
        self.recv_data = self.DATA

    def connect(self, address):
        pass  # Stub method does nothing

    def send(self, data):
        self.sent_data.append(data)

    def recv(self, buffer_size):
        result = self.recv_data[:buffer_size]
        self.recv_data = self.recv_data[buffer_size:]
        return result

    def close(self):
        pass  # Stub method does nothing

    def flush(self):
        self.sent_data[:] = []

    def reset(self):
        self.sent_data[:] = []
        self.recv_data = self.DATA


class LoopbackSocket(object):
    """Records what is written and replays a queue of prepared frames.

    Unlike StubSocket this does not subclass socket.socket, so it can be
    handed to a client without opening a real descriptor.
    """

    def __init__(self, inbox=b""):
        self.sent = []
        self.inbox = inbox

    def send(self, data):
        self.sent.append(data)
        return len(data)

    def recv(self, buffer_size):
        chunk = self.inbox[:buffer_size]
        self.inbox = self.inbox[buffer_size:]
        return chunk

    def frame(self):
        """Everything written, as one buffer."""
        return b"".join(self.sent)
