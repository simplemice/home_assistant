"""Device-reported lock status, battery category and BLE signal strength."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.helpers.entity import EntityCategory

from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .models.x11 import RELOCK_SECONDS, UNLOCK_EVENT_TYPES
from .devices import SmartlockEntity


class LockStatus(SmartlockEntity, SensorEntity):
    """Locked, except for RELOCK_SECONDS after an unlock (the lock relocks itself)."""

    def __init__(self, data):
        super().__init__(
            data,
            SensorEntityDescription(
                key="reported_lock_state",
                translation_key="reported_lock_state",
                device_class=SensorDeviceClass.ENUM,
                options=["locked", "unlocked"],
            ),
        )
        self._attr_options = ["locked", "unlocked"]
        self._cancel_relock = None

    @property
    def available(self):
        return True

    @property
    def native_value(self):
        return "unlocked" if self._model.unlocked else "locked"

    @property
    def icon(self):
        return "mdi:lock-open" if self._model.unlocked else "mdi:lock"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self._model.subscribe_unlocks(self._on_unlock))
        self.async_on_remove(self._stop_timer)

    def _stop_timer(self):
        if self._cancel_relock is not None:
            self._cancel_relock()
            self._cancel_relock = None

    def _on_unlock(self, *_):
        self._stop_timer()
        self.async_write_ha_state()
        self._cancel_relock = async_call_later(
            self.hass, RELOCK_SECONDS + 0.5, self._relocked
        )

    @callback
    def _relocked(self, _now):
        self._cancel_relock = None
        self.async_write_ha_state()


class LastUnlock(SmartlockEntity, SensorEntity, RestoreEntity):
    """How the lock was last opened: fingerprint, PIN, card, app, ...

    Keeps its value across restarts; user_id and time are attributes.
    """

    def __init__(self, data):
        super().__init__(
            data,
            SensorEntityDescription(
                key="last_unlock_method",
                translation_key="last_unlock_method",
                device_class=SensorDeviceClass.ENUM,
                options=list(UNLOCK_EVENT_TYPES),
                icon="mdi:key-variant",
            ),
        )
        self._attr_options = list(UNLOCK_EVENT_TYPES)
        self._method = None
        self._attrs = {}

    @property
    def available(self):
        # Last known value stays visible while the lock sleeps / is out of range.
        return True

    @property
    def native_value(self):
        return self._method

    @property
    def extra_state_attributes(self):
        return self._attrs

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            if last.state in UNLOCK_EVENT_TYPES:
                self._method = last.state
                self._attrs = {
                    k: v for k, v in last.attributes.items() if k in ("user_id", "dp", "at")
                }
        self.async_on_remove(self._model.subscribe_events(self._on_unlock))

    def _on_unlock(self, event_type, attributes):
        self._method = event_type
        self._attrs = {**attributes, "at": dt_util.utcnow().isoformat()}
        self.async_write_ha_state()


class BatteryLevel(SmartlockEntity, SensorEntity, RestoreEntity):
    """Battery category. Keeps the last value while the lock sleeps or is out of range."""

    def __init__(self, data):
        super().__init__(
            data,
            SensorEntityDescription(
                key="battery_state",
                translation_key="battery_state",
                device_class=SensorDeviceClass.ENUM,
                entity_category=EntityCategory.DIAGNOSTIC,
                options=list(data.model.battery_levels),
                icon="mdi:battery",
            ),
        )
        self._attr_options = list(data.model.battery_levels)
        self._restored = None

    @property
    def available(self):
        return True

    @property
    def native_value(self):
        return self._model.battery or self._restored

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            if last.state in self._attr_options:
                self._restored = last.state


class BLESignal(SmartlockEntity, SensorEntity):
    def __init__(self, data):
        super().__init__(
            data,
            SensorEntityDescription(
                key="signal_strength",
                translation_key="signal_strength",
                device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                entity_registry_enabled_default=False,
            ),
        )

    @property
    def native_value(self):
        return self._device.rssi


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [BLESignal(data), LockStatus(data)]
    if "battery" in data.model.capabilities:
        entities.append(BatteryLevel(data))
    if "unlock_events" in data.model.capabilities:
        entities.append(LastUnlock(data))
    async_add_entities(entities)
