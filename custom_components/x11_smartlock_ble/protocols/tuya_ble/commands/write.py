"""Reusable single-byte V4 writes; models supply IDs and allowed values."""

from ..exceptions import ProtocolError


class ByteWrite:
    def __init__(self, point_id, value_type, allowed):
        self.point_id = point_id
        self.value_type = value_type
        self.allowed = allowed

    def payload(self, value):
        if type(value) is not self.value_type or value not in self.allowed:
            raise ProtocolError("Unsupported command value")
        return (
            b"\x00\x00\x00\x00\x01"
            + bytes([self.point_id])
            + b"\x00\x00\x01"
            + bytes([int(value)])
        )

    async def execute(self, protocol, value):
        await protocol.send_command(self.payload(value))


class FixedAction:
    def __init__(self, write, value):
        self.write = write
        self.value = value

    async def execute(self, protocol):
        await self.write.execute(protocol, self.value)
