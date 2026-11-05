"""A1 Ultra jtmspro/hc7n0urm model. All A1 DP choices live here."""

import base64
import binascii
import time

from ..domain.contracts import LockModel
from ..protocols.tuya_ble.commands.unlock_check import CheckTokenUnlock
from ..protocols.tuya_ble.commands.write import ByteWrite, FixedAction
from ..protocols.tuya_ble.const import PointType as PointType
from ..protocols.tuya_ble.dialects.fd50 import FD50PayloadDecoder
from ..protocols.tuya_ble.exceptions import ProtocolError


class A1UltraModel(LockModel):
    product_id = "hc7n0urm"
    category = "jtmspro"
    protocol_id = "tuya_ble_fd50"
    name = "A1 Ultra"
    manufacturer = "Tuya"
    capabilities = frozenset({"volume", "direction", "calibrate", "battery"})
    credential_fields = ("uuid", "local_key", "device_id", "ble_unlock_check")
    volumes = ("mute", "normal")
    battery_levels = ("high", "medium", "low", "poweroff")

    @classmethod
    def validate_credentials(cls, values):
        if not all(
            isinstance(values.get(key), str)
            and 0 < len(values[key]) <= 512
            and values[key].isascii()
            for key in cls.credential_fields
        ):
            return False
        if len(values.get("local_key", "")) < 6:
            return False
        if "ble_unlock_check" in cls.credential_fields:
            try:
                return (
                    len(base64.b64decode(values["ble_unlock_check"], validate=True))
                    >= 19
                )
            except (ValueError, TypeError, binascii.Error):
                return False
        return True

    def __init__(self, protocol, credentials):
        self.protocol = protocol
        self.points = protocol.datapoints
        self.decoder = FD50PayloadDecoder(
            self.points, protocol.publish, {9, 31, 68, 78}
        )
        protocol.payload_decoder = self.decoder.parse
        self.lock_command = FixedAction(ByteWrite(46, bool, {True}), True)
        self.unlock_command = CheckTokenUnlock(credentials)
        self.volume_command = ByteWrite(31, int, {0, 1})
        self.direction_command = ByteWrite(78, bool, {False, True})
        self.calibrate_command = FixedAction(ByteWrite(68, int, {0}), 0)

    async def lock(self):
        await self.lock_command.execute(self.protocol)

    async def unlock(self):
        await self.unlock_command.execute(self.protocol)

    @property
    def lock_report(self):
        # 118 is the decoder's internal slot, not a physical-position DP ID.
        # Only the decoded DP47 boolean is a supported lock-status report.
        point = self.points[118]
        if (
            point is not None
            and point.flags == 47
            and type(point.value) is int
            and point.value in (0, 1)
        ):
            return point.timestamp, not bool(point.value)
        return None

    @property
    def volume(self):
        point = self.points[31]
        return (
            self.volumes[point.value]
            if point and type(point.value) is int and point.value in (0, 1)
            else None
        )

    @property
    def reversed_direction(self):
        point = self.points[78]
        return bool(point.value) if point else None

    @property
    def battery(self):
        point = self.points[9]
        return (
            self.battery_levels[point.value]
            if point and type(point.value) is int and 0 <= point.value < 4
            else None
        )

    async def set_volume(self, volume):
        if volume not in self.volumes:
            raise ProtocolError("Unsupported sound volume")
        await self.volume_command.execute(self.protocol, self.volumes.index(volume))
        self._publish_setting(31, self.volumes.index(volume), PointType.DT_ENUM)

    async def set_direction(self, reversed_direction):
        if type(reversed_direction) is not bool:
            raise ProtocolError("Direction must be boolean")
        await self.direction_command.execute(self.protocol, reversed_direction)
        self._publish_setting(78, reversed_direction, PointType.DT_BOOL)

    async def calibrate(self):
        await self.calibrate_command.execute(self.protocol)

    def _publish_setting(self, point_id, value, kind):
        self.points._update_from_device(point_id, time.time(), 0, kind, value)
        self.protocol.publish([self.points[point_id]])
