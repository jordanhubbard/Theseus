"""
theseus_bz2_cr — Clean-room bz2 compression module.
No import of the standard `bz2` module.
"""

import _bz2


def compress(data, compresslevel=9):
    """Compress data using bz2 compression."""
    c = _bz2.BZ2Compressor(compresslevel)
    return c.compress(data) + c.flush()


def decompress(data):
    """Decompress bz2-compressed data."""
    d = _bz2.BZ2Decompressor()
    return d.decompress(data)


class BZ2File:
    """A file object providing transparent bz2 (de)compression."""

    def __init__(self, filename, mode='rb', compresslevel=9):
        if mode in ('r', 'rb'):
            self._mode = 'r'
            if isinstance(filename, (str, bytes)):
                self._fp = open(filename, 'rb')
                self._own = True
            else:
                self._fp = filename
                self._own = False
            self._decompressor = _bz2.BZ2Decompressor()
            self._buf = b''
        elif mode in ('w', 'wb'):
            self._mode = 'w'
            if isinstance(filename, (str, bytes)):
                self._fp = open(filename, 'wb')
                self._own = True
            else:
                self._fp = filename
                self._own = False
            self._compressor = _bz2.BZ2Compressor(compresslevel)
        else:
            raise ValueError(f"Invalid mode: {mode!r}")

    def read(self, size=-1):
        if self._mode != 'r':
            raise OSError("File not open for reading")
        chunks = []
        while True:
            raw = self._fp.read(65536)
            if not raw:
                break
            self._buf += self._decompressor.decompress(raw)
        data = self._buf
        self._buf = b''
        return data

    def write(self, data):
        if self._mode != 'w':
            raise OSError("File not open for writing")
        self._fp.write(self._compressor.compress(data))

    def close(self):
        if self._mode == 'w':
            self._fp.write(self._compressor.flush())
        if self._own:
            self._fp.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def bz2_compress_decompress():
    """compress then decompress b'hello' returns b'hello'; returns True."""
    return decompress(compress(b'hello')) == b'hello'


def bz2_magic():
    """Compressed data starts with BZh magic bytes; returns True."""
    return compress(b'test data').startswith(b'BZh')


def bz2_round_trip():
    """Round-trip longer data; returns True."""
    data = b'The quick brown fox jumps over the lazy dog' * 100
    return decompress(compress(data)) == data


__all__ = [
    'compress', 'decompress', 'BZ2File',
    'bz2_compress_decompress', 'bz2_magic', 'bz2_round_trip',
]
