"""ACP-originated cover position-command context tracker.

Mirrors :class:`stop.StopTracker` but for ``cover.set_cover_position``,
``cover.open_cover``, ``cover.close_cover``, and ``cover.set_cover_tilt_position``.
The coordinator's state-change handler uses ``was_acp_position_context`` to
distinguish ACP-originated state changes from user-initiated ones — when a state
change carries an HA Context whose id is **not** in this tracker, the event is by
definition external (a real user, an automation, or another integration), and
manual-override detection can fast-path it without relying on numeric position
math (critical for ``assumed_state`` and OPEN/CLOSE-only covers where the math
path is unreliable).

The two trackers are kept separate rather than collapsed into a generic
``ContextTracker`` because their lifecycles differ: stop_cover contexts feed the
``EVENT_CALL_SERVICE`` listener (a service-call observation path), while
position contexts feed the state-change listener (a state-mutation observation
path). Sharing a single deque would conflate the two and break the existing
``acp_stop_context_count`` introspection used by tests.
"""

from __future__ import annotations

from collections import deque


class PositionContextTracker:
    """Tracks ACP-originated cover position-command context ids.

    Deque is capped at 16 entries (matches :class:`stop.StopTracker`) — enough
    for several concurrent reconciliation passes; older context ids fall off
    naturally as new ones append.
    """

    _CONTEXT_HISTORY_SIZE = 16

    def __init__(self) -> None:
        """Initialize an empty bounded history of ACP-originated context ids."""
        self._acp_position_contexts: deque[str] = deque(
            maxlen=self._CONTEXT_HISTORY_SIZE
        )

    def record(self, context_id: str) -> None:
        """Append ``context_id`` to the ACP-originated position-command history."""
        self._acp_position_contexts.append(context_id)

    def was_acp_position_context(self, context_id: str) -> bool:
        """Whether ``context_id`` belongs to an ACP-originated position-command call."""
        return context_id in self._acp_position_contexts

    def acp_position_context_count(self, *, unique: bool = False) -> int:
        """Return the number of recorded ACP-originated position-command context ids.

        With ``unique=True`` returns the count of distinct ids — lets tests
        verify production code minted a fresh context per call without
        inspecting the underlying deque.
        """
        if unique:
            return len(set(self._acp_position_contexts))
        return len(self._acp_position_contexts)
