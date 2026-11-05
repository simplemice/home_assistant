"""One cancellable, read-only heartbeat per persistent BLE session."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

_LOGGER = logging.getLogger(__name__)


async def maintain_connection(
    refresh: Callable[[], Awaitable[None]],
    *,
    interval: float = 30,
    max_delay: float = 120,
    timeout: float = 90,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    disconnected: asyncio.Event | None = None,
) -> None:
    """Request status, never write an actuator/password datapoint.

    The caller owns and cancels this task on unload. Sequential refreshes
    cannot accumulate if an adapter is slow. Cancellation must propagate.
    """
    delay = interval
    retrying = False
    while True:
        if disconnected is None or retrying:
            await sleep(delay)
        else:
            try:
                await asyncio.wait_for(disconnected.wait(), delay)
            except TimeoutError:
                pass
            else:
                await sleep(1)  # Let BlueZ release the link; coalesce callbacks.
        if disconnected is not None:
            disconnected.clear()
        try:
            async with asyncio.timeout(timeout):
                await refresh()
        except Exception as exc:
            # Do not log credentials, decrypted frames or exception messages.
            _LOGGER.debug("BLE heartbeat failed (%s); retrying", type(exc).__name__)
            delay = min(max_delay, delay * 2) if retrying or disconnected is None else 2
            retrying = True
        else:
            delay = interval
            retrying = False
