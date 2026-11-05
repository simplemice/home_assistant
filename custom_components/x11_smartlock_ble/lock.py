"""Optimistic command control; the separate sensor carries device status."""

from homeassistant.components.lock import LockEntity, LockEntityDescription

from .const import DOMAIN
from .devices import SmartlockActionEntity


class LockControl(SmartlockActionEntity, LockEntity):
    _attr_assumed_state = True

    def __init__(self, data):
        super().__init__(
            data,
            LockEntityDescription(key="manual_lock", translation_key="manual_lock"),
        )

    @property
    def is_locked(self):
        return self._actions.locked

    @property
    def extra_state_attributes(self):
        return {
            "state_source": "command_intent",
            "bluetooth_connected": self.coordinator.connected,
            "command_pending": self._actions.pending,
        }

    async def async_lock(self, **kwargs):
        await self._execute_action(lambda: self._actions.set_locked(True))

    async def async_unlock(self, **kwargs):
        await self._execute_action(lambda: self._actions.set_locked(False))

    async def async_toggle(self, **kwargs):
        await self._execute_action(self._actions.toggle)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([LockControl(hass.data[DOMAIN][entry.entry_id])])
