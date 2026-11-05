"""Latest user action and device reports drive the shared control direction."""

import asyncio
from contextlib import suppress

from ..domain.command_context import CommandClosed, CommandStateUnknown


class LockActions:
    """Replace pending work; never wait for physical movement or replay writes."""

    def __init__(self, model, status, commands, changed, session_policy=None):
        self._model = model
        self._status = status
        self._commands = commands
        self._session_policy = session_policy
        self._changed = changed
        self._intent = status.locked
        self.expected_action = None
        self._last_reported = status.locked
        self._busy = False
        self._closed = False
        self._revision = 0
        self._task = None
        self._admission = asyncio.Lock()
        self._unsubscribe = status.subscribe(self._reported)

    def _reported(self, locked):
        if self._closed:
            return
        previous_report = self._last_reported
        self._last_reported = locked
        if locked == self._intent and self.expected_action is not None:
            self.expected_action = "idle"
            self._changed()
        elif (
            self.expected_action in ("opening", "closing") and locked == previous_report
        ):
            # A repeated starting-position report is not a new manual action.
            return
        if not self._busy and not self._closed:
            self._intent = locked
            self._changed()

    @property
    def available(self):
        return not self._closed

    @property
    def locked(self):
        return self._intent

    @property
    def pending(self):
        return self._busy

    async def set_locked(self, locked):
        if self._closed:
            raise CommandClosed()
        requested_at = asyncio.get_running_loop().time()
        previous_intent = self._intent
        self._revision += 1
        revision = self._revision
        self._intent = locked
        self.expected_action = "closing" if locked else "opening"
        self._busy = True
        self._changed()
        task = None
        try:
            async with self._admission:
                if revision != self._revision or self._closed:
                    return
                previous = self._task
                if previous is not None and not previous.done():
                    # Cancel only local waiting/ACK tracking. A submitted motor
                    # write is not undone or replayed; send the new requested action.
                    previous.cancel()
                    try:
                        await asyncio.shield(previous)
                    except asyncio.CancelledError:
                        if asyncio.current_task().cancelling():
                            raise
                    except Exception:
                        pass
                if revision != self._revision or self._closed:
                    return
                model_action = self._model.lock if locked else self._model.unlock

                async def action():
                    await self._status.execute(model_action)

                async def admitted_action():
                    if self._session_policy is None:
                        await action()
                    else:
                        await self._session_policy.execute(action)

                operation = (
                    admitted_action()
                    if self._commands is None
                    else self._commands.execute(
                        admitted_action, requested_at=requested_at
                    )
                )
                task = self._task = asyncio.create_task(operation)
            await task
        except asyncio.CancelledError:
            if revision == self._revision:
                self._intent = self._status.locked
                self.expected_action = None
                raise
            # A newer explicit request superseded this invocation.
        except Exception:
            if revision == self._revision:
                self._intent = previous_intent
                self.expected_action = None
            raise
        finally:
            if revision == self._revision:
                self._busy = False
                if self._task is task:
                    self._task = None
                # A position received while sending may describe the starting
                # position. Keep the selected action, as the original control
                # did after ACK; later unsolicited reports resynchronize it.
                self._changed()

    async def toggle(self):
        if self.locked is None:
            raise CommandStateUnknown()
        await self.set_locked(not self.locked)

    async def close(self):
        self._closed = True
        self._unsubscribe()
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await task
