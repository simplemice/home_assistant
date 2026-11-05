"""A1 device identity, entity base and BLE update coordinator."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .application.lock_actions import LockActions
from .protocols.tuya_ble.exceptions import ProtocolError
from .application.lock_commands import LockCommandWaiter
from .application.lock_status import ReportedLockStatus

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN
from .domain.command_context import (
    CommandBusy,
    CommandClosed,
    CommandNotReady,
    CommandStateUnknown,
)


class SmartlockEntity(CoordinatorEntity):
    def __init__(self, data, description):
        super().__init__(data.coordinator)
        self._device = data.device
        self._model = data.model
        self._session_policy = getattr(data, "session_policy", None)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._device.device_id}-{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device.address)},
            connections={(dr.CONNECTION_BLUETOOTH, self._device.address)},
            name=f"{data.model.name} {self._device.address.replace(':', '')[-6:]}",
            manufacturer=data.model.manufacturer,
            model=f"{data.model.name} ({data.model.product_id})",
        )
        if self._device.device_version:
            self._attr_device_info["sw_version"] = f"{self._device.device_version} (protocol {self._device.protocol_version})"
        if self._device.hardware_version:
            self._attr_device_info["hw_version"] = self._device.hardware_version

    @property
    def available(self):
        if self._session_policy is not None and not self._session_policy.persistent:
            return self._session_policy.available
        return self.coordinator.connected


class SmartlockActionEntity(SmartlockEntity):
    """Common HA boundary for the lock control and toggle button."""

    def __init__(self, data, description):
        super().__init__(data, description)
        self._commands = data.commands
        self._actions = data.actions
        self._session_policy = getattr(data, "session_policy", None)

    @property
    def available(self):
        return self._actions.available

    async def _execute_setting(self, action):
        if self._session_policy is None:
            return await self._execute_action(action)
        await self._execute_action(lambda: self._session_policy.execute(action))

    async def _execute_action(self, action):
        try:
            await action()
        except CommandBusy as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_busy"
            ) from exc
        except CommandStateUnknown as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_state_unknown"
            ) from exc
        except (TimeoutError, CommandClosed, CommandNotReady) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from exc
        except ProtocolError as exc:
            # Model-level refusals (e.g. no unlock token yet, no remote lock DP)
            # carry an actionable message; do not hide them behind "timed out".
            _LOGGER.warning("Command rejected: %s", exc)
            raise HomeAssistantError(f"Command rejected: {exc}") from exc
        except Exception as exc:
            _LOGGER.warning("Command failed: %r", exc)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from exc


class SmartlockCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, device, config_entry_id):
        super().__init__(hass, logging.getLogger(__name__), name=DOMAIN)
        self._device = device
        self._config_entry_id = config_entry_id
        self.connected = False
        self._unsubscribers = [
            device.register_connected_callback(self._connected),
            device.register_disconnected_callback(self._disconnected),
            device.register_callback(self._updated),
        ]

    @callback
    def _connected(self):
        self.connected = True
        registry = dr.async_get(self.hass)
        identifier = (DOMAIN, self._device.address)
        if hasattr(registry, "async_get_device_by_identifier"):
            entry = registry.async_get_device_by_identifier(
                identifier, self._config_entry_id
            )
        else:  # Compatibility with Home Assistant before the scoped registry API.
            entry = registry.async_get_device(identifiers={identifier})
        if entry is not None and self._device.device_version:
            registry.async_update_device(
                entry.id,
                sw_version=f"{self._device.device_version} (protocol {self._device.protocol_version})",
                hw_version=self._device.hardware_version or None,
            )
        self.async_update_listeners()

    @callback
    def _disconnected(self):
        self.connected = False
        self.async_update_listeners()

    @callback
    def _updated(self, updates):
        self.connected = True
        self.async_set_updated_data(None)

    def close(self):
        for unsubscribe in self._unsubscribers:
            if callable(unsubscribe):
                unsubscribe()
        self._unsubscribers.clear()


@dataclass
class SmartlockData:
    title: str
    device: object
    model: object
    manager: object
    coordinator: SmartlockCoordinator
    close: Callable[[], Awaitable[None]] | None = None
    commands: LockCommandWaiter | None = None
    status: ReportedLockStatus | None = None
    actions: LockActions | None = None
    session_policy: object | None = None
