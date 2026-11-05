from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .classify import matches
from .const import DOMAIN, NEW_WARNING_PULSE_SECONDS
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
        TMDThunderstormWarningSensor(coordinator, entry),
        TMDMonsoonWarningSensor(coordinator, entry),
        TMDNewWarningSensor(coordinator, entry),
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

    def _matches(self, category: str) -> bool:
        return matches(self.coordinator.active_warnings, category)


class TMDWarningActiveSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:shield-alert"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Warning Active"
        self._attr_unique_id = f"{entry.entry_id}_warning_active"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.active_warnings)


class TMDStormWarningSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:weather-hurricane"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Storm Warning"
        self._attr_unique_id = f"{entry.entry_id}_storm_warning"

    @property
    def is_on(self) -> bool:
        return self._matches("storm")


class TMDHeavyRainSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_icon = "mdi:weather-pouring"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Heavy Rain Warning"
        self._attr_unique_id = f"{entry.entry_id}_heavy_rain"

    @property
    def is_on(self) -> bool:
        return self._matches("heavy_rain")


class TMDWaveWarningSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:waves"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Wave Warning"
        self._attr_unique_id = f"{entry.entry_id}_wave_warning"

    @property
    def is_on(self) -> bool:
        return self._matches("wave")


class TMDThunderstormWarningSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:weather-lightning"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Thunderstorm Warning"
        self._attr_unique_id = f"{entry.entry_id}_thunderstorm_warning"

    @property
    def is_on(self) -> bool:
        return self._matches("thunderstorm")


class TMDMonsoonWarningSensor(TMDBinarySensorBase):
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:weather-windy"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD Monsoon Cold Warning"
        self._attr_unique_id = f"{entry.entry_id}_monsoon_cold_warning"

    @property
    def is_on(self) -> bool:
        return self._matches("monsoon")


class TMDNewWarningSensor(TMDBinarySensorBase):
    """Pulses ON for a few minutes when a previously unseen warning appears.

    Warnings present at startup are not "new", and a re-issued update to a known
    issue does not re-trigger.
    """

    _attr_icon = "mdi:bell-ring"

    def __init__(self, coordinator: TMDCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "TMD New Warning"
        self._attr_unique_id = f"{entry.entry_id}_new_warning"
        self._seen = self._keys()
        self._pulse_on = False
        self._cancel_pulse: CALLBACK_TYPE | None = None

    def _keys(self) -> set[tuple[str, str]]:
        return {
            (w.get("issue_no", ""), w.get("title_en") or w.get("title_th", ""))
            for w in self.coordinator.data or []
        }

    @property
    def is_on(self) -> bool:
        return self._pulse_on

    @callback
    def _handle_coordinator_update(self) -> None:
        keys = self._keys()
        if keys - self._seen:
            self._start_pulse()
        self._seen |= keys
        super()._handle_coordinator_update()

    def _start_pulse(self) -> None:
        if self._cancel_pulse:
            self._cancel_pulse()
        self._pulse_on = True
        self._cancel_pulse = async_call_later(
            self.hass, NEW_WARNING_PULSE_SECONDS, self._end_pulse
        )

    @callback
    def _end_pulse(self, _now) -> None:
        self._cancel_pulse = None
        self._pulse_on = False
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._cancel_pulse:
            self._cancel_pulse()
            self._cancel_pulse = None
        await super().async_will_remove_from_hass()
