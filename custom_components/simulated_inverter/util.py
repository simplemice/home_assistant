"""Helpers for reading source entity states safely."""
from __future__ import annotations

from homeassistant.core import State

_UNAVAILABLE = ("unknown", "unavailable")


def num(states: dict[str, State | None], entity_id: str, default: float = 0.0) -> float:
    """Return a source entity's state as a float, or a default if missing/invalid."""
    state = states.get(entity_id)
    if state is None or state.state in _UNAVAILABLE:
        return default
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return default


def text(states: dict[str, State | None], entity_id: str, default: str = "Unknown") -> str:
    """Return a source entity's state as text, or a default if missing/invalid."""
    state = states.get(entity_id)
    if state is None or state.state in _UNAVAILABLE:
        return default
    return state.state


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
