"""
theseus_zlib_cr2 - Clean-room checksum functions (Adler-32 and CRC-32).
Do NOT import zlib.
"""

_MOD_ADLER = 65521


def adler32(data: bytes) -> int:
    a = 1
    b = 0
    for byte in data:
        a = (a + byte) % _MOD_ADLER
        b = (b + a) % _MOD_ADLER
    return (b << 16) | a


_CRC32_TABLE = None


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


def crc32(data: bytes) -> int:
    global _CRC32_TABLE
    if _CRC32_TABLE is None:
        _CRC32_TABLE = _build_crc32_table()
    crc = 0xFFFFFFFF
    for byte in data:
        crc = (crc >> 8) ^ _CRC32_TABLE[(crc ^ byte) & 0xFF]
    return crc ^ 0xFFFFFFFF


def zlib2_adler32_hello():
    return adler32(b'hello')


def zlib2_crc32_hello():
    return crc32(b'hello')


def zlib2_adler32_empty():
    return adler32(b'')


__all__ = [
    'adler32', 'crc32',
    'zlib2_adler32_hello', 'zlib2_crc32_hello', 'zlib2_adler32_empty',
]
