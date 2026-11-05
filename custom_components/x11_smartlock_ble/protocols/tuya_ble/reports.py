"""Strict Tuya V4 framing; never search inside raw credential values."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Report:
    header: bytes
    points: tuple[tuple[int, int, bytes], ...]
    source_timestamp: float | None = None

    @property
    def acknowledgement(self):
        return self.header + b"\x00"


def decode_report(data: bytes, *, timestamped=False):
    if len(data) < 11 or data[0] != 0:
        raise ValueError("Unsupported V4 report header")
    pos = 7
    timestamp = None
    if timestamped:
        if data[7] == 0:
            pos = 21
            if len(data) < pos or not data[8:pos].isdigit():
                raise ValueError("Invalid report timestamp")
            timestamp = int(data[8:pos]) / 1000
        elif data[7] == 1:
            pos = 12
            if len(data) < pos:
                raise ValueError("Truncated report timestamp")
            timestamp = int.from_bytes(data[8:pos], "big")
        else:
            raise ValueError("Unsupported timestamp format")
    points = []
    while pos < len(data):
        if pos + 4 > len(data):
            raise ValueError("Truncated datapoint header")
        point_id, kind = data[pos : pos + 2]
        size = int.from_bytes(data[pos + 2 : pos + 4], "big")
        pos += 4
        if kind > 5 or pos + size > len(data):
            raise ValueError("Invalid datapoint length or type")
        value = data[pos : pos + size]
        if (kind in (1, 4) and size != 1) or (kind == 2 and size != 4):
            raise ValueError("Invalid scalar length")
        if kind == 1 and value not in (b"\x00", b"\x01"):
            raise ValueError("Invalid boolean")
        points.append((point_id, kind, value))
        pos += size
    if not points:
        raise ValueError("Empty report")
    return Report(data[:7], tuple(points), timestamp)
