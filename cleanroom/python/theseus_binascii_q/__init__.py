"""
theseus_binascii_q — Clean-room hexlify / unhexlify / CRC-32.
Do NOT import binascii.
"""


class Error(ValueError):
    """Raised on invalid hex input."""


def hexlify(data):
    return bytes(data).hex().encode("ascii")


def unhexlify(data):
    if isinstance(data, bytes):
        text = data.decode("ascii")
    else:
        text = str(data)
    if len(text) % 2:
        raise Error("Odd-length string")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise Error(str(exc))


def crc32(data, value=0):
    crc = (value & 0xFFFFFFFF) ^ 0xFFFFFFFF
    for byte in bytes(data):
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


__all__ = ["crc32", "hexlify", "unhexlify", "Error"]
