"""Zambretti & Sager Weather Forecaster."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, EVENT_HOMEASSISTANT_STARTED, HomeAssistant
from homeassistant.helpers import config_validation as cv

from typing import Any

from .const import DOMAIN, VERSION
from .coordinator import async_create_coordinator
from .frontend import JSModuleRegistration

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


# ── WebSocket: version endpoint (для проверки совпадения версий) ──────────

@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/version"})
@websocket_api.async_response
async def _ws_get_version(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Возвращает версию интеграции на фронтенд."""
    connection.send_result(msg["id"], {"version": VERSION})


# ── async_setup ───────────────────────────────────────────────────────────

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Вызывается один раз при загрузке домена.

    Регистрирует WebSocket-команду и JS-карточку.
    Должен быть здесь, а не в async_setup_entry.
    """
    websocket_api.async_register_command(hass, _ws_get_version)

    async def _setup_frontend(_event=None) -> None:
        try:
            registrar = JSModuleRegistration(hass)
            await registrar.async_register()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "Failed to register Zambretti card resource: %s. "
                "Add manually: Settings → Dashboards → Resources → "
                "%s/zambretti-weather-card.js (JavaScript module)",
                err,
                "/zambretti_sager_card",
            )

    if hass.state == CoreState.running:
        await _setup_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _setup_frontend)

    return True


# ── async_setup_entry ─────────────────────────────────────────────────────

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка интеграции при добавлении через интерфейс."""
    _LOGGER.info("Инициализация Zambretti & Sager для: %s", entry.title)

    hass.data.setdefault(DOMAIN, {})
    coordinator = await async_create_coordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Перезапуск при изменении опций."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Выгрузка при удалении entry."""
    # Остановить подписку на state change, чтобы избежать утечки
    coordinator: Any = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is not None:
        coordinator._stop_pressure_watcher()  # noqa: SLF001

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
