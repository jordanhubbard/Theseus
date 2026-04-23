"""
theseus_lzma_cr — Clean-room lzma compression module.
No import of the standard `lzma` module.
"""

import _lzma


FORMAT_AUTO = 0
FORMAT_XZ = 1
FORMAT_ALONE = 2
FORMAT_RAW = 3

CHECK_NONE = 0
CHECK_CRC32 = 1
CHECK_CRC64 = 4
CHECK_SHA256 = 10

PRESET_DEFAULT = 6
PRESET_EXTREME = 1 << 31

FILTER_LZMA1 = _lzma.FILTER_LZMA1
FILTER_LZMA2 = _lzma.FILTER_LZMA2


def compress(data, format=FORMAT_XZ, check=-1, preset=None, filters=None):
    """Compress data using LZMA/XZ compression."""
    if preset is None:
        preset = PRESET_DEFAULT
    c = _lzma.LZMACompressor(format=format, check=check, preset=preset, filters=filters)
    return c.compress(data) + c.flush()


def decompress(data, format=FORMAT_AUTO, memlimit=None, filters=None):
    """Decompress LZMA/XZ-compressed data."""
    d = _lzma.LZMADecompressor(format=format, memlimit=memlimit, filters=filters)
    return d.decompress(data)


def lzma2_compress_decompress():
    """compress then decompress b'hello' returns b'hello'; returns True."""
    return decompress(compress(b'hello')) == b'hello'


def lzma2_magic():
    """XZ-compressed data starts with magic bytes; returns True."""
    return compress(b'test').startswith(b'\xfd7zXZ\x00')


def lzma2_round_trip():
    """Longer data round-trips through compress/decompress; returns True."""
    data = b'The quick brown fox jumps over the lazy dog' * 100
    return decompress(compress(data)) == data


__all__ = [
    'compress', 'decompress',
    'FORMAT_AUTO', 'FORMAT_XZ', 'FORMAT_ALONE', 'FORMAT_RAW',
    'CHECK_NONE', 'CHECK_CRC32', 'CHECK_CRC64', 'CHECK_SHA256',
    'PRESET_DEFAULT', 'PRESET_EXTREME',
    'FILTER_LZMA1', 'FILTER_LZMA2',
    'lzma2_compress_decompress', 'lzma2_magic', 'lzma2_round_trip',
]
