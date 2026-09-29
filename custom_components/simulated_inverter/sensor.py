"""Sensor platform for the Simulated Inverter integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_DESCRIPTIONS, SW_VERSION
from .const import SimulatedInverterSensorEntityDescription


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Simulated Inverter sensors from a config entry."""
    async_add_entities(
        SimulatedInverterSensor(entry, description) for description in SENSOR_DESCRIPTIONS
    )


class SimulatedInverterSensor(SensorEntity):
    """A sensor mirroring one reading from the simulated power system."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: SimulatedInverterSensorEntityDescription

    def __init__(
        self,
        entry: ConfigEntry,
        description: SimulatedInverterSensorEntityDescription,
    ) -> None:
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Simulated Inverter",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=SW_VERSION,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        sources = self.entity_description.sources
        if sources:
            self.async_on_remove(
                async_track_state_change_event(self.hass, sources, self._handle_source_update)
            )
        self._recompute()

    @callback
    def _handle_source_update(self, event: Event[EventStateChangedData]) -> None:
        self._recompute()
        self.async_write_ha_state()

    def _recompute(self) -> None:
        states = {eid: self.hass.states.get(eid) for eid in self.entity_description.sources}
        value_fn = self.entity_description.value_fn
        if value_fn is None:
            self._attr_native_value = None
            return
        try:
            self._attr_native_value = value_fn(states)
        except (TypeError, ValueError, ZeroDivisionError):
            self._attr_native_value = None
