"""X11 jtmspro/gozpr1op model (Tuya Q7_BLE).

Schema from the Tuya cloud (Query Properties) for this product:
  DP9 battery_state (enum), DP31 beep_volume (enum), DP19 unlock_ble,
  DP70 check_code_set (raw), DP71 ble_unlock_check (raw, NO cloud value).
The cloud schema omits DP46/DP47, but the lock does report DP47 (bool) over
BLE, so lock state is read from it and DP46 is tried for locking (unverified).

Remote unlock uses the check-token command shared with the other jtmspro FD50
locks. Its token (`ble_unlock_check`) is entered in the config / options and is
replaced by any newer DP71 the lock reports over BLE (the Tuya app obtains it
while unlocking, so the cloud device log shows it after an app unlock).
"""

import base64
import binascii
import logging
import time

from ..domain.contracts import LockModel
from ..protocols.tuya_ble.commands.unlock_check import CheckTokenUnlock
from ..protocols.tuya_ble.commands.write import ByteWrite, FixedAction
from ..protocols.tuya_ble.dialects.fd50 import FD50PayloadDecoder
from ..protocols.tuya_ble.exceptions import ProtocolError
from ..protocols.tuya_ble.reports import Report, decode_report
from .a1_ultra import A1UltraModel

_LOGGER = logging.getLogger(__name__)

CHECK_DP = 71

# The lock re-engages by itself this long after every unlock (not configurable).
RELOCK_SECONDS = 5

# Unlock-record DPs (cloud schema: Integer 0..999 = user / credential ID).
UNLOCK_METHODS = {
    12: "fingerprint",
    13: "password",
    14: "dynamic_password",
    15: "card",
    19: "bluetooth",
    55: "temporary_password",
}
UNLOCK_EVENT_TYPES = list(UNLOCK_METHODS.values())
# Ignore timestamped (history) records older than this many seconds.
MAX_EVENT_AGE = 120
MIN_CHECK_LEN = 19


