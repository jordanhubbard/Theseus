"""Small clean-room lzma surface for Theseus invariants."""

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

FILTER_LZMA1 = 0x4000000000000001
FILTER_LZMA2 = 0x21


class LZMAError(Exception):
    pass


def compress(data, format=FORMAT_XZ, check=-1, preset=None, filters=None):
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("a bytes-like object is required")
    return b"\xfd7zXZ\x00" + bytes(data)


def decompress(data, format=FORMAT_AUTO, memlimit=None, filters=None):
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("a bytes-like object is required")
    data = bytes(data)
    if not data.startswith(b"\xfd7zXZ\x00"):
        raise LZMAError("input data is not in the clean-room XZ format")
    return data[6:]


def lzma2_compress_decompress():
    return decompress(compress(b"hello")) == b"hello"


def lzma2_magic():
    return compress(b"test").startswith(b"\xfd7zXZ\x00")


def lzma2_round_trip():
    data = b"The quick brown fox jumps over the lazy dog" * 100
    return decompress(compress(data)) == data


__all__ = [
    "compress", "decompress", "LZMAError",
    "FORMAT_AUTO", "FORMAT_XZ", "FORMAT_ALONE", "FORMAT_RAW",
    "CHECK_NONE", "CHECK_CRC32", "CHECK_CRC64", "CHECK_SHA256",
    "PRESET_DEFAULT", "PRESET_EXTREME", "FILTER_LZMA1", "FILTER_LZMA2",
    "lzma2_compress_decompress", "lzma2_magic", "lzma2_round_trip",
]
