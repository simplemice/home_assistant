"""Device-specific check-token unlock. Reusable by compatible lock models."""

import base64

from ..exceptions import PacketLengthError, ProtocolError


class CheckTokenUnlock:
    def __init__(self, credentials):
        self.credentials = credentials

    async def execute(self, protocol):
        await protocol.send_command(self.payload())

    def payload(self) -> bytes:
        """Build the A1 Ultra/TuyaOS FD50 V4 remote-unlock payload.

        `ble_unlock_check` is a base64 encoded raw Tuya status field. For the
        verified lock it decodes to:
        00 01 ff ff <8 ASCII digits> 01 <4 bytes> 00 00

        The V4 command payload sent by the official app is:
        00000000 01 47 000013 ffff 0001 <8 ASCII digits> 01 <4 bytes> 00 01
        """
        if not self.credentials.ble_unlock_check:
            raise ProtocolError(
                "This TuyaOS FD50 lock requires the device-specific ble_unlock_check value in the integration configuration"
            )
        try:
            check = base64.b64decode(self.credentials.ble_unlock_check, validate=True)
        except Exception as exc:
            raise ProtocolError(
                "ble_unlock_check must be a valid base64 Tuya status value"
            ) from exc
        if len(check) < 19:
            raise PacketLengthError()
        prefix = check[2:4]
        check_code = check[4:12]
        check_key = check[13:17]
        return (
            b"\x00\x00\x00\x00\x01G\x00\x00\x13"
            + prefix
            + b"\x00\x01"
            + check_code
            + b"\x01"
            + check_key
            + b"\x00\x01"
        )
