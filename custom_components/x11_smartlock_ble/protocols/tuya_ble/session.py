from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import Callable
from contextlib import nullcontext, suppress
from functools import partial
from struct import pack

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.exc import BleakDBusError
from bleak_retry_connector import (
    BLEAK_BACKOFF_TIME,
    BLEAK_RETRY_EXCEPTIONS,
    BleakClientWithServiceCache,
    BleakError,
    BleakNotFoundError,
)
from Crypto.Cipher import AES

from ...domain.command_context import CommandNotReady, send_deadline
from ...domain.credentials import CredentialProvider, LockCredentials
from ...domain.datapoints import DataPoint, DataPoints
from ...transports.ble import BleTransport
from .codec import PacketCodec
from .const import (
    CHARACTERISTIC_NOTIFY,
    CHARACTERISTIC_NOTIFY_FD50,
    CHARACTERISTIC_WRITE,
    CHARACTERISTIC_WRITE_FD50,
    MANUFACTURER_DATA_ID,
    RESPONSE_WAIT_TIMEOUT,
    SERVICE_UUID,
    PointType,
    TuyaCommandCode,
)
from .exceptions import (
    PacketFormatError,
    PacketLengthError,
    ProtocolError,
)
from .reports import decode_report

_LOGGER = logging.getLogger(__name__)
BLEAK_EXCEPTIONS = (*BLEAK_RETRY_EXCEPTIONS, OSError)
global_connect_lock = asyncio.Lock()


