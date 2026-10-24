"""Shared diagnostic-event recorder for managers.

Centralises the ``{"ts": now, "event": name, **fields}`` shape every manager
was hand-building before calling ``EventBuffer.record``. Composed, not
inherited — managers hold an instance, the same philosophy as
:class:`.timeout_controller.TimeoutController`.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...diagnostics.event_buffer import EventBuffer


class EventRecorder:
    """Stamp and append a diagnostic event to an optional ring buffer.

    No-ops when no buffer is attached, so callers never need their own
    ``if buffer is not None`` guard. ``now_fn`` defaults to UTC-aware now and
    can be injected for managers that own a mockable clock (e.g. MotionManager).
    """

    def __init__(
        self,
        event_buffer: EventBuffer | None,
        *,
        now_fn: Callable[[], dt.datetime] | None = None,
    ) -> None:
        """Bind to a buffer (or None) and an optional clock."""
        self._event_buffer = event_buffer
        self._now_fn = now_fn or (lambda: dt.datetime.now(dt.UTC))

    def record(self, event: str, **fields: Any) -> None:
        """Record ``event`` with ``fields``, stamping ``ts`` from the clock."""
        if self._event_buffer is None:
            return
        self._event_buffer.record(
            {"ts": self._now_fn().isoformat(), "event": event, **fields}
        )
