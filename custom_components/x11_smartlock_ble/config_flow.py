"""Discover nearby locks, collect owner credentials, verify a read-only session."""

from __future__ import annotations

import asyncio
import base64
import binascii
from types import SimpleNamespace

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_HOLD_TIME,
    CONF_KEEP_CONNECTED,
    CONF_POLL_INTERVAL,
    CONF_WAIT_FOR_RECONNECT,
    DOMAIN,
)
from .keyman import LocalCredentialProvider
from .registry import MODELS, create_connection, discovery_services


class SmartlockConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._devices = {}
        self._address = None
        self._product_id = next(iter(MODELS))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmartlockOptionsFlow()

    async def async_step_bluetooth(self, discovery_info):
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._devices[discovery_info.address] = discovery_info
        self.context["title_placeholders"] = {
            "name": f"FD50 {discovery_info.address[-8:]}"
        }
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        current = self._async_current_ids()
        for info in bluetooth.async_discovered_service_info(self.hass):
            if info.address not in current and discovery_services().intersection(
                set(info.service_data or {}) | set(info.service_uuids or [])
            ):
                self._devices[info.address] = info
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            if address not in self._devices:
                # Manual entry: the lock may not advertise a known service.
                ble_device = bluetooth.async_ble_device_from_address(
                    self.hass, address, True
                )
                if ble_device is None:
                    errors["base"] = "not_visible"
                else:
                    self._devices[address] = SimpleNamespace(
                        device=ble_device, name=address
                    )
            if not errors:
                self._address = address
                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return await self.async_step_model()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": a, "label": f"{i.name} ({a})"}
                                for a, i in self._devices.items()
                            ],
                            custom_value=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_model(self, user_input=None):
        if user_input is not None:
            self._product_id = user_input["product_id"]
            return await self.async_step_credentials()
        if len(MODELS) == 1:
            self._product_id = next(iter(MODELS))
            return await self.async_step_credentials()
        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {
                    vol.Required("product_id"): vol.In(
                        {key: cls.name for key, cls in MODELS.items()}
                    )
                }
            ),
        )

    async def async_step_credentials(self, user_input=None):
        errors = {}
        model = MODELS[self._product_id]
        if user_input is not None:
            values = {
                key: user_input.get(key, "").strip() for key in model.credential_fields
            }
            if not model.validate_credentials(values):
                errors["base"] = "invalid_credentials"
            else:
                values["product_id"] = model.product_id
                values["category"] = model.category
                values["device_name"] = model.name
                values["product_name"] = model.name
                values["product_model"] = model.name
                data = {CONF_ADDRESS: self._address, "credentials": values}
                provider = LocalCredentialProvider(self.hass, data)
                credentials = await provider.get_device_credentials(self._address)
                device = None
                try:
                    device, _ = create_connection(
                        credentials, provider, self._devices[self._address].device
                    )
                    device.managed_connection = True
                    async with asyncio.timeout(90):
                        await device.initialize()
                        await device.update()
                except Exception:
                    errors["base"] = "cannot_connect"
                finally:
                    if device is not None:
                        try:
                            await device.stop()
                        except Exception:
                            errors["base"] = "cannot_connect"
                if not errors:
                    return self.async_create_entry(
                        title=f"{model.name} {self._address.replace(':', '')[-6:]}",
                        data=data,
                        options={CONF_KEEP_CONNECTED: True},
                    )
        # Legacy file support is optional; never read another integration's data.
        # Only non-secret model selection receives a default; secrets are never echoed.
        fields = {}
        for key in model.credential_fields:
            optional = key in getattr(model, "optional_credential_fields", ())
            fields[(vol.Optional if optional else vol.Required)(key)] = selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            )
        return self.async_show_form(
            step_id="credentials", data_schema=vol.Schema(fields), errors=errors
        )


class SmartlockOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._persistent = user_input[CONF_KEEP_CONNECTED]
            self._unlock_check = (user_input.get("ble_unlock_check") or "").strip()
            if self._unlock_check:
                try:
                    valid = len(base64.b64decode(self._unlock_check, validate=True)) >= 19
                except (ValueError, TypeError, binascii.Error):
                    valid = False
                if not valid:
                    return self._show_init({"ble_unlock_check": "invalid_unlock_check"})
            if self._persistent:
                return await self.async_step_persistent()
            return await self.async_step_on_demand()
        return self._show_init()

    def _unlock_check_option(self):
        out = {}
        if self._unlock_check:
            out["ble_unlock_check"] = self._unlock_check
        return out

    def _show_init(self, errors=None):
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_KEEP_CONNECTED,
                        default=self.config_entry.options.get(
                            CONF_KEEP_CONNECTED, True
                        ),
                    ): bool,
                    vol.Optional("ble_unlock_check"): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
        )

    async def async_step_persistent(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    **self.config_entry.options,
                    **self._unlock_check_option(),
                    CONF_KEEP_CONNECTED: True,
                    CONF_WAIT_FOR_RECONNECT: user_input[CONF_WAIT_FOR_RECONNECT],
                },
            )
        return self.async_show_form(
            step_id="persistent",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_WAIT_FOR_RECONNECT,
                        default=self.config_entry.options.get(
                            CONF_WAIT_FOR_RECONNECT, False
                        ),
                    ): bool,
                }
            ),
        )

    async def async_step_on_demand(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    **self.config_entry.options,
                    **self._unlock_check_option(),
                    CONF_KEEP_CONNECTED: False,
                    CONF_WAIT_FOR_RECONNECT: False,
                    CONF_POLL_INTERVAL: int(user_input[CONF_POLL_INTERVAL]),
                    CONF_HOLD_TIME: int(user_input[CONF_HOLD_TIME]),
                },
            )
        intervals = ["0", "10", "20", "30", "40", "50", "60"]
        return self.async_show_form(
            step_id="on_demand",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=str(
                            self.config_entry.options.get(CONF_POLL_INTERVAL, 20)
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=intervals,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="connection_duration",
                        )
                    ),
                    vol.Required(
                        CONF_HOLD_TIME,
                        default=str(self.config_entry.options.get(CONF_HOLD_TIME, 10)),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=intervals,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="connection_duration",
                        )
                    ),
                }
            ),
        )
