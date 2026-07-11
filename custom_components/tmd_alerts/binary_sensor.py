from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TMDCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TMDCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        TMDWarningActiveSensor(coordinator, entry),
        TMDStormWarningSensor(coordinator, entry),
        TMDHeavyRainSensor(coordinator, entry),
        TMDWaveWarningSensor(coordinator, entry),
    ])


def _device_info(entry_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="Thailand Weather Alerts (TMD)",
        manufacturer="Thai Meteorological Department",
        model="Weather Warning API v2",
        configuration_url="https://www.tmd.go.th",
    )


class TMDBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = _device_info(entry.entry_id)

    def _matches_keywords(self, *keywords: str) -> bool:
        if not self.coordinator.data:
            return False
        for warning in self.coordinator.data:
            text = (
                warning.get("title_en", "") + " " + warning.get("headline_en", "")
            ).lower()
            if any(kw in text for kw in keywords):
                return True
        return False


class TMDWarningActiveSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:shield-alert"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Warning Active"
        self._attr_unique_id = f"{entry.entry_id}_warning_active"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data)


class TMDStormWarningSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:weather-hurricane"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Storm Warning"
        self._attr_unique_id = f"{entry.entry_id}_storm_warning"

    @property
    def is_on(self) -> bool:
        return self._matches_keywords("storm", "tropical", "typhoon", "cyclone", "depression")


class TMDHeavyRainSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_icon = "mdi:weather-pouring"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Heavy Rain Warning"
        self._attr_unique_id = f"{entry.entry_id}_heavy_rain"

    @property
    def is_on(self) -> bool:
        return self._matches_keywords("heavy rain", "very heavy rain", "flash flood", "flood", "heavy to very heavy")


class TMDWaveWarningSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:waves"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Wave Warning"
        self._attr_unique_id = f"{entry.entry_id}_wave_warning"

    @property
    def is_on(self) -> bool:
        return self._matches_keywords("wave", "wind-wave", "strong wind", "andaman", "gulf")
