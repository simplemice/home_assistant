"""Own active protocol sessions and their retry tasks. No lock commands."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

from .application.session_policy import SessionPolicy
from .keepalive import maintain_connection


@dataclass
class Connection:
    protocol: object
    policy: object = None
    task: asyncio.Task | None = None
    unsubscribe: Callable[[], None] | None = None


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, Connection] = {}

    async def start(
        self, key, protocol, keep_connected=True, *, poll_interval=20, hold_time=10
    ):
        if key in self._connections:
            raise ValueError("Connection already owned")
        policy = SessionPolicy(
            protocol,
            persistent=keep_connected,
            poll_interval=poll_interval,
            hold_time=hold_time,
        )
        connection = Connection(protocol, policy)
        self._connections[key] = connection
        protocol.managed_connection = True
        disconnected = asyncio.Event()
        if keep_connected:
            connection.unsubscribe = protocol.register_disconnected_callback(
                disconnected.set
            )
        try:
            await protocol.initialize()
            if keep_connected:
                disconnected.set()
                connection.task = asyncio.create_task(
                    maintain_connection(policy.refresh, disconnected=disconnected),
                    name=f"lock-connection-{key}",
                )
            else:
                policy.start_polling()
            return policy
        except BaseException:
            await self.close(key)
            raise

    async def close(self, key):
        connection = self._connections.pop(key, None)
        if connection is None:
            return
        if connection.unsubscribe is not None:
            connection.unsubscribe()
        try:
            if connection.task is not None:
                connection.task.cancel()
                with suppress(asyncio.CancelledError):
                    await connection.task
        finally:
            # A failed heartbeat must not prevent releasing the BLE client.
            try:
                await connection.policy.close()
            finally:
                await connection.protocol.stop()

    async def close_all(self):
        errors = []
        for key in list(self._connections):
            try:
                await self.close(key)
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup("Could not close all BLE sessions cleanly", errors)
