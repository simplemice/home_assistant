from __future__ import annotations


class A1UltraError(Exception):
    """Base class for Tuya BLE errors."""


class InvalidEnumValue(A1UltraError):
    """Raised when value assigned to DP_ENUM datapoint has unexpected type."""

    def __init__(self) -> None:
        super().__init__("Value of DP_ENUM datapoint must be unsigned integer")


class PacketFormatError(A1UltraError):
    """Raised when data in Tuya BLE structures formatted in wrong way."""

    def __init__(self) -> None:
        super().__init__("Incoming packet is formatted in wrong way")


class PacketCRCError(A1UltraError):
    """Raised when data packet has invalid CRC."""

    def __init__(self) -> None:
        super().__init__("Incoming packet has invalid CRC")


class PacketLengthError(A1UltraError):
    """Raised when data packet has invalid length."""

    def __init__(self) -> None:
        super().__init__("Incoming packet has invalid length")


class ProtocolError(A1UltraError):
    """Raised when Tuya BLE device returned error in response to command."""

    def __init__(self, code: int | str) -> None:
        if isinstance(code, str):
            super().__init__(code)
        else:
            super().__init__(("BLE device returned error code %s") % (code))
