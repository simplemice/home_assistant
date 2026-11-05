"""Read owner-provided A1 credentials from a local file; no cloud client."""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import CONF_CRED_FILE
from .domain.credentials import CredentialProvider, LockCredentials
from .registry import MODELS


class LocalCredentialProvider(CredentialProvider):
    def __init__(self, hass: HomeAssistant, data: dict) -> None:
        self._hass = hass
        self._data = data
        self._devices = None

    async def get_device_credentials(
        self, address, force_update=False, save_data=False
    ):
        inline = self._data.get("credentials")
        if inline and self._data.get("address", "").upper() == address.upper():
            data = dict(inline)
            override = self._data.get("ble_unlock_check")
            if isinstance(override, str) and override.strip():
                data["ble_unlock_check"] = override.strip()
        else:
            data = await self._from_file(address, force_update)
        model = MODELS.get(data.get("product_id")) if isinstance(data, dict) else None
        if model is None or data.get("category") != model.category:
            return None
        if not all(
            isinstance(data.get(k), str) and data[k]
            for k in ("uuid", "local_key", "device_id")
        ):
            return None
        return LockCredentials(
            data["uuid"],
            data["local_key"],
            data["device_id"],
            model.category,
            model.product_id,
            data.get("device_name", model.name),
            data.get("product_model", model.name),
            data.get("product_name", model.name),
            data.get("ble_unlock_check"),
        )

    async def _from_file(self, address, force_update):
        if self._devices is None or force_update:
            path = Path(self._hass.config.path(CONF_CRED_FILE))
            try:
                contents = await self._hass.async_add_executor_job(
                    path.read_text, "utf-8"
                )
                self._devices = {k.upper(): v for k, v in json.loads(contents).items()}
            except (OSError, ValueError, AttributeError):
                self._devices = {}
        value = self._devices.get(address.upper())
        return value if isinstance(value, dict) else None

    @property
    def data(self):
        return self._data
