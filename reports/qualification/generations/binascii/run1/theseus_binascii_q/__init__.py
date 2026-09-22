# generation A crc table

__all__ = ["crc32", "hexlify", "unhexlify", "Error"]


class Error(ValueError):
    pass


def _build_crc32_table():
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
        table.append(crc)
    return table


_CRC32_TABLE = _build_crc32_table()

_HEX_CHARS = b"0123456789abcdef"


def _as_bytes(data):
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    raise TypeError("argument 1 must be bytes-like")


def crc32(data, value=0):
    data = _as_bytes(data)
    crc = value ^ 0xFFFFFFFF
    for byte in data:
        crc = _CRC32_TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def hexlify(data, sep=None, bytes_per_sep=1):
    data = _as_bytes(data)
    if sep is None:
        out = bytearray(len(data) * 2)
        j = 0
        for byte in data:
            out[j] = _HEX_CHARS[byte >> 4]
            out[j + 1] = _HEX_CHARS[byte & 0x0F]
            j += 2
        return bytes(out)
    if isinstance(sep, str):
        try:
            sep = sep.encode("ascii")
        except UnicodeEncodeError:
            raise TypeError("sep must be ASCII")
    elif not isinstance(sep, (bytes, bytearray)):
        raise TypeError("sep must be bytes or ASCII string")
    if isinstance(sep, bytearray):
        sep = bytes(sep)
    if len(sep) != 1:
        raise ValueError("sep must be length 1")
    if bytes_per_sep < 1:
        raise ValueError("bytes_per_sep must be >= 1")
    parts = []
    i = 0
    n = len(data)
    while i < n:
        chunk = data[i : i + bytes_per_sep]
        piece = bytearray(len(chunk) * 2)
        j = 0
        for byte in chunk:
            piece[j] = _HEX_CHARS[byte >> 4]
            piece[j + 1] = _HEX_CHARS[byte & 0x0F]
            j += 2
        parts.append(bytes(piece))
        i += bytes_per_sep
    return sep.join(parts)


def unhexlify(hexstr):
    if isinstance(hexstr, str):
        try:
            hexstr = hexstr.encode("ascii")
        except UnicodeEncodeError:
            raise Error("Non-hexadecimal digit found")
    elif isinstance(hexstr, bytearray):
        hexstr = bytes(hexstr)
    elif isinstance(hexstr, memoryview):
        hexstr = bytes(hexstr)
    elif not isinstance(hexstr, bytes):
        raise TypeError("argument must be str or bytes-like")
    if len(hexstr) % 2:
        raise Error("Odd-length string")
    out = bytearray(len(hexstr) // 2)
    for i in range(0, len(hexstr), 2):
        hi = hexstr[i]
        lo = hexstr[i + 1]
        nhi = _hex_nibble(hi)
        if nhi < 0:
            raise Error("Non-hexadecimal digit found")
        nlo = _hex_nibble(lo)
        if nlo < 0:
            raise Error("Non-hexadecimal digit found")
        out[i // 2] = (nhi << 4) | nlo
    return bytes(out)


def _hex_nibble(c):
    if 48 <= c <= 57:
        return c - 48
    if 97 <= c <= 102:
        return c - 87
    if 65 <= c <= 70:
        return c - 55
    return -1
