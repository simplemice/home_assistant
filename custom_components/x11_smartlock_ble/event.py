"""Unlock event entity: fires with the unlock method and credential ID."""

from homeassistant.components.event import EventEntity, EventEntityDescription

from .const import DOMAIN
from .devices import SmartlockEntity
from .models.x11 import UNLOCK_EVENT_TYPES


class UnlockEvent(SmartlockEntity, EventEntity):
    """Fires on fingerprint, PIN, one-time code, card, temporary PIN and app unlocks."""

    _attr_event_types = UNLOCK_EVENT_TYPES

    def __init__(self, data):
        super().__init__(
            data,
            EventEntityDescription(
                key="unlock_event", translation_key="unlock_event", icon="mdi:key"
            ),
        )

    @property
    def available(self):
        # Records arrive whenever the lock is connected; keep the entity usable
        # between connections so automations are not flagged unavailable.
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._model.subscribe_events(self._fire))

    def _fire(self, event_type, attributes):
        self._trigger_event(event_type, attributes)
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    if "unlock_events" in data.model.capabilities:
        async_add_entities([UnlockEvent(data)])
