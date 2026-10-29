"""LEX TH (Lazada Express Thailand) parcel tracking."""
from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_URL,
    CONF_TRACKING_NUMBER,
    DOMAIN,
    REQUEST_TIMEOUT,
    SCAN_INTERVAL,
    STATE_NOT_FOUND,
    TRACKING_URL,
    normalize_status,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


def _ms_to_utc(value: Any) -> datetime | None:
    """Convert epoch milliseconds to an aware UTC datetime."""
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def parse_response(number: str, payload: Any) -> dict[str, Any]:
    """Turn the API JSON into the coordinator data dict."""
    if not isinstance(payload, dict) or not payload.get("success"):
        raise UpdateFailed(f"LEX TH returned unsuccessful response for {number}")

    base = {
        "tracking_number": number,
        "tracking_url": TRACKING_URL.format(number=number),
    }
    data = payload.get("data")
    if not isinstance(data, dict):
        return {
            **base,
            "state": STATE_NOT_FOUND,
            "raw_status": None,
            "provider": None,
            "last_location": None,
            "last_update": None,
            "package_code": None,
            "timeline": [],
        }

    events = []
    for item in data.get("timeline") or []:
        if not isinstance(item, dict):
            continue
        events.append(
            {
                "status": item.get("status"),
                "time": _ms_to_utc(item.get("processTime")),
                "location": item.get("location"),
                "provider": item.get("shippingProvider"),
            }
        )
    epoch = datetime.min.replace(tzinfo=UTC)
    events.sort(key=lambda e: e["time"] or epoch, reverse=True)

    newest = events[0] if events else {}
    raw_status = data.get("status") or newest.get("status")
    return {
        **base,
        "state": normalize_status(raw_status),
        "raw_status": raw_status,
        "provider": data.get("lastMileShippingProvider")
        or data.get("firstMileShippingProvider")
        or newest.get("provider"),
        "last_location": newest.get("location"),
        "last_update": newest.get("time"),
        "package_code": data.get("packageCode"),
        "timeline": events,
    }


async def async_fetch_parcel(hass: HomeAssistant, number: str) -> dict[str, Any]:
    """Fetch one parcel; raise UpdateFailed on network or API errors."""
    session = async_get_clientsession(hass)
    try:
        async with session.post(
            API_URL,
            json={"trackingNumber": number},
            headers={"content-type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        ) as resp:
            if resp.status != 200:
                _LOGGER.error(
                    "LEX TH API returned HTTP %s for %s (bot protection may have changed)",
                    resp.status,
                    number,
                )
                raise UpdateFailed(f"LEX TH API returned HTTP {resp.status}")
            payload = await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        _LOGGER.error("Error talking to LEX TH API for %s: %s", number, err)
        raise UpdateFailed(f"Error communicating with LEX TH: {err}") from err
    return parse_response(number, payload)


class LexThCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll one parcel."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.data[CONF_TRACKING_NUMBER]}",
            update_interval=SCAN_INTERVAL,
        )
        self.tracking_number: str = entry.data[CONF_TRACKING_NUMBER]

    async def _async_update_data(self) -> dict[str, Any]:
        return await async_fetch_parcel(self.hass, self.tracking_number)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a parcel from a config entry."""
    coordinator = LexThCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
