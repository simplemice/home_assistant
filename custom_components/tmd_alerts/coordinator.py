from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import fetch_warnings
from .const import (
    API_URL,
    CONF_LANGUAGE,
    CONF_UID,
    CONF_UKEY,
    DEFAULT_LANGUAGE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UID,
    DEFAULT_UKEY,
    DOMAIN,
    LANG_AUTO,
    LANG_EN,
    LANG_TH,
)

_LOGGER = logging.getLogger(__name__)


class TMDCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._entry = entry
        self.uid = entry.data.get(CONF_UID, DEFAULT_UID)
        self.ukey = entry.data.get(CONF_UKEY, DEFAULT_UKEY)

    @property
    def language(self) -> str:
        """Return active language: auto-detects from HA config unless overridden."""
        configured = self._entry.options.get(
            CONF_LANGUAGE,
            self._entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
        )
        if configured == LANG_AUTO:
            ha_lang = (self.hass.config.language or "").lower()
            return LANG_TH if ha_lang.startswith("th") else LANG_EN
        return configured

    async def _async_update_data(self) -> list[dict]:
        try:
            return await fetch_warnings(self.hass, API_URL, self.uid, self.ukey)
        except Exception as err:
            raise UpdateFailed(f"Error fetching TMD warnings: {err}") from err
