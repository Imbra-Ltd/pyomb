"""A port double: what a caller's serial port looks like from the RTU stream."""


class FakePort:
    """Replays a scripted inbox and records every read size and every write.

    read() hands back what is left up to size, so an exhausted inbox reads as
    the port's timeout elapsing -- the empty read the stream treats as
    silence. per_read caps one read at that many bytes, which is a slow device
    seen through a per-call timeout. echo puts each frame written at the front
    of the inbox, ahead of any reply, the way an RS-485 transceiver echoes.
    failure is raised from the next read instead of answering it.
    """

    def __init__(self, inbox=b"", per_read=None, echo=False, failure=None):
        self.inbox = bytearray(inbox)
        self.reads = []
        self.writes = []
        self.per_read = per_read
        self.echo = echo
        self.failure = failure

    def read(self, size):
        self.reads.append(size)

        if self.failure is not None:
            failure, self.failure = self.failure, None
            raise failure

        if self.per_read is not None:
            size = min(size, self.per_read)

        chunk = bytes(self.inbox[:size])
        del self.inbox[:size]

        return chunk

    def write(self, data):
        self.writes.append(bytes(data))

        if self.echo:
            self.inbox[0:0] = data

        return len(data)


class ShortWritingPort(FakePort):
    """Writes one byte fewer than it was given, which no port should."""

    def write(self, data):
        super().write(data)

        return len(data) - 1
