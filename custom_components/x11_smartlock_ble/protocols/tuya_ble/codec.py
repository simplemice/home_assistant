"""Tuya BLE encryption, CRC and fragment encoding; pure wire format."""

import secrets
from struct import pack, unpack

from Crypto.Cipher import AES

from .const import GATT_MTU, TuyaCommandCode
from .exceptions import PacketCRCError, PacketFormatError, PacketLengthError


class PacketCodec:
    @staticmethod
    def calc_crc16(data: bytes) -> int:
        crc = 65535
        for byte in data:
            crc ^= byte & 255
            for _ in range(8):
                tmp = crc & 1
                crc >>= 1
                if tmp != 0:
                    crc ^= 40961
        return crc

    @staticmethod
    def pack_int(value: int) -> bytearray:
        curr_byte: int
        result = bytearray()
        while True:
            curr_byte = value & 127
            value >>= 7
            if value != 0:
                curr_byte |= 128
            result += pack(">B", curr_byte)
            if value == 0:
                break
        return result

    @staticmethod
    def unpack_int(data: bytes, start_pos: int) -> tuple[int, int]:
        result: int = 0
        offset: int = 0
        while offset < 5:
            pos: int = start_pos + offset
            if pos >= len(data):
                raise PacketFormatError()
            curr_byte: int = data[pos]
            result |= (curr_byte & 127) << offset * 7
            offset += 1
            if curr_byte & 128 == 0:
                break
        if offset > 4:
            raise PacketFormatError()
        else:
            return (result, start_pos + offset)

    @staticmethod
    def build_packets(
        seq_num: int,
        code: TuyaCommandCode,
        data: bytes,
        response_to: int = 0,
        *,
        login_key: bytes,
        session_key: bytes,
        protocol_version: int,
    ) -> list[bytes]:
        key: bytes
        iv = secrets.token_bytes(16)
        security_flag: bytes
        if code == TuyaCommandCode.FUN_SENDER_DEVICE_INFO:
            key = login_key
            security_flag = b"\x04"
        else:
            key = session_key
            security_flag = b"\x05"
        raw = bytearray()
        raw += pack(">IIHH", seq_num, response_to, code.value, len(data))
        raw += data
        crc = PacketCodec.calc_crc16(raw)
        raw += pack(">H", crc)
        while len(raw) % 16 != 0:
            raw += b"\x00"
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = security_flag + iv + cipher.encrypt(raw)
        command = []
        packet_num = 0
        pos = 0
        length = len(encrypted)
        while pos < length:
            packet = bytearray()
            packet += PacketCodec.pack_int(packet_num)
            if packet_num == 0:
                packet += PacketCodec.pack_int(length)
                packet_protocol_version = protocol_version
                if code == TuyaCommandCode.FUN_SENDER_DEVICE_INFO:
                    packet_protocol_version = 2
                packet += pack(">B", packet_protocol_version << 4)
            chunk_mtu = GATT_MTU
            if code == TuyaCommandCode.FUN_SENDER_DEVICE_INFO:
                chunk_mtu = 244
            data_part = encrypted[pos : pos + chunk_mtu - len(packet)]
            packet += data_part
            command.append(packet)
            pos += len(data_part)
            packet_num += 1
        return command

    @staticmethod
    def decode(envelope, key):
        """Decrypt and validate a complete message before exposing its payload."""
        if len(envelope) < 33 or (len(envelope) - 17) % 16:
            raise PacketLengthError()
        cipher = AES.new(key, AES.MODE_CBC, envelope[1:17])
        raw = cipher.decrypt(envelope[17:])
        if len(raw) < 14:
            raise PacketLengthError()
        seq, response_to, code, length = unpack(">IIHH", raw[:12])
        end = 12 + length
        if len(raw) < end + 2:
            raise PacketLengthError()
        (expected,) = unpack(">H", raw[end : end + 2])
        if PacketCodec.calc_crc16(raw[:end]) != expected:
            raise PacketCRCError()
        return seq, response_to, code, raw[12:end]
