"""Утилиты для чтения и коррекции давления."""

from __future__ import annotations

import logging

from homeassistant.const import UnitOfPressure
from homeassistant.core import State
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.unit_conversion import PressureConverter

_LOGGER = logging.getLogger(__name__)

_INVALID_STATES = frozenset({"unknown", "unavailable", "none", ""})

_HPA_UNITS = frozenset({
    UnitOfPressure.HPA,
    UnitOfPressure.MBAR,
    "hPa",
    "mbar",
    "mb",
})


async def get_elevation(hass, latitude, longitude):
    """Получить высоту над уровнем моря через Open-Elevation API."""
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={latitude},{longitude}"
    session = async_get_clientsession(hass)
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                return data["results"][0]["elevation"]
    except Exception as err:
        _LOGGER.warning("Failed to get elevation from API: %s", err)
    return None


def calculate_sea_level_pressure(pressure, temperature, altitude):
    """Рассчитать давление на уровне моря."""
    if altitude is None or altitude == 0:
        return pressure

    factor = 1 - (0.0065 * altitude) / (temperature + 0.0065 * altitude + 273.15)

    if factor <= 0:
        return pressure + (altitude / 8.3)

    return pressure / (factor ** 5.257)


def _normalize_pressure_value(value: float, unit: str | None, entity_id: str) -> float:
    """Нормализовать числовое значение давления в hPa."""
    if unit in _HPA_UNITS or unit is None:
        # Если единица не указана, но значение > 2000 — скорее всего Па
        if unit is None and value > 2000:
            return value / 100
        return value

    if unit == UnitOfPressure.PA:
        return value / 100

    try:
        return PressureConverter.convert(value, unit, UnitOfPressure.HPA)
    except Exception:
        _LOGGER.warning(
            "Unknown pressure unit '%s' for %s, assuming hPa",
            unit,
            entity_id,
        )
        return value


def parse_pressure_hpa(state: State) -> float:
    """Прочитать давление из состояния сенсора и нормализовать в hPa."""
    if state.state.lower() in _INVALID_STATES:
        raise ValueError(f"Sensor {state.entity_id} has invalid state: {state.state!r}")
    value = float(state.state)
    unit = state.attributes.get("unit_of_measurement")
    return _normalize_pressure_value(value, unit, state.entity_id)


def parse_pressure_hpa_from_history(history_state) -> float:
    """Прочитать давление из записи recorder (State или dict или LazyState)."""

    # Объект State из homeassistant.core
    if isinstance(history_state, State):
        return parse_pressure_hpa(history_state)

    # dict — компактный формат recorder в новых версиях HA
    if isinstance(history_state, dict):
        state_value = history_state.get("state") or history_state.get("s")
        if state_value is None or str(state_value).lower() in _INVALID_STATES:
            raise ValueError(f"Invalid history pressure state: {state_value!r}")
        unit = history_state.get("unit_of_measurement") or history_state.get("uom")
        entity_id = history_state.get("entity_id", "history")
        return _normalize_pressure_value(float(state_value), unit, entity_id)

    # LazyState или любой другой объект с атрибутами
    state_value = getattr(history_state, "state", None)
    if state_value is None or str(state_value).lower() in _INVALID_STATES:
        raise ValueError(f"Invalid history pressure state: {state_value!r}")

    unit = getattr(history_state, "attributes", {}).get("unit_of_measurement")
    entity_id = getattr(history_state, "entity_id", "history")
    return _normalize_pressure_value(float(state_value), unit, entity_id)
