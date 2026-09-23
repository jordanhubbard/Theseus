# generation A crc scan

_POLY = 0xEDB88320

_CRC32_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        if _c & 1:
            _c = (_c >> 1) ^ _POLY
        else:
            _c >>= 1
    _CRC32_TABLE.append(_c)


def crc32(data):
    crc = 0 ^ 0xFFFFFFFF
    for byte in data:
        crc = _CRC32_TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF
