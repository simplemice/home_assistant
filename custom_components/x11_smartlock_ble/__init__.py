"""Home Assistant lifecycle adapter for the lock domain."""

from __future__ import annotations

import logging

from bleak.backends.device import BLEDevice
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import ADDRESS, BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.storage import Store

from .application.lock_actions import LockActions
from .application.lock_commands import LockCommandWaiter
from .application.lock_status import ReportedLockStatus
from .connections import ConnectionManager
from .const import (
    CONF_HOLD_TIME,
    CONF_KEEP_CONNECTED,
    CONF_POLL_INTERVAL,
    CONF_WAIT_FOR_RECONNECT,
    DOMAIN,
)
from .devices import SmartlockCoordinator, SmartlockData
from .keyman import LocalCredentialProvider
from .registry import create_connection

PLATFORMS = [
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.EVENT,
]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    address = entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(hass, address, True)
    if ble_device is None:
        # Keep command entities loaded while the radio is unavailable. Discovery
        # replaces this placeholder before the next observed connection attempt.
        ble_device = BLEDevice(address, entry.title, {})
    provider = LocalCredentialProvider(hass, {**entry.options, **entry.data})
    credentials = await provider.get_device_credentials(address)
    if credentials is None:
        raise ConfigEntryNotReady("Lock credentials are missing")
    try:
        device, model = create_connection(credentials, provider, ble_device)
    except ValueError as exc:
        raise ConfigEntryNotReady("Unsupported lock model") from exc
    if hasattr(model, "check_listener"):
        code_store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.unlock_check")
        configured = credentials.ble_unlock_check or ""
        saved = await code_store.async_load() or {}
        # A value saved for the same configured base is newer than the config.
        if saved.get("base") == configured and saved.get("current"):
            credentials.ble_unlock_check = saved["current"]

        def _remember(value, _store=code_store, _base=configured):
            _store.async_delay_save(lambda: {"base": _base, "current": value}, 1)

        model.check_listener = _remember
    coordinator = SmartlockCoordinator(hass, device, entry.entry_id)
    store = hass.data.setdefault(DOMAIN, {})
    connections = store.setdefault("_connections", ConnectionManager())
    persistent = entry.options.get(CONF_KEEP_CONNECTED, True)
    try:
        session_policy = await connections.start(
            entry.entry_id,
            device,
            persistent,
            poll_interval=entry.options.get(CONF_POLL_INTERVAL, 20),
            hold_time=entry.options.get(CONF_HOLD_TIME, 10),
        )
    except Exception as exc:
        coordinator.close()
        raise ConfigEntryNotReady("Could not establish the BLE session") from exc
    except BaseException:
        coordinator.close()
        raise

    commands = (
        LockCommandWaiter(device, coordinator.async_update_listeners)
        if persistent and entry.options.get(CONF_WAIT_FOR_RECONNECT, False)
        else None
    )
    status = ReportedLockStatus(
        device,
        model,
        coordinator.async_update_listeners,
        retain_on_disconnect=not persistent,
    )
    actions = LockActions(
        model, status, commands, coordinator.async_update_listeners, session_policy
    )

    async def close():
        await actions.close()
        try:
            if commands is not None:
                await commands.close()
        finally:
            try:
                await connections.close(entry.entry_id)
            finally:
                status.close()
                coordinator.close()

    data = SmartlockData(
        entry.title,
        device,
        model,
        provider,
        coordinator,
        close,
        commands,
        status,
        actions,
        session_policy,
    )
    store[entry.entry_id] = data
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        store.pop(entry.entry_id, None)
        await close()
        raise

    @callback
    def advertised(info, change):
        device.set_ble_device_and_advertisement_data(info.device, info.advertisement)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            advertised,
            BluetoothCallbackMatcher({ADDRESS: address}),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async def stopped(event):
        await close()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stopped))
    return True


async def _async_update_listener(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data.close()
        return True
    return False
