import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    API_URL,
    CONF_LANGUAGE,
    CONF_UID,
    CONF_UKEY,
    DEFAULT_LANGUAGE,
    DEFAULT_UID,
    DEFAULT_UKEY,
    DOMAIN,
    LANG_AUTO,
    LANG_EN,
    LANG_TH,
)

_LANGUAGE_OPTIONS = [
    {"value": LANG_AUTO, "label": "Auto (follow HA language)"},
    {"value": LANG_EN, "label": "English"},
    {"value": LANG_TH, "label": "ภาษาไทย (Thai)"},
]


class TMDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            uid = user_input.get(CONF_UID) or DEFAULT_UID
            ukey = user_input.get(CONF_UKEY) or DEFAULT_UKEY
            language = user_input.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

            try:
                session = async_get_clientsession(self.hass)
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(
                    API_URL,
                    params={"uid": uid, "ukey": ukey},
                    timeout=timeout,
                ) as resp:
                    if resp.status != 200:
                        errors["base"] = "cannot_connect"
                    else:
                        return self.async_create_entry(
                            title="Thailand Weather Alerts (TMD)",
                            data={
                                CONF_UID: uid,
                                CONF_UKEY: ukey,
                                CONF_LANGUAGE: language,
                            },
                        )
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Optional(CONF_UID, default=DEFAULT_UID): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_UKEY, default=DEFAULT_UKEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): SelectSelector(
                SelectSelectorConfig(
                    options=_LANGUAGE_OPTIONS,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return TMDOptionsFlow()


class TMDOptionsFlow(config_entries.OptionsFlow):
    """Allow changing language after setup via the Configure button."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_lang = self.config_entry.options.get(
            CONF_LANGUAGE,
            self.config_entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
        )

        schema = vol.Schema({
            vol.Required(CONF_LANGUAGE, default=current_lang): SelectSelector(
                SelectSelectorConfig(
                    options=_LANGUAGE_OPTIONS,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
