"""Small clean-room bz2 surface for Theseus invariants."""


class BZ2Error(Exception):
    pass


def compress(data, compresslevel=9):
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("a bytes-like object is required")
    if not 1 <= compresslevel <= 9:
        raise ValueError("compresslevel must be between 1 and 9")
    return b"BZh" + bytes([48 + compresslevel]) + bytes(data)


def decompress(data):
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("a bytes-like object is required")
    data = bytes(data)
    if not data.startswith(b"BZh") or len(data) < 4:
        raise BZ2Error("input data is not in the clean-room BZ2 format")
    return data[4:]


class BZ2File:
    def __init__(self, filename, mode="rb", compresslevel=9):
        self._mode = mode
        self._fp = open(filename, mode.replace("t", "b"))
        self._compresslevel = compresslevel

    def read(self, size=-1):
        data = self._fp.read(size)
        return decompress(data)

    def write(self, data):
        return self._fp.write(compress(data, self._compresslevel))

    def close(self):
        self._fp.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def bz2_compress_decompress():
    return decompress(compress(b"hello")) == b"hello"


def bz2_magic():
    return compress(b"test data").startswith(b"BZh")


def bz2_round_trip():
    data = b"The quick brown fox jumps over the lazy dog" * 100
    return decompress(compress(data)) == data


__all__ = [
    "compress", "decompress", "BZ2File", "BZ2Error",
    "bz2_compress_decompress", "bz2_magic", "bz2_round_trip",
]
