"""Config flow for LEX TH."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.update_coordinator import UpdateFailed

from . import async_fetch_parcel
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_LANGUAGE,
    CONF_TRACKING_NUMBER,
    DEFAULT_LANGUAGE,
    DOMAIN,
    LANGUAGES,
    TRACKING_NUMBER_RE,
)


class LexThConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle adding a parcel."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        number = ""
        language = "th" if self.hass.config.language == "th" else DEFAULT_LANGUAGE
        if user_input is not None:
            number = user_input[CONF_TRACKING_NUMBER].strip().upper()
            language = user_input[CONF_LANGUAGE]
            if not TRACKING_NUMBER_RE.match(number):
                errors["base"] = "invalid_tracking_number"
            else:
                await self.async_set_unique_id(number)
                self._abort_if_unique_id_configured()
                try:
                    await async_fetch_parcel(self.hass, number)
                except UpdateFailed:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=number,
                        data={CONF_TRACKING_NUMBER: number, CONF_LANGUAGE: language},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TRACKING_NUMBER, default=number): str,
                    vol.Required(CONF_LANGUAGE, default=language): SelectSelector(
                        SelectSelectorConfig(
                            options=LANGUAGES,
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="language",
                        )
                    ),
                }
            ),
            errors=errors,
        )
