"""Own on-demand leases, polling and idle release without knowing lock DPs."""

import asyncio
import logging
from contextlib import suppress

from ..domain.command_context import CommandClosed, CommandNotReady, send_deadline

_LOGGER = logging.getLogger(__name__)


class SessionPolicy:
    """One connection owner; polling cannot close an overlapping user action."""

    def __init__(self, protocol, *, persistent=True, poll_interval=20, hold_time=10):
        self.protocol = protocol
        self.persistent = persistent
        self.poll_interval = poll_interval
        self.hold_time = hold_time
        self._gate = asyncio.Lock()
        self._users = 0
        self._hold_until = 0.0
        self._idle = None
        self._poller = None
        self._closed = False
        self._operations = set()

    @property
    def available(self):
        return not self._closed

    def start_polling(self):
        if not self.persistent and self.poll_interval:
            self._poller = asyncio.create_task(self._poll(), name="lock-status-poll")

    async def _poll(self):
        while True:
            await asyncio.sleep(self.poll_interval)
            # During a command hold we already receive live notifications.
            if self._users or asyncio.get_running_loop().time() < self._hold_until:
                continue
            try:
                await self.refresh()
            except Exception as exc:
                _LOGGER.debug("Status poll failed (%s)", type(exc).__name__)

    async def _acquire(self, connect):
        async with self._gate:
            if self._closed:
                raise CommandClosed()
            if self._idle is not None:
                self._idle.cancel()
                self._idle = None
            if not self.protocol.command_ready:
                if not connect:
                    raise CommandNotReady()
                try:
                    async with asyncio.timeout(30):
                        await self.protocol.connect()
                except BaseException:
                    if not self._users and not self.persistent:
                        await self.protocol.disconnect()
                    raise
            self._users += 1

    async def _release(self, action):
        async with self._gate:
            self._users -= 1
            if action and not self.persistent:
                self._hold_until = asyncio.get_running_loop().time() + self.hold_time
            if not self._users and not self.persistent and not self._closed:
                if self._idle is not None:
                    self._idle.cancel()
                self._idle = asyncio.create_task(self._release_when_idle())

    async def _release_when_idle(self):
        await asyncio.sleep(
            max(0, self._hold_until - asyncio.get_running_loop().time())
        )
        async with self._gate:
            if not self._users and not self._closed:
                try:
                    await self.protocol.disconnect()
                except Exception as exc:
                    _LOGGER.debug("Idle disconnect failed (%s)", type(exc).__name__)

    async def execute(self, action):
        """One attempt per invocation. No queued replay after connection failure."""
        task = asyncio.current_task()
        self._operations.add(task)
        acquired = False
        try:
            await self._acquire(connect=not self.persistent)
            acquired = True
            # No transport-initiated reconnect between admission and first byte.
            deadline = send_deadline.get()
            token = send_deadline.set(
                deadline or asyncio.get_running_loop().time() + 10
            )
            try:
                await action()
            finally:
                send_deadline.reset(token)
        finally:
            if acquired:
                await self._release(action=True)
            self._operations.discard(task)

    async def refresh(self):
        """Query all statuses and wait for a report before releasing the lease."""
        task = asyncio.current_task()
        self._operations.add(task)
        acquired = False
        try:
            await self._acquire(connect=True)
            acquired = True
            await self.protocol.query_status()
        except Exception:
            async with self._gate:
                if (
                    acquired
                    and self._users == 1
                    and asyncio.get_running_loop().time() >= self._hold_until
                ):
                    await self.protocol.disconnect()
            raise
        finally:
            if acquired:
                await self._release(action=False)
            self._operations.discard(task)

    async def close(self):
        self._closed = True
        tasks = set(self._operations)
        tasks.update(t for t in (self._idle, self._poller) if t is not None)
        tasks.discard(asyncio.current_task())
        for task in tasks:
            task.cancel()
        if tasks:
            with suppress(asyncio.CancelledError):
                await asyncio.gather(*tasks, return_exceptions=True)
