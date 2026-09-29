"""Constants and sensor descriptions for the Simulated Inverter integration.

This integration does not simulate anything itself. It reads the existing
simulated power-flow sensors produced by packages/battery_simulation.yaml,
packages/grid_simulation.yaml, packages/solar_simulation.yaml and
packages/wind_turbine_simulation.yaml, and re-presents them as a single
device with the sensor set you'd get from a real hybrid inverter install
(modeled after Huawei FusionSolar / SolaX Power hardware): grid meter,
PV string controller, battery BMS, and weather-station probes.

A few sensors (string/pack/phase voltage & current, module temperature,
irradiance, humidity, arc-fault/insulation status) have no direct simulated
source. Those are derived with clearly-labeled nominal assumptions from the
power values that do exist, the same way a real inverter derives V/I from
its MPPT and meter ICs. Sensors with no plausible source at all (e.g. wind
direction) are intentionally left out rather than faked.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfIrradiance,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import State
from homeassistant.helpers.typing import StateType

from .util import clamp, num, text

DOMAIN = "simulated_inverter"
MANUFACTURER = "Simulated Systems"
MODEL = "SI-HYBRID-10K"
SW_VERSION = "1.0.0"

# Nominal assumptions used to derive V/I/temperature readings that the
# simulation packages never computed directly.
PANEL_RATED_W = 3000.0
PANEL_EFF = 0.85
PV_STRING_V_FLOOR = 500.0
PV_STRING_V_SPAN = 100.0
BATTERY_V_NOMINAL = 51.2
BATTERY_V_SAG_MAX = 3.0
BATTERY_V_RISE_MAX = 1.5
GRID_V_NOMINAL = 230.0
GRID_V_SAG_MAX = 5.0
GRID_V_RISE_MAX = 3.0
GRID_F_NOMINAL = 50.0


@dataclass(frozen=True, kw_only=True)
class SimulatedInverterSensorEntityDescription(SensorEntityDescription):
    """Sensor description bound to one or more source entities."""

    sources: tuple[str, ...] = ()
    value_fn: Callable[[Mapping[str, State | None]], StateType] | None = None


def _grid_net(states: Mapping[str, State | None]) -> StateType:
    imp = num(states, "sensor.grid_power_import_simulated")
    exp = num(states, "sensor.grid_power_export_simulated")
    return round(imp - exp, 1)


def _grid_voltage_l1(states: Mapping[str, State | None]) -> StateType:
    imp = num(states, "sensor.grid_power_import_simulated")
    exp = num(states, "sensor.grid_power_export_simulated")
    if imp > 0:
        sag = clamp(imp, 0, 3000) / 3000 * GRID_V_SAG_MAX
        return round(GRID_V_NOMINAL - sag, 1)
    if exp > 0:
        rise = clamp(exp, 0, 3000) / 3000 * GRID_V_RISE_MAX
        return round(GRID_V_NOMINAL + rise, 1)
    return GRID_V_NOMINAL


def _grid_current_l1(states: Mapping[str, State | None]) -> StateType:
    net = abs(num(states, "sensor.grid_power_import_simulated") - num(states, "sensor.grid_power_export_simulated"))
    voltage = _grid_voltage_l1(states)
    return round(net / voltage, 2) if voltage else 0.0


def _pv_string_voltage(states: Mapping[str, State | None]) -> StateType:
    power = num(states, "sensor.solar_live_power_simulated")
    if power <= 0:
        return 0.0
    fraction = clamp(power / (PANEL_RATED_W * PANEL_EFF), 0, 1)
    return round(PV_STRING_V_FLOOR + PV_STRING_V_SPAN * fraction, 1)


def _pv_string_current(states: Mapping[str, State | None]) -> StateType:
    power = num(states, "sensor.solar_live_power_simulated")
    voltage = _pv_string_voltage(states)
    return round(power / voltage, 2) if voltage else 0.0


def _pv_module_temperature(states: Mapping[str, State | None]) -> StateType:
    ambient = num(states, "sensor.astroweather_home_2m_temperature", 25.0)
    power = num(states, "sensor.solar_live_power_simulated")
    fraction = clamp(power / (PANEL_RATED_W * PANEL_EFF), 0, 1)
    return round(ambient + fraction * 25.0, 1)


def _irradiance(states: Mapping[str, State | None]) -> StateType:
    power = num(states, "sensor.solar_live_power_simulated")
    return round(clamp(power / (PANEL_RATED_W * PANEL_EFF) * 1000, 0, 1200), 0)


def _relative_humidity(states: Mapping[str, State | None]) -> StateType:
    temp = num(states, "sensor.astroweather_home_2m_temperature", 28.0)
    dew = num(states, "sensor.astroweather_astroweather_2m_dewpoint", 22.0)

    def _sat(t: float) -> float:
        return math.exp((17.625 * t) / (243.04 + t))

    rh = 100.0 * _sat(dew) / _sat(temp)
    return round(clamp(rh, 0, 100), 1)


def _battery_pack_voltage(states: Mapping[str, State | None]) -> StateType:
    power = num(states, "sensor.battery_power_simulated")
    if power < 0:
        sag = clamp(-power, 0, 3000) / 3000 * BATTERY_V_SAG_MAX
        return round(BATTERY_V_NOMINAL - sag, 2)
    rise = clamp(power, 0, 3000) / 3000 * BATTERY_V_RISE_MAX
    return round(BATTERY_V_NOMINAL + rise, 2)


def _battery_pack_current(states: Mapping[str, State | None]) -> StateType:
    power = num(states, "sensor.battery_power_simulated")
    voltage = _battery_pack_voltage(states)
    return round(power / voltage, 2) if voltage else 0.0


def _battery_cell_temp(states: Mapping[str, State | None]) -> StateType:
    ambient = num(states, "sensor.astroweather_home_2m_temperature", 25.0)
    power = abs(num(states, "sensor.battery_power_simulated"))
    return round(ambient + clamp(power / 3000, 0, 1) * 15.0, 1)


def _pv_rapid_shutdown_status(states: Mapping[str, State | None]) -> StateType:
    elev = num(states, "sensor.astroweather_astroweather_sun_altitude")
    return "Standby (Night)" if elev < 5 else "Active"


def _arc_fault_monitor_status(states: Mapping[str, State | None]) -> StateType:
    thunder = num(states, "sensor.phuket_day_thunder_probability")
    if thunder > 70:
        return "Warning: High EMI Interference"
    if thunder > 40:
        return "Elevated Monitoring"
    return "Normal"


def _insulation_resistance_status(states: Mapping[str, State | None]) -> StateType:
    rain = num(states, "sensor.pirateweather_precip_intensity")
    if rain > 10:
        return "Monitoring - High Moisture"
    if rain > 2:
        return "Monitoring"
    return "Normal"


def _self_consumption_ratio(states: Mapping[str, State | None]) -> StateType:
    home = num(states, "sensor.sim_home_power")
    grid_import = num(states, "sensor.grid_power_import_simulated")
    if home <= 0:
        return 100.0
    return round(clamp((home - grid_import) / home * 100, 0, 100), 1)


SENSOR_DESCRIPTIONS: tuple[SimulatedInverterSensorEntityDescription, ...] = (
    # --- Grid meter (Huawei DTSU666-H / SolaX SDM630 analog) ---
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_power",
        name="Grid Meter Power",
        icon="mdi:transmission-tower",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.grid_power_import_simulated", "sensor.grid_power_export_simulated"),
        value_fn=_grid_net,
    ),
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_import_power",
        name="Grid Meter Import Power",
        icon="mdi:transmission-tower-import",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.grid_power_import_simulated",),
        value_fn=lambda s: round(num(s, "sensor.grid_power_import_simulated"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_export_power",
        name="Grid Meter Export Power",
        icon="mdi:transmission-tower-export",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.grid_power_export_simulated",),
        value_fn=lambda s: round(num(s, "sensor.grid_power_export_simulated"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_voltage_l1",
        name="Grid Meter Voltage L1",
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        sources=("sensor.grid_power_import_simulated", "sensor.grid_power_export_simulated"),
        value_fn=_grid_voltage_l1,
    ),
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_current_l1",
        name="Grid Meter Current L1",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        sources=("sensor.grid_power_import_simulated", "sensor.grid_power_export_simulated"),
        value_fn=_grid_current_l1,
    ),
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_frequency",
        name="Grid Meter Frequency",
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        sources=(),
        value_fn=lambda s: GRID_F_NOMINAL,
    ),
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_status",
        name="Grid Meter Status",
        icon="mdi:transmission-tower",
        entity_category=EntityCategory.DIAGNOSTIC,
        sources=("sensor.grid_status",),
        value_fn=lambda s: text(s, "sensor.grid_status"),
    ),
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_energy_import_total",
        name="Grid Meter Energy Import Total",
        icon="mdi:transmission-tower-import",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        sources=("sensor.total_grid_energy_import",),
        value_fn=lambda s: round(num(s, "sensor.total_grid_energy_import"), 3),
    ),
    SimulatedInverterSensorEntityDescription(
        key="grid_meter_energy_export_total",
        name="Grid Meter Energy Export Total",
        icon="mdi:transmission-tower-export",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        sources=("sensor.total_grid_energy_export",),
        value_fn=lambda s: round(num(s, "sensor.total_grid_energy_export"), 3),
    ),
    # --- PV string / Smart Module Controller (Huawei SUN2000-P analog) ---
    SimulatedInverterSensorEntityDescription(
        key="pv_string_power",
        name="PV String Power",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.solar_live_power_simulated",),
        value_fn=lambda s: round(num(s, "sensor.solar_live_power_simulated"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="pv_string_voltage",
        name="PV String Voltage",
        icon="mdi:flash-triangle",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        sources=("sensor.solar_live_power_simulated",),
        value_fn=_pv_string_voltage,
    ),
    SimulatedInverterSensorEntityDescription(
        key="pv_string_current",
        name="PV String Current",
        icon="mdi:current-dc",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        sources=("sensor.solar_live_power_simulated",),
        value_fn=_pv_string_current,
    ),
    SimulatedInverterSensorEntityDescription(
        key="pv_module_temperature",
        name="PV Module Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        sources=("sensor.solar_live_power_simulated", "sensor.astroweather_home_2m_temperature"),
        value_fn=_pv_module_temperature,
    ),
    SimulatedInverterSensorEntityDescription(
        key="pv_power_to_home",
        name="PV Power to Home",
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.solar_power_to_home",),
        value_fn=lambda s: round(num(s, "sensor.solar_power_to_home"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="pv_power_to_battery",
        name="PV Power to Battery",
        icon="mdi:battery-charging",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.solar_power_to_battery",),
        value_fn=lambda s: round(num(s, "sensor.solar_power_to_battery"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="pv_power_to_grid",
        name="PV Power to Grid",
        icon="mdi:transmission-tower-export",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.solar_export_to_grid",),
        value_fn=lambda s: round(num(s, "sensor.solar_export_to_grid"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="pv_energy_total",
        name="PV Energy Total",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        sources=("sensor.total_solar_energy_in",),
        value_fn=lambda s: round(num(s, "sensor.total_solar_energy_in"), 3),
    ),
    SimulatedInverterSensorEntityDescription(
        key="pv_rapid_shutdown_status",
        name="PV Rapid Shutdown Status",
        icon="mdi:shield-sun",
        entity_category=EntityCategory.DIAGNOSTIC,
        sources=("sensor.astroweather_astroweather_sun_altitude",),
        value_fn=_pv_rapid_shutdown_status,
    ),
    # --- Battery BMS (Triple Power / T-BAT analog) ---
    SimulatedInverterSensorEntityDescription(
        key="battery_soc",
        name="Battery State of Charge",
        icon="mdi:battery-high",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        sources=("sensor.battery_soc_simulated",),
        value_fn=lambda s: round(num(s, "sensor.battery_soc_simulated"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_energy_remaining",
        name="Battery Energy Remaining",
        icon="mdi:battery-high",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        sources=("sensor.battery_energy_remaining",),
        value_fn=lambda s: round(num(s, "sensor.battery_energy_remaining"), 3),
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_power",
        name="Battery Power",
        icon="mdi:battery-sync",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.battery_power_simulated",),
        value_fn=lambda s: round(num(s, "sensor.battery_power_simulated"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_charge_power",
        name="Battery Charge Power",
        icon="mdi:battery-charging-high",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.battery_charge_power_total",),
        value_fn=lambda s: round(num(s, "sensor.battery_charge_power_total"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_discharge_power",
        name="Battery Discharge Power",
        icon="mdi:home-battery",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.battery_discharge_power_home",),
        value_fn=lambda s: round(num(s, "sensor.battery_discharge_power_home"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_bms_status",
        name="Battery BMS Status",
        icon="mdi:battery-heart-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        sources=("sensor.battery_bms_state",),
        value_fn=lambda s: text(s, "sensor.battery_bms_state"),
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_runtime_remaining",
        name="Battery Runtime Remaining",
        icon="mdi:timer-check",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        sources=("sensor.battery_runtime_remaining",),
        value_fn=lambda s: round(num(s, "sensor.battery_runtime_remaining", 999), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_pack_voltage",
        name="Battery Pack Voltage",
        icon="mdi:flash",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        sources=("sensor.battery_power_simulated",),
        value_fn=_battery_pack_voltage,
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_pack_current",
        name="Battery Pack Current (DC Shunt)",
        icon="mdi:current-dc",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        sources=("sensor.battery_power_simulated",),
        value_fn=_battery_pack_current,
    ),
    SimulatedInverterSensorEntityDescription(
        key="battery_cell_temp_avg",
        name="Battery Cell Temperature Average",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        sources=("sensor.battery_power_simulated", "sensor.astroweather_home_2m_temperature"),
        value_fn=_battery_cell_temp,
    ),
    # --- Wind turbine input (auxiliary DC generation source) ---
    SimulatedInverterSensorEntityDescription(
        key="wind_turbine_power",
        name="Wind Turbine Power",
        icon="mdi:wind-turbine",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.wind_turbine_power_simulated",),
        value_fn=lambda s: round(num(s, "sensor.wind_turbine_power_simulated"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="wind_hub_speed",
        name="Wind Speed (Hub Height, 3S-WS-PLS-A analog)",
        icon="mdi:weather-windy",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        sources=("sensor.wind_speed_hub",),
        value_fn=lambda s: round(num(s, "sensor.wind_speed_hub"), 2),
    ),
    SimulatedInverterSensorEntityDescription(
        key="wind_yaw_efficiency",
        name="Wind Yaw Efficiency",
        icon="mdi:rotate-3d-variant",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        sources=("sensor.wind_yaw_efficiency",),
        value_fn=lambda s: round(num(s, "sensor.wind_yaw_efficiency", 1.0), 3),
    ),
    SimulatedInverterSensorEntityDescription(
        key="wind_power_to_battery",
        name="Wind Power to Battery",
        icon="mdi:battery-arrow-up",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.wind_battery_charge_power",),
        value_fn=lambda s: round(num(s, "sensor.wind_battery_charge_power"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="wind_energy_total",
        name="Wind Energy Total",
        icon="mdi:wind-turbine",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        sources=("sensor.wind_energy_raw",),
        value_fn=lambda s: round(num(s, "sensor.wind_energy_raw"), 3),
    ),
    # --- Weather station probes (DataHub 1000 / Sensor Box analog) ---
    SimulatedInverterSensorEntityDescription(
        key="irradiance",
        name="Solar Irradiance (3S-IS analog)",
        icon="mdi:weather-sunny",
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        sources=("sensor.solar_live_power_simulated",),
        value_fn=_irradiance,
    ),
    SimulatedInverterSensorEntityDescription(
        key="ambient_temperature",
        name="Ambient Temperature (3S-AT-PT1000 analog)",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        sources=("sensor.astroweather_home_2m_temperature",),
        value_fn=lambda s: round(num(s, "sensor.astroweather_home_2m_temperature", 25.0), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="relative_humidity",
        name="Relative Humidity (3S-RH&AT analog)",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        sources=("sensor.astroweather_home_2m_temperature", "sensor.astroweather_astroweather_2m_dewpoint"),
        value_fn=_relative_humidity,
    ),
    # --- Embedded safety sensors ---
    SimulatedInverterSensorEntityDescription(
        key="arc_fault_monitor_status",
        name="AFCI Arc Fault Monitor Status",
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        sources=("sensor.phuket_day_thunder_probability",),
        value_fn=_arc_fault_monitor_status,
    ),
    SimulatedInverterSensorEntityDescription(
        key="insulation_resistance_status",
        name="Ground Fault Insulation Monitor Status",
        icon="mdi:shield-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        sources=("sensor.pirateweather_precip_intensity",),
        value_fn=_insulation_resistance_status,
    ),
    # --- System summary ---
    SimulatedInverterSensorEntityDescription(
        key="total_home_load_power",
        name="Total Home Load Power",
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        sources=("sensor.sim_home_power",),
        value_fn=lambda s: round(num(s, "sensor.sim_home_power"), 1),
    ),
    SimulatedInverterSensorEntityDescription(
        key="self_consumption_ratio",
        name="Self-Consumption Ratio",
        icon="mdi:home-percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        sources=("sensor.sim_home_power", "sensor.grid_power_import_simulated"),
        value_fn=_self_consumption_ratio,
    ),
)
