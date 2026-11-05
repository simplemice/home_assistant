"""Bounded, optional waiting for one lock command. No model or BLE imports."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress

from ..domain.command_context import (
    CommandBusy,
    CommandClosed,
    CommandNotReady,
    send_deadline,
)
from ..domain.contracts import LockProtocol


class LockCommandWaiter:
    """Wait for the connection owner's authenticated session; never reconnect."""

    def __init__(
        self, session: LockProtocol, changed: Callable[[], None], timeout: float = 10
    ):
        self._session = session
        self._changed = changed
        self._timeout = timeout
        self._ready = asyncio.Event()
        self._closed = False
        self._task = None
        self._unsubscribers = [
            session.register_connected_callback(self._connected),
            session.register_disconnected_callback(self._disconnected),
        ]

    @property
    def pending(self):
        return self._task is not None

    @property
    def available(self):
        """Availability means command admission, not Bluetooth connectivity."""
        return not self._closed

    def _connected(self):
        self._ready.set()
        self._changed()

    def _disconnected(self):
        self._ready.clear()
        if self._closed:
            return
        self._changed()

    async def execute(
        self, action: Callable[[], Awaitable[None]], *, requested_at=None
    ) -> None:
        if self._closed:
            raise CommandClosed()
        if self._task is not None:
            raise CommandBusy()
        self._task = asyncio.current_task()
        deadline = (
            asyncio.get_running_loop().time() if requested_at is None else requested_at
        ) + self._timeout
        token = send_deadline.set(deadline)
        try:
            self._changed()
            while True:
                async with asyncio.timeout_at(deadline):
                    self._ready.clear()
                    if not self._session.command_ready:
                        await self._ready.wait()
                if self._closed:
                    raise CommandClosed()
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError("Command expired before transmission")
                try:
                    await action()
                    return
                except CommandNotReady:
                    # The transport explicitly guarantees no write was attempted.
                    continue
        finally:
            send_deadline.reset(token)
            self._task = None
            self._changed()

    async def close(self):
        self._closed = True
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        task = self._task
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
