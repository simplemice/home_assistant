"""Open button. Close/Status/Calibrate buttons were removed on purpose."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .devices import SmartlockActionEntity


class LockActionButton(SmartlockActionEntity, ButtonEntity):
    def __init__(self, data, locked):
        self._locked = locked
        key = "close_lock" if locked else "open_lock"
        super().__init__(
            data,
            ButtonEntityDescription(
                key=key,
                translation_key=key,
                icon="mdi:lock" if locked else "mdi:lock-open",
            ),
        )

    async def async_press(self):
        await self._execute_action(lambda: self._actions.set_locked(self._locked))


class RefreshStatusButton(SmartlockActionEntity, ButtonEntity):
    def __init__(self, data):
        super().__init__(
            data,
            ButtonEntityDescription(
                key="refresh_status",
                translation_key="refresh_status",
                icon="mdi:refresh",
            ),
        )

    async def async_press(self):
        await self._execute_action(self._session_policy.refresh)


class CalibrateButton(SmartlockActionEntity, ButtonEntity):
    def __init__(self, data):
        super().__init__(
            data,
            ButtonEntityDescription(
                key="calibrate",
                translation_key="calibrate",
                entity_category=EntityCategory.CONFIG,
                icon="mdi:target",
            ),
        )

    async def async_press(self):
        await self._execute_setting(self._model.calibrate)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    # Only "Open" is exposed. Drop the registry entries of the buttons that were
    # removed (and the obsolete toggle) so they do not linger as unavailable.
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    device_id = data.device.device_id
    for domain, key in (
        ("button", "toggle_lock"),
        ("button", "close_lock"),
        ("button", "refresh_status"),
        ("button", "calibrate"),
        ("lock", "manual_lock"),
        ("sensor", "expected_action"),
    ):
        old_id = registry.async_get_entity_id(domain, DOMAIN, f"{device_id}-{key}")
        if old_id:
            registry.async_remove(old_id)
    async_add_entities([LockActionButton(data, False)])
