"""Received point values; independent of Home Assistant and transport."""

from dataclasses import dataclass


@dataclass
class DataPoint:
    id: int
    timestamp: float
    flags: int
    type: object
    value: object


class DataPoints:
    def __init__(self):
        self._values = {}

    def __getitem__(self, key):
        return self._values.get(key)

    def _update_from_device(self, dp_id, timestamp, flags, kind, value):
        self._values[dp_id] = DataPoint(dp_id, timestamp, flags, kind, value)
