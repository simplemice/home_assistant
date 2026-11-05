# X11 Smartlock Local BLE

Local Bluetooth control for the Tuya **X11** lock (category `jtmspro`, product `gozpr1op`, model `Q7_BLE`). No Tuya cloud calls at runtime.

Built on [asemenov566/tuya_smartlock_local_ble](https://github.com/asemenov566/tuya_smartlock_local_ble) (MIT: FD50 session, check-token unlock) with the `jtmspro` DP map confirmed in [ShonP40/Tuya-BLE](https://github.com/ShonP40/Tuya-BLE): DP46 lock, DP47 lock state, DP9 battery. See `LICENSE`.

## Status: untested on hardware
`gozpr1op` is not listed as verified in either upstream. The model reuses the common jtmspro commands; lock state, battery and unlock may differ on this firmware. Volume, direction and calibration are intentionally not exposed.

## Credentials (one-time, from iot.tuya.com API Explorer)
| Field | Source |
| --- | --- |
| UUID, Device ID, Local key | `GET /v1.0/iot-03/devices/{device_id}` |

Re-adding the lock in the Tuya app creates a **new device ID and local key**; use the current ones.

`ble_unlock_check` (DP71) has **no value in the cloud** for the X11 (Query Properties lists it without one). Leave the field empty: the integration captures DP71 from the lock over BLE once it connects. If it never reports it, unlock fails with a clear message. The X11 schema has no DP46/DP47, so there is no remote lock command and no lock-state report; it relocks automatically.

## Install
1. Copy this folder to `<config>/custom_components/x11_smartlock_ble/`, restart HA.
2. Close the Tuya/Smart Life app and disconnect any other device holding the lock (BLE locks allow one connection). Touch the keypad to wake it.
3. Settings → Devices & services → Add integration → **X11 Smartlock Local BLE**. Pick the lock, or type its MAC if it is not listed.
4. Don't run `tuya_ble` / `tuya_ble_lock` against the same lock at the same time.
