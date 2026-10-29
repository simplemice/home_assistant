"""Sensor platform for LEX TH."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LexThCoordinator
from .const import (
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    SENSOR_NAME,
    SENSOR_NAME_DETAILS,
    STATE_TEXT,
    STATES,
    describe_status,
    normalize_status,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: LexThCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [LexThStatusSensor(coordinator, entry), LexThDetailsSensor(coordinator, entry)]
    )


class LexThEntity(CoordinatorEntity[LexThCoordinator], SensorEntity):
    """Shared device info and language handling."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LexThCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._language = entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        number = coordinator.tracking_number
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, number)},
            name=f"LEX TH {number}",
            manufacturer="LEX TH",
            model="Parcel",
            configuration_url=coordinator.data["tracking_url"]
            if coordinator.data
            else None,
        )

    @property
    def _description(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        return describe_status(data.get("raw_status"), data["state"], self._language)


class LexThStatusSensor(LexThEntity):
    """Normalized parcel status."""

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATES
    _attr_icon = "mdi:package-variant-closed"
    # Timeline can be large and changes rarely; keep it out of the recorder.
    _unrecorded_attributes = frozenset({"timeline"})

    def __init__(self, coordinator: LexThCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = SENSOR_NAME[self._language]
        self._attr_unique_id = f"{coordinator.tracking_number}_status"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data["state"] if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        last_update = data.get("last_update")
        return {
            "tracking_number": data.get("tracking_number"),
            "status_text": STATE_TEXT[self._language].get(data.get("state")),
            "description": self._description,
            "raw_status": data.get("raw_status"),
            "provider": data.get("provider"),
            "last_location": data.get("last_location"),
            "last_update": last_update.isoformat() if last_update else None,
            "package_code": data.get("package_code"),
            "tracking_url": data.get("tracking_url"),
            "timeline": [
                {
                    "status": e["status"],
                    "description": describe_status(
                        e["status"], normalize_status(e["status"]), self._language
                    ),
                    "time": e["time"].isoformat() if e["time"] else None,
                    "location": e["location"],
                    "provider": e["provider"],
                }
                for e in data.get("timeline", [])
            ],
        }


class LexThDetailsSensor(LexThEntity):
    """Lazada-style sentence describing the latest tracking event."""

    _attr_translation_key = "details"
    _attr_icon = "mdi:package-variant"

    def __init__(self, coordinator: LexThCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = SENSOR_NAME_DETAILS[self._language]
        self._attr_unique_id = f"{coordinator.tracking_number}_details"

    @property
    def native_value(self) -> str | None:
        return self._description

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        last_update = data.get("last_update")
        return {
            "last_location": data.get("last_location"),
            "last_update": last_update.isoformat() if last_update else None,
        }