class TuyaBLEProtocol:
    protocol_id = "tuya_ble_fd50"
    # Header sub-types that count as a status answer; None accepts any live report.
    status_report_subtypes: frozenset[int] | None = frozenset({1})
    discovery_services = frozenset({"0000fd50-0000-1000-8000-00805f9b34fb", "0000a201-0000-1000-8000-00805f9b34fb"})

    def __init__(
        self,
        device_manager: CredentialProvider,
        ble_device: BLEDevice,
        advertisement_data: AdvertisementData | None = None,
    ) -> None:
        """Init the A1Ultra."""
        self._device_manager = device_manager
        self.payload_decoder = lambda data: None
        self._transport = BleTransport()
        self._device_info: LockCredentials | None = None
        self._ble_device = ble_device
        self._advertisement_data = advertisement_data
        self._operation_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        self._response_tasks: set[asyncio.Task] = set()
        self._client_cleanup_tasks: set[asyncio.Task] = set()
        self._connect_lock = asyncio.Lock()
        self._client: BleakClientWithServiceCache | None = None
        self._expected_disconnect = False
        self._stopped = False
        self.managed_connection = False
        self._connected_callbacks: list[Callable[[], None]] = []
        self._callbacks: list[Callable[[list[DataPoint]], None]] = []
        self._disconnected_callbacks: list[Callable[[], None]] = []
        self._current_seq_num = 1
        self._seq_num_lock = asyncio.Lock()
        self._characteristic_notify = CHARACTERISTIC_NOTIFY
        self._characteristic_write = CHARACTERISTIC_WRITE
        self._uses_fd50_channel = False
        self._is_bound = False
        self._flags = 0
        self._protocol_version = 2
        self._device_version: str = ""
        self._protocol_version_str: str = ""
        self._hardware_version: str = ""
        self._device_info: LockCredentials | None = None
        self._auth_key: bytes | None = None
        self._local_key: bytes | None = None
        self._login_key: bytes | None = None
        self._session_key: bytes | None = None
        self._is_paired = False
        self._input_buffer: bytearray | None = None
        self._input_expected_packet_num = 0
        self._input_expected_length = 0
        self._input_expected_responses: dict[int, asyncio.Future[int] | None] = {}
        self._datapoints = DataPoints()
        self._report_received = asyncio.Event()
        self._status_query_client = None
        self._status_query_lock = asyncio.Lock()

    def set_ble_device_and_advertisement_data(
        self, ble_device: BLEDevice, advertisement_data: AdvertisementData
    ) -> None:
        """Set the ble device."""
        self._ble_device = ble_device
        self._advertisement_data = advertisement_data

    async def initialize(self) -> None:
        _LOGGER.debug("%s: Initializing", self.address)
        if await self._update_device_info():
            self._decode_advertisement_data()

    def _build_pairing_request(self) -> bytes:
        result = bytearray()
        result += self._device_info.uuid.encode()
        result += self._local_key
        result += self._device_info.device_id.encode()
        for _ in range(44 - len(result)):
            result += b"\x00"
        return result

    async def pair(self):
        await self._send_packet(
            TuyaCommandCode.FUN_SENDER_PAIR, self._build_pairing_request()
        )

    async def update(self) -> None:
        _LOGGER.debug("%s: Updating", self.address)
        await self._send_packet(TuyaCommandCode.FUN_SENDER_DEVICE_STATUS, bytes())

    async def connect(self):
        """Establish a reusable session without a motor command."""
        if self._stopped:
            raise ProtocolError("Session is stopped")
        await self._ensure_connected()
        if not self.command_ready:
            raise ProtocolError("Session is not ready")

    async def query_status(self):
        async with self._status_query_lock:
            try:
                async with asyncio.timeout(10):
                    await self.update()
                    await self._report_received.wait()
            finally:
                self._status_query_client = None

    async def disconnect(self):
        """Release idle BLE while keeping this protocol reusable."""
        try:
            pending = tuple(self._response_tasks)
            if pending:
                try:
                    async with asyncio.timeout(5):
                        await asyncio.gather(*pending, return_exceptions=True)
                except TimeoutError:
                    pass
            await self._execute_disconnect()
            await self._wait_for_client_cleanup()
        finally:
            self._expected_disconnect = self._stopped
            self._fire_disconnected_callbacks()

    async def _update_device_info(self) -> bool:
        if self._device_info is None:
            if self._device_manager:
                self._device_info = await self._device_manager.get_device_credentials(
                    self._ble_device.address, False
                )
            if self._device_info:
                self._local_key = self._device_info.local_key[:6].encode()
                self._login_key = hashlib.md5(self._local_key).digest()
        return self._device_info is not None

    def _decode_advertisement_data(self) -> None:
        raw_product_id: bytes | None = None
        raw_uuid: bytes | None = None
        if self._advertisement_data:
            if self._advertisement_data.service_data:
                service_data = self._advertisement_data.service_data.get(SERVICE_UUID)
                if service_data and len(service_data) > 1:
                    match service_data[0]:
                        case 0:
                            raw_product_id = service_data[1:]
            if self._advertisement_data.manufacturer_data:
                manufacturer_data = self._advertisement_data.manufacturer_data.get(
                    MANUFACTURER_DATA_ID
                )
                if manufacturer_data and len(manufacturer_data) > 6:
                    self._is_bound = manufacturer_data[0] & 128 != 0
                    self._protocol_version = manufacturer_data[1]
                    raw_uuid = manufacturer_data[6:]
                    if raw_product_id:
                        key = hashlib.md5(raw_product_id).digest()
                        cipher = AES.new(key, AES.MODE_CBC, key)
                        raw_uuid = cipher.decrypt(raw_uuid)
                        self._uuid = raw_uuid.decode("utf-8")

    @property
    def address(self) -> str:
        """Return the address."""
        return self._ble_device.address

    @property
    def name(self) -> str:
        """Get the name of the device."""
        if self._device_info:
            return self._device_info.device_name
        else:
            return self._ble_device.name or self._ble_device.address

    @property
    def rssi(self) -> int | None:
        """Get the rssi of the device."""
        if self._advertisement_data:
            return self._advertisement_data.rssi
        return None

    @property
    def uuid(self) -> str:
        if self._device_info is not None:
            return self._device_info.uuid
        else:
            return ""

    @property
    def local_key(self) -> str:
        if self._device_info is not None:
            return self._device_info.local_key
        else:
            return ""

    @property
    def category(self) -> str:
        if self._device_info is not None:
            return self._device_info.category
        else:
            return ""

    @property
    def device_id(self) -> str:
        if self._device_info is not None:
            return self._device_info.device_id
        else:
            return ""

    @property
    def product_id(self) -> str:
        if self._device_info is not None:
            return self._device_info.product_id
        else:
            return ""

    @property
    def product_model(self) -> str:
        if self._device_info is not None:
            return self._device_info.product_model
        else:
            return ""

    @property
    def product_name(self) -> str:
        if self._device_info is not None:
            return self._device_info.product_name
        else:
            return ""

    @property
    def ble_unlock_check(self) -> str:
        if self._device_info is not None and self._device_info.ble_unlock_check:
            return self._device_info.ble_unlock_check
        else:
            return ""

    @property
    def device_version(self) -> str:
        return self._device_version

    @property
    def hardware_version(self) -> str:
        return self._hardware_version

    @property
    def protocol_version(self) -> str:
        return self._protocol_version_str

    @property
    def datapoints(self) -> DataPoints:
        """Get datapoints exposed by device."""
        return self._datapoints

    def _fire_connected_callbacks(self) -> None:
        """Fire the callbacks."""
        for callback in self._connected_callbacks:
            callback()

    def register_connected_callback(
        self, callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback to be called when device disconnected."""

        def unregister_callback() -> None:
            self._connected_callbacks.remove(callback)

        self._connected_callbacks.append(callback)
        return unregister_callback

    def _fire_callbacks(self, datapoints: list[DataPoint]) -> None:
        """Fire the callbacks."""
        for callback in self._callbacks:
            callback(datapoints)

    def register_callback(
        self, callback: Callable[[list[DataPoint]], None]
    ) -> Callable[[], None]:
        """Register a callback to be called when the state changes."""

        def unregister_callback() -> None:
            self._callbacks.remove(callback)

        self._callbacks.append(callback)
        return unregister_callback

    def _fire_disconnected_callbacks(self) -> None:
        """Fire the callbacks."""
        for callback in self._disconnected_callbacks:
            callback()

    def register_disconnected_callback(
        self, callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback to be called when device disconnected."""

        def unregister_callback() -> None:
            self._disconnected_callbacks.remove(callback)

        self._disconnected_callbacks.append(callback)
        return unregister_callback

    async def start(self):
        """Start the A1Ultra."""
        _LOGGER.debug("%s: Starting...", self.address)

    async def stop(self) -> None:
        """Stop the A1Ultra."""
        _LOGGER.debug("%s: Stop", self.address)
        self._stopped = True
        pending = tuple(self._response_tasks)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        try:
            await self._execute_disconnect()
        finally:
            await self._wait_for_client_cleanup()

    async def _close_client(self, client: BleakClientWithServiceCache) -> None:
        """Release backend resources even after the radio link has gone away."""
        if self._client is client:
            self._client = None
        cleanup = self._queue_client_cleanup(client)
        await asyncio.shield(cleanup)

    def _queue_client_cleanup(self, client):
        cleanup = asyncio.create_task(self._release_client(client))
        self._client_cleanup_tasks.add(cleanup)
        cleanup.add_done_callback(self._client_cleanup_tasks.discard)
        return cleanup

    async def _release_client(self, client):
        try:
            async with asyncio.timeout(10):
                await client.disconnect()
        except Exception as exc:
            _LOGGER.debug("BLE client cleanup ended (%s)", type(exc).__name__)

    async def _wait_for_client_cleanup(self) -> None:
        pending = tuple(self._client_cleanup_tasks)
        if pending:
            await asyncio.shield(asyncio.gather(*pending))

    def _session_notification(self, client, sender, data) -> None:
        """Reject delayed notifications from a retired connection."""
        if client is self._client and not self._stopped:
            self._notification_handler(sender, data)

    async def refresh_session(self) -> None:
        """Read status; discard a stale session so the next poll reconnects."""
        try:
            await self.update()
        except Exception:
            try:
                await self._execute_disconnect()
            finally:
                self._is_paired = False
                self._expected_disconnect = self._stopped
                self._fire_disconnected_callbacks()
            raise

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if client is not self._client:
            return
        was_paired = self._is_paired
        self._is_paired = False
        self._client = None
        self._clean_input()
        self._queue_client_cleanup(client)
        for future in tuple(self._input_expected_responses.values()):
            if future is not None and not future.done():
                future.set_exception(BleakError("BLE session disconnected"))
        for task in tuple(self._response_tasks):
            if task is not asyncio.current_task():
                task.cancel()
        self._fire_disconnected_callbacks()
        if self._expected_disconnect:
            _LOGGER.debug(
                "%s: Disconnected from device; RSSI: %s", self.address, self.rssi
            )
            return
        _LOGGER.debug(
            "%s: Device unexpectedly disconnected; RSSI: %s", self.address, self.rssi
        )
        if was_paired and (not self.managed_connection):
            _LOGGER.debug("%s: Scheduling reconnect; RSSI: %s", self.address, self.rssi)
            asyncio.create_task(self._reconnect())

    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        async with self._connect_lock:
            client = self._client
            self._expected_disconnect = True
            self._client = None
            if client:
                try:
                    if client.is_connected:
                        await client.stop_notify(self._characteristic_notify)
                finally:
                    await self._close_client(client)
        async with self._seq_num_lock:
            self._current_seq_num = 1
        self._is_paired = False
        self._clean_input()

    def _select_characteristics(self, client: BleakClientWithServiceCache) -> None:
        """Select the GATT channel actually exposed by the device."""
        if client.services.get_characteristic(CHARACTERISTIC_NOTIFY):
            self._characteristic_notify = CHARACTERISTIC_NOTIFY
            self._characteristic_write = CHARACTERISTIC_WRITE
        elif client.services.get_characteristic(CHARACTERISTIC_NOTIFY_FD50):
            _LOGGER.debug(
                "%s: legacy characteristics not present, using FD50 GATT channel",
                self.address,
            )
            self._characteristic_notify = CHARACTERISTIC_NOTIFY_FD50
            self._characteristic_write = CHARACTERISTIC_WRITE_FD50
            self._uses_fd50_channel = True

    async def _ensure_connected(self) -> None:
        """Ensure connection to device is established."""
        global global_connect_lock
        if self._expected_disconnect:
            return
        if self._connect_lock.locked():
            _LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.address,
                self.rssi,
            )
        if self._client and self._client.is_connected and self._is_paired:
            return
        async with self._connect_lock:
            await asyncio.sleep(0.01)
            if self._client and self._client.is_connected and self._is_paired:
                return
            attempts_count = 4
            while attempts_count > 0:
                await self._wait_for_client_cleanup()
                attempts_count -= 1
                if attempts_count == 0:
                    _LOGGER.error(
                        "%s: Connecting, all attempts failed; RSSI: %s",
                        self.address,
                        self.rssi,
                    )
                    raise BleakNotFoundError()
                try:
                    async with global_connect_lock:
                        _LOGGER.debug(
                            "%s: Connecting; RSSI: %s", self.address, self.rssi
                        )
                        client = await self._transport.connect(
                            self._ble_device,
                            self._disconnected,
                            lambda: self._ble_device,
                        )
                except BleakNotFoundError:
                    _LOGGER.error(
                        "%s: device not found, not in range, or poor RSSI: %s",
                        self.address,
                        self.rssi,
                        exc_info=True,
                    )
                    continue
                except BLEAK_EXCEPTIONS:
                    _LOGGER.debug(
                        "%s: communication failed", self.address, exc_info=True
                    )
                    continue
                except Exception:
                    _LOGGER.debug("%s: unexpected error", self.address, exc_info=True)
                    continue
                if client and client.is_connected:
                    _LOGGER.debug("%s: Connected; RSSI: %s", self.address, self.rssi)
                    self._client = client
                    self._select_characteristics(client)
                    try:
                        await self._transport.start_notify(
                            self._client,
                            self._characteristic_notify,
                            partial(self._session_notification, client),
                        )
                    except Exception:
                        await self._close_client(client)
                        self._client = None
                        _LOGGER.error(
                            "%s: starting notifications failed",
                            self.address,
                            exc_info=True,
                        )
                        continue
                else:
                    continue
                if self._client and self._client.is_connected:
                    _LOGGER.debug("%s: Sending device info request", self.address)
                    try:
                        device_info_payload = b"\x00\xf3"
                        if not await self._send_packet_while_connected(
                            TuyaCommandCode.FUN_SENDER_DEVICE_INFO,
                            device_info_payload,
                            0,
                            True,
                        ):
                            await self._close_client(client)
                            self._client = None
                            _LOGGER.error(
                                "%s: Sending device info request failed", self.address
                            )
                            continue
                    except Exception:
                        await self._close_client(client)
                        self._client = None
                        _LOGGER.error(
                            "%s: Sending device info request failed",
                            self.address,
                            exc_info=True,
                        )
                        continue
                else:
                    continue
                if self._client and self._client.is_connected:
                    _LOGGER.debug("%s: Sending pairing request", self.address)
                    try:
                        if not await self._send_packet_while_connected(
                            TuyaCommandCode.FUN_SENDER_PAIR,
                            self._build_pairing_request(),
                            0,
                            True,
                        ):
                            await self._close_client(client)
                            self._client = None
                            _LOGGER.error(
                                "%s: Sending pairing request failed", self.address
                            )
                            continue
                    except Exception:
                        await self._close_client(client)
                        self._client = None
                        _LOGGER.error(
                            "%s: Sending pairing request failed",
                            self.address,
                            exc_info=True,
                        )
                        continue
                else:
                    continue
                break
        if self._client:
            if self._client.is_connected:
                if self._is_paired:
                    _LOGGER.debug("%s: Successfully connected", self.address)
                    self._fire_connected_callbacks()
                else:
                    _LOGGER.error("%s: Connected but not paired", self.address)
            else:
                _LOGGER.error("%s: Not connected", self.address)
        else:
            _LOGGER.error("%s: No client device", self.address)

    async def _reconnect(self) -> None:
        """Attempt a reconnect"""
        _LOGGER.debug("%s: Reconnect, ensuring connection", self.address)
        async with self._seq_num_lock:
            self._current_seq_num = 1
        try:
            if self._expected_disconnect:
                return
            await self._ensure_connected()
            if self._expected_disconnect:
                return
            _LOGGER.debug("%s: Reconnect, connection ensured", self.address)
        except BLEAK_EXCEPTIONS:
            _LOGGER.debug(
                "%s: Reconnect, failed to ensure connection - backing off",
                self.address,
                exc_info=True,
            )
            await asyncio.sleep(BLEAK_BACKOFF_TIME)
            _LOGGER.debug("%s: Reconnecting again", self.address)
            asyncio.create_task(self._reconnect())

    async def _get_seq_num(self) -> int:
        async with self._seq_num_lock:
            result = self._current_seq_num
            self._current_seq_num += 1
        return result

    async def _send_packet(
        self, code: TuyaCommandCode, data: bytes, wait_for_response: bool = True
    ) -> None:
        """Send packet to device and optional read response."""
        if self._expected_disconnect:
            raise ProtocolError("BLE device has been stopped")
        await self._ensure_connected()
        if self._expected_disconnect:
            raise ProtocolError("BLE device has been stopped")
        if not await self._send_packet_while_connected(
            code, data, 0, wait_for_response
        ):
            raise TimeoutError("BLE response timed out")

    def _queue_response(self, code, data, response_to):
        """Own notification replies and bind them to the receiving session."""
        if self._stopped or self._client is None:
            return
        task = asyncio.create_task(
            self._send_response(code, data, response_to, self._client)
        )
        self._response_tasks.add(task)
        task.add_done_callback(self._response_tasks.discard)

    async def _send_response(self, code, data, response_to, client=None) -> None:
        """Reply without waiting behind a request that needs this response."""
        client = client or self._client
        if client is None or self._stopped:
            return
        try:
            await self._send_packet_while_connected(
                code, data, response_to, False, expected_client=client
            )
        except Exception as exc:
            _LOGGER.debug("BLE reply ended (%s)", type(exc).__name__)

    async def _send_packet_while_connected(
        self, code, data, response_to, wait_for_response, *, expected_client=None
    ) -> bool:
        # Serialize requests, but allow replies while a request awaits its ACK.
        async with self._request_lock if wait_for_response else nullcontext():
            return await self._send_packet_while_connected_locked(
                code, data, response_to, wait_for_response, expected_client
            )

    async def _send_packet_while_connected_locked(
        self, code, data, response_to, wait_for_response, expected_client=None,
        send_window=None,
    ) -> bool:
        future = None
        seq_num = None
        try:
            # Fragments must stay contiguous; the ACK wait must not hold this lock.
            async with self._operation_lock:
                command_client = self._client
                if send_window is not None and not self.command_ready:
                    raise CommandNotReady()
                if expected_client is not None and (
                    self._stopped
                    or self._client is not expected_client
                    or not expected_client.is_connected
                ):
                    return False
                seq_num = await self._get_seq_num()
                if wait_for_response:
                    future = asyncio.get_running_loop().create_future()
                    self._input_expected_responses[seq_num] = future
                _LOGGER.debug("BLE send #%s %s reply-to #%s", seq_num, code.name, response_to)
                packets = self._build_packets(seq_num, code, data, response_to)
                def admit_write():
                    # Run inside the writer task, with no scheduling gap before
                    # the transport call. Queued callbacks can retire a session
                    # or consume the deadline after the parent builds its frame.
                    if self._client is not command_client or (
                        expected_client is not None
                        and (self._stopped or not expected_client.is_connected)
                    ):
                        raise CommandNotReady()
                    if send_window is not None:
                        if not self.command_ready:
                            raise CommandNotReady()
                        if asyncio.get_running_loop().time() >= send_window.when():
                            raise TimeoutError("Command expired before transmission")
                        # After this point delivery is ambiguous: never retry.
                        send_window.reschedule(None)
                    if code == TuyaCommandCode.FUN_SENDER_DEVICE_STATUS:
                        self._report_received.clear()
                        self._status_query_client = command_client

                await self._write_fragments_atomically(packets, admit_write)
            if future is not None:
                try:
                    await asyncio.wait_for(future, RESPONSE_WAIT_TIMEOUT)
                except TimeoutError:
                    return False
            return True
        finally:
            if seq_num is not None:
                self._input_expected_responses.pop(seq_num, None)
            if future is not None:
                if not future.done():
                    future.cancel()
                elif not future.cancelled():
                    future.exception()  # Also consume a disconnect during a failed write.

    async def _write_fragments_atomically(self, packets, admit_write=None):
        """Finish an already-started frame before cancelling local ACK waiting."""
        owner = asyncio.current_task()
        async def write():
            async with asyncio.timeout(RESPONSE_WAIT_TIMEOUT):
                if owner.cancelling():
                    raise asyncio.CancelledError
                if admit_write is not None:
                    admit_write()
                await self._int_send_packet_while_connected(packets)

        task = asyncio.create_task(write())
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
            except Exception:
                break
        if cancelled:
            # Repeated replacements must not cancel the shielded frame either.
            with suppress(Exception, asyncio.CancelledError):
                task.result()
            raise asyncio.CancelledError
        task.result()

    async def _int_send_packet_while_connected(self, packets: list[bytes]) -> None:
        try:
            await self._send_packets_locked(packets)
        except BleakNotFoundError:
            _LOGGER.error(
                "%s: device not found, no longer in range, or poor RSSI: %s",
                self.address,
                self.rssi,
                exc_info=True,
            )
            raise
        except BLEAK_EXCEPTIONS:
            _LOGGER.error("%s: communication failed", self.address, exc_info=True)
            raise

    async def _send_packets_locked(self, packets: list[bytes]) -> None:
        """Send command to device and read response."""
        try:
            await self._int_send_packets_locked(packets)
        except BleakDBusError as ex:
            await asyncio.sleep(BLEAK_BACKOFF_TIME)
            _LOGGER.debug(
                "%s: RSSI: %s; Backing off %ss; Disconnecting due to error: %s",
                self.address,
                self.rssi,
                BLEAK_BACKOFF_TIME,
                ex,
            )
            if not self.managed_connection and (not self._is_paired):
                asyncio.create_task(self._reconnect())
            raise BleakError from ex
        except BleakError as ex:
            _LOGGER.debug(
                "%s: RSSI: %s; Disconnecting due to error: %s",
                self.address,
                self.rssi,
                ex,
            )
            if not self.managed_connection and (not self._is_paired):
                asyncio.create_task(self._reconnect())
            raise

    async def _int_send_packets_locked(self, packets: list[bytes]) -> None:
        """Execute command and read response."""
        for packet in packets:
            if self._client:
                try:
                    await self._transport.write(
                        self._client, self._characteristic_write, packet
                    )
                except Exception:
                    _LOGGER.error(
                        "%s: Error during sending packet", self.address, exc_info=True
                    )
                    if self._client and self._client.is_connected:
                        self._disconnected(self._client)
                    raise BleakError()
            else:
                _LOGGER.error(
                    "%s: Client disconnected during sending packet",
                    self.address,
                    exc_info=True,
                )
                raise BleakError()

    def _get_key(self, security_flag: int) -> bytes:
        if security_flag == 1:
            return self._auth_key
        if security_flag == 4:
            return self._login_key
        elif security_flag == 5:
            return self._session_key
        else:
            pass

    def _parse_timestamp(self, data: bytes, start_pos: int) -> tuple(float, int):
        timestamp: float
        pos = start_pos
        if pos >= len(data):
            raise PacketLengthError()
        time_type = data[pos]
        pos += 1
        end_pos = pos
        match time_type:
            case 0:
                end_pos += 13
                if end_pos > len(data):
                    raise PacketLengthError()
                timestamp = int(data[pos:end_pos].decode()) / 1000
                pass
            case 1:
                end_pos += 4
                if end_pos > len(data):
                    raise PacketLengthError()
                timestamp = int.from_bytes(data[pos:end_pos], "big") * 1.0
                pass
            case _:
                raise PacketFormatError()
        _LOGGER.debug("%s: Received timestamp: %s", self.address, time.ctime(timestamp))
        return (timestamp, end_pos)

    def _parse_datapoints_v3(
        self, timestamp: float, flags: int, data: bytes, start_pos: int
    ) -> int:
        datapoints: list[DataPoint] = []
        pos = start_pos
        while len(data) - pos >= 4:
            id: int = data[pos]
            pos += 1
            _type: int = data[pos]
            if _type > PointType.DT_BITMAP.value:
                raise PacketFormatError()
            type: PointType = PointType(_type)
            pos += 1
            data_len: int = data[pos]
            pos += 1
            next_pos = pos + data_len
            if next_pos > len(data):
                raise PacketLengthError()
            raw_value = data[pos:next_pos]
            match type:
                case PointType.DT_RAW | PointType.DT_BITMAP:
                    value = raw_value
                case PointType.DT_BOOL:
                    value = int.from_bytes(raw_value, "big") != 0
                case PointType.DT_VALUE | PointType.DT_ENUM:
                    value = int.from_bytes(raw_value, "big", signed=True)
                case PointType.DT_STRING:
                    value = raw_value.decode()
            pass
            self._datapoints._update_from_device(id, timestamp, flags, type, value)
            datapoints.append(self._datapoints[id])
            pos = next_pos
        self._fire_callbacks(datapoints)

    def _parse_datapoints_v4(self, data: bytes, *, timestamped=False):
        report = decode_report(data, timestamped=timestamped)
        self.payload_decoder(report)
        if (
            not timestamped
            and (
                self.status_report_subtypes is None
                or (report.header[5] & 0x7F) in self.status_report_subtypes
            )
            and self._status_query_client is not None
            and self._status_query_client is self._client
        ):
            self._report_received.set()
        return report

    def _handle_command_or_response(
        self, seq_num: int, response_to: int, code: TuyaCommandCode, data: bytes
    ) -> None:
        result: int = 0
        match code:
            case TuyaCommandCode.FUN_SENDER_DPS_V4:
                result = data[5] if len(data) == 6 and data[0] == 0 else -1
            case TuyaCommandCode.FUN_SENDER_DEVICE_INFO:
                if len(data) < 46:
                    raise PacketLengthError()
                self._device_version = "%s.%s" % (data[0], data[1])
                self._protocol_version_str = "%s.%s" % (data[2], data[3])
                self._hardware_version = "%s.%s" % (data[12], data[13])
                self._protocol_version = data[2]
                self._flags = data[4]
                self._is_bound = data[5] != 0
                srand = data[6:12]
                self._session_key = hashlib.md5(self._local_key + srand).digest()
                self._auth_key = data[14:46]
            case TuyaCommandCode.FUN_SENDER_PAIR:
                if len(data) != 1:
                    raise PacketLengthError()
                result = data[0]
                if result == 2:
                    _LOGGER.debug("%s: Device is already paired", self.address)
                    result = 0
                self._is_paired = result == 0
            case TuyaCommandCode.FUN_SENDER_DEVICE_STATUS:
                if len(data) != 1:
                    raise PacketLengthError()
                result = data[0]
            case TuyaCommandCode.FUN_RECEIVE_TIME1_REQ:
                if len(data) != 0:
                    raise PacketLengthError()
                timestamp = int(time.time_ns() / 1000000)
                timezone = -int(time.timezone / 36)
                data = str(timestamp).encode() + pack(">h", timezone)
                self._queue_response(code, data, seq_num)
            case TuyaCommandCode.FUN_RECEIVE_TIME2_REQ:
                if len(data) != 0:
                    raise PacketLengthError()
                time_str: time.struct_time = time.localtime()
                timezone = -int(time.timezone / 36)
                data = pack(
                    ">BBBBBBBh",
                    time_str.tm_year % 100,
                    time_str.tm_mon,
                    time_str.tm_mday,
                    time_str.tm_hour,
                    time_str.tm_min,
                    time_str.tm_sec,
                    time_str.tm_wday,
                    timezone,
                )
                self._queue_response(code, data, seq_num)
            case TuyaCommandCode.FUN_RECEIVE_DP:
                self._parse_datapoints_v3(time.time(), 0, data, 0)
                self._queue_response(code, bytes(0), seq_num)
            case TuyaCommandCode.FUN_RECEIVE_SIGN_DP:
                dp_seq_num = int.from_bytes(data[:2], "big")
                flags = data[2]
                self._parse_datapoints_v3(time.time(), flags, data, 2)
                data = pack(">HBB", dp_seq_num, flags, 0)
                self._queue_response(code, data, seq_num)
            case TuyaCommandCode.FUN_RECEIVE_TIME_DP:
                timestamp: float
                pos: int
                timestamp, pos = self._parse_timestamp(data, 0)
                self._parse_datapoints_v3(timestamp, 0, data, pos)
                self._queue_response(code, bytes(0), seq_num)
            case TuyaCommandCode.FUN_RECEIVE_SIGN_TIME_DP:
                timestamp: float
                pos: int
                dp_seq_num = int.from_bytes(data[:2], "big")
                flags = data[2]
                timestamp, pos = self._parse_timestamp(data, 3)
                self._parse_datapoints_v3(time.time(), flags, data, pos)
                data = pack(">HBB", dp_seq_num, flags, 0)
                self._queue_response(code, data, seq_num)
            case (
                TuyaCommandCode.FUN_RECEIVE_DP_V4
                | TuyaCommandCode.FUN_RECEIVE_TIME_DP_V4
            ):
                try:
                    report = self._parse_datapoints_v4(
                        data, timestamped=code == TuyaCommandCode.FUN_RECEIVE_TIME_DP_V4)
                except ValueError:
                    _LOGGER.debug(
                        "Ignored malformed V4 report (%s bytes) %s%s",
                        len(data),
                        "[timestamped] " if code == TuyaCommandCode.FUN_RECEIVE_TIME_DP_V4 else "",
                        data.hex(),
                    )
                else:
                    if not report.header[5] & 0x80:
                        self._queue_response(code, report.acknowledgement, seq_num)
        if response_to != 0:
            future = self._input_expected_responses.pop(response_to, None)
            if future and (not future.done()):
                _LOGGER.debug(
                    "%s: Received expected response to #%s, result: %s",
                    self.address,
                    response_to,
                    result,
                )
                if result == 0:
                    future.set_result(result)
                else:
                    future.set_exception(ProtocolError(result))

    def _clean_input(self) -> None:
        self._input_buffer = None
        self._input_expected_packet_num = 0
        self._input_expected_length = 0

    def _parse_input(self) -> None:
        if (
            self._input_buffer is None
            or len(self._input_buffer) < 33
            or (len(self._input_buffer) - 17) % 16
        ):
            self._clean_input()
            raise PacketLengthError()
        security_flag = self._input_buffer[0]
        key = self._get_key(security_flag)
        envelope = bytes(self._input_buffer)
        self._clean_input()
        seq_num, response_to, _code, data = PacketCodec.decode(envelope, key)
        code: TuyaCommandCode
        try:
            code = TuyaCommandCode(_code)
        except ValueError:
            pass
            return
        if response_to != 0:
            _LOGGER.debug(
                "%s: Received: #%s %s, response to #%s",
                self.address,
                seq_num,
                code.name,
                response_to,
            )
        else:
            _LOGGER.debug("%s: Received: #%s %s", self.address, seq_num, code.name)
        self._handle_command_or_response(seq_num, response_to, code, data)

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""
        pass
        pos: int = 0
        packet_num: int
        packet_num, pos = PacketCodec.unpack_int(data, pos)
        if packet_num < self._input_expected_packet_num:
            _LOGGER.error(
                "%s: Unexpcted packet (number %s) in notifications, expected %s",
                self.address,
                packet_num,
                self._input_expected_packet_num,
            )
            self._clean_input()
        if packet_num == self._input_expected_packet_num:
            if packet_num == 0:
                self._input_buffer = bytearray()
                self._input_expected_length, pos = PacketCodec.unpack_int(data, pos)
                if not 33 <= self._input_expected_length <= 4096:
                    self._clean_input()
                    return
                pos += 1
            self._input_buffer += data[pos:]
            self._input_expected_packet_num += 1
        else:
            _LOGGER.error(
                "%s: Missing packet (number %s) in notifications, received %s",
                self.address,
                self._input_expected_packet_num,
                packet_num,
            )
            self._clean_input()
            return
        if len(self._input_buffer) > self._input_expected_length:
            _LOGGER.error(
                "%s: Unexpcted length of data in notifications, received %s expected %s",
                self.address,
                len(self._input_buffer),
                self._input_expected_length,
            )
            self._clean_input()
            return
        elif len(self._input_buffer) == self._input_expected_length:
            self._parse_input()

    def _build_packets(self, seq_num, code, data, response_to=0):
        return PacketCodec.build_packets(
            seq_num,
            code,
            data,
            response_to,
            login_key=self._login_key,
            session_key=self._session_key,
            protocol_version=self._protocol_version,
        )

    @property
    def command_ready(self):
        return bool(
            not self._stopped and not self._expected_disconnect
            and self._client and self._client.is_connected and self._is_paired
        )

    async def send_command(self, payload):
        """Send one model payload. Never replay actuator writes."""
        deadline = send_deadline.get()
        if deadline is not None:
            # The application service waits for the connection manager. This
            # path cannot initiate a second connection or send after its expiry.
            async with asyncio.timeout_at(deadline) as window:
                async with self._request_lock:
                    sent = await self._send_packet_while_connected_locked(
                        TuyaCommandCode.FUN_SENDER_DPS_V4, payload, 0, True,
                        send_window=window,
                    )
            if not sent:
                raise TimeoutError("BLE response timed out; command not replayed")
            return
        await self._send_packet(TuyaCommandCode.FUN_SENDER_DPS_V4, payload, True)

    def publish(self, points):
        """Publish decoded or acknowledged model state."""
        self._fire_callbacks(points)
