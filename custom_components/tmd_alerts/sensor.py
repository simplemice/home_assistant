from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.util import dt as dt_util

from .classify import SEVERITY_OPTIONS, severity
from .const import DOMAIN
from .coordinator import TMDCoordinator

_NO_WARNINGS = {
    "en": "None",
    "th": "ไม่มีการแจ้งเตือน",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TMDCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        TMDWarningCountSensor(coordinator, entry),
        TMDLatestWarningSensor(coordinator, entry),
        TMDWarningExpiresSensor(coordinator, entry),
        TMDWarningSeveritySensor(coordinator, entry),
        TMDWarningsUpdatedSensor(coordinator, entry),
    ])


def _device_info(entry_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="Thailand Weather Alerts (TMD)",
        manufacturer="Thai Meteorological Department",
        model="Weather Warning API v2",
        configuration_url="https://www.tmd.go.th",
    )


class TMDWarningCountSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "warnings"
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "TMD Active Warnings"
        self._attr_unique_id = f"{entry.entry_id}_warning_count"
        self._attr_device_info = _device_info(entry.entry_id)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.active_warnings)

    @property
    def extra_state_attributes(self) -> dict:
        active = self.coordinator.active_warnings
        if not active:
            return {}
        lang = self.coordinator.language
        return {
            "warnings": [
                {
                    "title": w.get(f"title_{lang}", w.get("title_en", "")),
                    "headline": w.get(f"headline_{lang}", w.get("headline_en", "")),
                    "effect_start": w.get("effect_start", ""),
                    "effect_end": w.get("effect_end", ""),
                }
                for w in active
            ]
        }


class TMDLatestWarningSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:weather-lightning-rainy"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "TMD Latest Warning"
        self._attr_unique_id = f"{entry.entry_id}_latest_warning"
        self._attr_device_info = _device_info(entry.entry_id)

    @property
    def _lang(self) -> str:
        return self.coordinator.language

    @property
    def native_value(self) -> str:
        active = self.coordinator.active_warnings
        if not active:
            return _NO_WARNINGS.get(self._lang, _NO_WARNINGS["en"])
        w = active[0]
        return (
            w.get(f"title_{self._lang}")
            or w.get("title_en")
            or _NO_WARNINGS.get(self._lang, _NO_WARNINGS["en"])
        )

    @property
    def extra_state_attributes(self) -> dict:
        active = self.coordinator.active_warnings
        if not active:
            return {}
        w = active[0]
        lang = self._lang
        end = w.get("effect_end_dt")
        hours_remaining = (
            round(max((end - dt_util.now()).total_seconds(), 0) / 3600, 1)
            if end
            else None
        )
        return {
            "headline": w.get(f"headline_{lang}") or w.get("headline_en", ""),
            "description": w.get(f"description_{lang}") or w.get("description_en", ""),
            "effect_start": w.get("effect_start", ""),
            "effect_end": w.get("effect_end", ""),
            "announce_date": w.get("announce_date", ""),
            "url": w.get(f"url_{lang}") or w.get("url_en", ""),
            "contact": w.get("contact", ""),
            "issue_no": w.get("issue_no", ""),
            "hours_remaining": hours_remaining,
            "language": lang,
        }


class TMDWarningExpiresSensor(CoordinatorEntity, SensorEntity):
    """Soonest end time among active warnings (use as an "all clear" trigger)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "TMD Warning Expires"
        self._attr_unique_id = f"{entry.entry_id}_warning_expires"
        self._attr_device_info = _device_info(entry.entry_id)

    @property
    def native_value(self):
        ends = [
            w["effect_end_dt"]
            for w in self.coordinator.active_warnings
            if w.get("effect_end_dt")
        ]
        return min(ends) if ends else None


class TMDWarningSeveritySensor(CoordinatorEntity, SensorEntity):
    """Keyword-derived severity: none / advisory / warning / severe."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = SEVERITY_OPTIONS
    _attr_icon = "mdi:alert-octagon"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "TMD Warning Severity"
        self._attr_unique_id = f"{entry.entry_id}_warning_severity"
        self._attr_device_info = _device_info(entry.entry_id)

    @property
    def native_value(self) -> str:
        return severity(self.coordinator.active_warnings)


class TMDWarningsUpdatedSensor(CoordinatorEntity, SensorEntity):
    """Time of the last successful TMD fetch."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:update"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "TMD Warnings Updated"
        self._attr_unique_id = f"{entry.entry_id}_warnings_updated"
        self._attr_device_info = _device_info(entry.entry_id)

    @property
    def native_value(self):
        return self.coordinator.last_success
