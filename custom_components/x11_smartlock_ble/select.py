"""Sound-volume HA adapter. Options and commands come from the model."""

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .devices import SmartlockActionEntity


class SoundVolume(SmartlockActionEntity, SelectEntity):
    def __init__(self, data):
        super().__init__(
            data,
            SelectEntityDescription(
                key="beep_volume",
                translation_key="beep_volume",
                entity_category=EntityCategory.CONFIG,
                options=list(data.model.volumes),
            ),
        )
        self._attr_options = list(data.model.volumes)

    @property
    def current_option(self):
        return self._model.volume

    async def async_select_option(self, option):
        await self._execute_setting(lambda: self._model.set_volume(option))
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    if "volume" in data.model.capabilities:
        async_add_entities([SoundVolume(data)])