class X11Model(LockModel):
    product_id = "gozpr1op"
    category = "jtmspro"
    protocol_id = "tuya_ble_fd50"
    name = "X11"
    manufacturer = "Tuya"
    capabilities = frozenset({"battery", "unlock_events"})
    credential_fields = ("uuid", "local_key", "device_id", "ble_unlock_check")
    optional_credential_fields = frozenset({"ble_unlock_check"})
    battery_levels = ("high", "medium", "low", "poweroff")

    @classmethod
    def validate_credentials(cls, values):
        for key in ("uuid", "local_key", "device_id"):
            value = values.get(key)
            if not (isinstance(value, str) and 0 < len(value) <= 512 and value.isascii()):
                return False
        if len(values["local_key"]) < 6:
            return False
        check = values.get("ble_unlock_check")
        if check:
            try:
                return len(base64.b64decode(check, validate=True)) >= MIN_CHECK_LEN
            except (ValueError, TypeError, binascii.Error):
                return False
        return True

    def __init__(self, protocol, credentials):
        self.protocol = protocol
        self.points = protocol.datapoints
        self.credentials = credentials
        # The X11 does not tag its status answers with sub-type 1; accept any live
        # report, otherwise the heartbeat times out and the link is recycled.
        protocol.status_report_subtypes = None
        self.decoder = FD50PayloadDecoder(self.points, protocol.publish, {9, 28, 31})
        protocol.payload_decoder = self._parse
        self.check_listener = None  # set by the HA adapter to persist new codes
        self._event_listeners = []
        self._unlock_listeners = []
        self._derived = None  # (timestamp, locked) from commands and unlock records
        self.sticky_lock_state = True  # DP47 is pushed rarely: keep the last state
        self._seen_events = []
        self._last_battery = None
        self.lock_command = FixedAction(ByteWrite(46, bool, {True}), True)
        self.unlock_command = CheckTokenUnlock(credentials)

    def _parse(self, data):
        """Capture DP71 whenever the lock reports it, then decode as usual."""
        if not isinstance(data, Report):
            self._emit_unlock_events(data)
        try:
            report = data if isinstance(data, Report) else decode_report(data)
        except ValueError:
            return
        for point_id, kind, raw in report.points:
            _LOGGER.debug(
                "hdr %s DP %s type %s len %s value %s%s",
                report.header.hex(),
                point_id,
                kind,
                len(raw),
                raw.hex(),
                " (timestamped)" if report.source_timestamp is not None else "",
            )
            if point_id == CHECK_DP and kind == 0 and len(raw) >= MIN_CHECK_LEN:
                # Newest report wins: the lock may issue a fresh code after use.
                value = base64.b64encode(raw).decode()
                if value != self.credentials.ble_unlock_check:
                    self.credentials.ble_unlock_check = value
                    _LOGGER.debug("Captured new unlock check from DP71")
                    if self.check_listener is not None:
                        self.check_listener(value)
        self.decoder.parse(report)

    def subscribe_events(self, listener):
        """Call listener(event_type, attributes) for every unlock record."""
        self._event_listeners.append(listener)
        return lambda: self._event_listeners.remove(listener)

    def subscribe_unlocks(self, listener):
        """Call listener() whenever the lock is (assumed) unlocked."""
        self._unlock_listeners.append(listener)
        return lambda: self._unlock_listeners.remove(listener)

    def _emit_unlock_events(self, data):
        """Find unlock-record DPs in live and timestamped packets.

        Timestamped packets are the lock's event log; the strict V4 decoder
        rejects the X11's variant, so records are located by their fixed
        shape (dp id, type 2, length 4, 32-bit value) and de-duplicated.
        """
        if len(data) < 12:
            return
        raw = bytes(data)
        if raw in self._seen_events:
            return
        self._seen_events = (self._seen_events + [raw])[-50:]
        found = []
        for pos in range(7, len(raw) - 7):
            dp = raw[pos]
            if dp in UNLOCK_METHODS and raw[pos + 1] == 2 and raw[pos + 2 : pos + 4] == b"\x00\x04":
                found.append((dp, int.from_bytes(raw[pos + 4 : pos + 8], "big")))
        if not found:
            _LOGGER.debug("No unlock record in packet: %s", raw.hex())
            return
        event_time = None
        try:
            event_time = decode_report(raw, timestamped=True).source_timestamp
        except ValueError:
            pass
        if event_time is not None and abs(time.time() - event_time) > MAX_EVENT_AGE:
            _LOGGER.debug("Skipping old unlock record (%s)", raw.hex())
            return
        for dp, value in found:
            _LOGGER.debug("Unlock record: %s id %s", UNLOCK_METHODS[dp], value)
            self._set_derived(False)
            for listener in tuple(self._event_listeners):
                listener(UNLOCK_METHODS[dp], {"user_id": value, "dp": dp})

    @property
    def has_unlock_check(self):
        return bool(self.credentials.ble_unlock_check)

    def _set_derived(self, locked):
        self._derived = (time.time(), locked)
        self.protocol.publish([])  # re-evaluate the reported lock status
        if not locked:
            for listener in tuple(self._unlock_listeners):
                listener()

    async def lock(self):
        raise ProtocolError("The lock re-engages by itself; remote lock is not supported")

    async def unlock(self):
        if not self.has_unlock_check:
            raise ProtocolError(
                "No ble_unlock_check yet: the lock has not reported DP71. "
                "Press Status / wake the lock, or enter the value in the config"
            )
        await self.unlock_command.execute(self.protocol)
        self._set_derived(False)

    # The lock relocks itself RELOCK_SECONDS after any unlock, so "unlocked" is
    # only ever a short window that starts with our unlock or an unlock record.
    @property
    def unlocked(self):
        return (
            self._derived is not None
            and not self._derived[1]
            and time.time() - self._derived[0] < RELOCK_SECONDS
        )

    @property
    def lock_report(self):
        if self._derived is None:
            return None
        stamp, locked = self._derived
        if not locked and time.time() - stamp >= RELOCK_SECONDS:
            return stamp + RELOCK_SECONDS, True
        return stamp, locked

    @property
    def battery(self):
        """Keep the last valid category; the lock also sends DP9 in other forms."""
        point = self.points[9]
        if point and type(point.value) is int:
            if 0 <= point.value < len(self.battery_levels):
                self._last_battery = self.battery_levels[point.value]
            else:
                _LOGGER.warning(
                    "Unexpected battery DP9 value %r (type %s)", point.value, point.type
                )
        return self._last_battery
