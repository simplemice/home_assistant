"""Rotation-direction HA adapter. Wire mapping belongs to the model."""

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .devices import SmartlockActionEntity


class RotationDirection(SmartlockActionEntity, SwitchEntity):
    def __init__(self, data):
        super().__init__(
            data,
            SwitchEntityDescription(
                key="change_direction",
                translation_key="change_direction",
                entity_category=EntityCategory.CONFIG,
                icon="mdi:rotate-3d-variant",
            ),
        )

    @property
    def is_on(self):
        return self._model.reversed_direction

    async def async_turn_on(self, **kwargs):
        await self._execute_setting(lambda: self._model.set_direction(True))

    async def async_turn_off(self, **kwargs):
        await self._execute_setting(lambda: self._model.set_direction(False))


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    if "direction" in data.model.capabilities:
        async_add_entities([RotationDirection(data)])
