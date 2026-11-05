"""Bleak/BlueZ transport operations, without Tuya commands or lock models."""

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection


class BleTransport:
    async def connect(self, device, disconnected, current_device):
        return await establish_connection(
            BleakClientWithServiceCache,
            device,
            device.address,
            disconnected,
            use_services_cache=True,
            ble_device_callback=current_device,
        )

    async def start_notify(self, client, characteristic, callback):
        await client.start_notify(
            characteristic, callback, bluez={"use_start_notify": True}
        )

    async def write(self, client, characteristic, payload):
        await client.write_gatt_char(characteristic, payload, False)
