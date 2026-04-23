"""
theseus_binascii_cr — Clean-room binascii module.
No import of the standard `binascii` module.
"""

import zlib as _zlib

_HEX_CHARS = b'0123456789abcdef'
_HEX_UPPER = b'0123456789ABCDEF'


def hexlify(data, sep=None, bytes_per_sep=1):
    """Convert binary data to its hexadecimal representation."""
    if isinstance(data, str):
        data = data.encode('latin-1')
    result = bytearray()
    for b in data:
        result.append(_HEX_CHARS[b >> 4])
        result.append(_HEX_CHARS[b & 0xF])
    if sep is not None:
        sep_bytes = sep.encode() if isinstance(sep, str) else bytes(sep)
        if bytes_per_sep > 0:
            parts = []
            hex_str = bytes(result)
            step = bytes_per_sep * 2
            for i in range(0, len(hex_str), step):
                parts.append(hex_str[i:i + step])
            result = bytearray(sep_bytes.join(parts))
    return bytes(result)


def unhexlify(hexstr):
    """Decode hexadecimal string to binary data."""
    if isinstance(hexstr, str):
        hexstr = hexstr.encode('ascii')
    if len(hexstr) % 2 != 0:
        raise ValueError("Odd-length string")
    result = bytearray()
    for i in range(0, len(hexstr), 2):
        high = chr(hexstr[i]).lower()
        low = chr(hexstr[i + 1]).lower()
        result.append(int(high + low, 16))
    return bytes(result)


_B64_CHARS = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'


def b2a_base64(data, *, newline=True):
    """Convert binary data to base64-encoded ASCII bytes."""
    if isinstance(data, str):
        data = data.encode('latin-1')
    result = bytearray()
    n = len(data)
    i = 0
    while i < n:
        b0 = data[i]
        b1 = data[i + 1] if i + 1 < n else 0
        b2 = data[i + 2] if i + 2 < n else 0
        result.append(_B64_CHARS[(b0 >> 2) & 0x3F])
        result.append(_B64_CHARS[((b0 & 3) << 4) | ((b1 >> 4) & 0xF)])
        if i + 1 < n:
            result.append(_B64_CHARS[((b1 & 0xF) << 2) | ((b2 >> 6) & 3)])
        else:
            result.append(ord('='))
        if i + 2 < n:
            result.append(_B64_CHARS[b2 & 0x3F])
        else:
            result.append(ord('='))
        i += 3
    if newline:
        result.append(ord('\n'))
    return bytes(result)


_B64_DECODE = [-1] * 256
for _i, _c in enumerate(_B64_CHARS):
    _B64_DECODE[_c] = _i


def a2b_base64(data):
    """Convert a block of base64 data back to binary."""
    if isinstance(data, str):
        data = data.encode('ascii')
    data = bytes(b for b in data if b not in b' \t\r\n')
    n = len(data)
    pad = 0
    while n > 0 and data[n - 1] == ord('='):
        pad += 1
        n -= 1
    result = bytearray()
    i = 0
    while i < n:
        c0 = _B64_DECODE[data[i]] if i < n else 0
        c1 = _B64_DECODE[data[i + 1]] if i + 1 < n else 0
        c2 = _B64_DECODE[data[i + 2]] if i + 2 < n else 0
        c3 = _B64_DECODE[data[i + 3]] if i + 3 < n else 0
        result.append((c0 << 2) | (c1 >> 4))
        if i + 2 < n or pad < 2:
            result.append(((c1 & 0xF) << 4) | (c2 >> 2))
        if i + 3 < n or pad < 1:
            result.append(((c2 & 3) << 6) | c3)
        i += 4
    return bytes(result)


def crc32(data, value=0):
    """Compute CRC-32 checksum."""
    return _zlib.crc32(data, value)


def crc_hqx(data, value):
    """Compute CRC-CCITT checksum (CRC-16)."""
    CRC_CCITT_TABLE = []
    for i in range(256):
        crc = i << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
        CRC_CCITT_TABLE.append(crc)

    for byte in data:
        value = ((value << 8) & 0xFF00) ^ CRC_CCITT_TABLE[((value >> 8) ^ byte) & 0xFF]
    return value


def b2a_hex(data, sep=None, bytes_per_sep=1):
    """Alias for hexlify."""
    return hexlify(data, sep, bytes_per_sep)


def a2b_hex(hexstr):
    """Alias for unhexlify."""
    return unhexlify(hexstr)


def b2a_uu(data):
    """Encode binary data to UU encoding."""
    if len(data) > 45:
        raise ValueError("At most 45 bytes at once")
    result = bytearray()
    result.append(32 + len(data))
    i = 0
    data = data + b'\x00\x00'
    while i < len(data) - 2:
        b0, b1, b2 = data[i], data[i + 1], data[i + 2]
        result.append(32 + ((b0 >> 2) & 0x3F) or 96)
        result.append(32 + (((b0 & 3) << 4) | (b1 >> 4)) or 96)
        result.append(32 + (((b1 & 0xF) << 2) | (b2 >> 6)) or 96)
        result.append(32 + (b2 & 0x3F) or 96)
        i += 3
    result.append(ord('\n'))
    return bytes(result)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def binascii2_hexlify():
    """hexlify(b'hello') returns b'68656c6c6f'; returns the hex string."""
    return hexlify(b'hello').decode('ascii')


def binascii2_unhexlify():
    """unhexlify('68656c6c6f') returns b'hello'; returns the string."""
    return unhexlify('68656c6c6f').decode('ascii')


def binascii2_crc32():
    """crc32 returns an integer; returns True."""
    result = crc32(b'hello world')
    return isinstance(result, int)


__all__ = [
    'hexlify', 'unhexlify', 'b2a_hex', 'a2b_hex',
    'b2a_base64', 'a2b_base64',
    'crc32', 'crc_hqx',
    'binascii2_hexlify', 'binascii2_unhexlify', 'binascii2_crc32',
]
