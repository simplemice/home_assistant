"""Integration identity and private credential path for X11 Smartlock Local BLE."""

from typing import Final

DOMAIN: Final = "x11_smartlock_ble"
CONF_KEEP_CONNECTED: Final = "keep_connected"
CONF_WAIT_FOR_RECONNECT: Final = "wait_for_reconnect"
CONF_POLL_INTERVAL: Final = "poll_interval"
CONF_HOLD_TIME: Final = "hold_time"
CONF_CRED_FILE: Final = DOMAIN + "/devices.json"
