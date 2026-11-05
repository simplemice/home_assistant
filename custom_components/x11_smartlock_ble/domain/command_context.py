"""Task-local execution deadline, independent of model, HA and transport."""

from contextvars import ContextVar

# Absolute asyncio loop time. Applies only until the first transport write.
send_deadline: ContextVar[float | None] = ContextVar("send_deadline", default=None)


class CommandNotReady(Exception):
    """No command bytes were submitted; waiting for a session is safe."""


class CommandBusy(Exception):
    """Another lock command is already pending or executing."""


class CommandClosed(Exception):
    """The owning integration has been unloaded."""


class CommandStateUnknown(Exception):
    """No chosen action or fresh initial report exists to invert."""
