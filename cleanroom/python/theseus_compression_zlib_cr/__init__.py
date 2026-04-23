"""
theseus_compression_zlib_cr — Clean-room compression.zlib module (Python 3.14+).
No import of the standard `compression.zlib` module.
Uses the underlying zlib C extension directly.
"""

import zlib as _zlib
import io as _io


# Re-export zlib constants
DEFLATED = _zlib.DEFLATED
DEF_BUF_SIZE = _zlib.DEF_BUF_SIZE
DEF_MEM_LEVEL = _zlib.DEF_MEM_LEVEL
MAX_WBITS = _zlib.MAX_WBITS
ZLIB_VERSION = _zlib.ZLIB_VERSION
ZLIB_RUNTIME_VERSION = _zlib.ZLIB_RUNTIME_VERSION
Z_BEST_COMPRESSION = _zlib.Z_BEST_COMPRESSION
Z_BEST_SPEED = _zlib.Z_BEST_SPEED
Z_DEFAULT_COMPRESSION = _zlib.Z_DEFAULT_COMPRESSION
Z_DEFAULT_STRATEGY = _zlib.Z_DEFAULT_STRATEGY
Z_FILTERED = _zlib.Z_FILTERED
Z_FIXED = _zlib.Z_FIXED
Z_FULL_FLUSH = _zlib.Z_FULL_FLUSH
Z_HUFFMAN_ONLY = _zlib.Z_HUFFMAN_ONLY
Z_NO_FLUSH = _zlib.Z_NO_FLUSH
Z_RLE = _zlib.Z_RLE
Z_SYNC_FLUSH = _zlib.Z_SYNC_FLUSH
Z_FINISH = _zlib.Z_FINISH

error = _zlib.error

# Compressor/Decompressor
compressobj = _zlib.compressobj
decompressobj = _zlib.decompressobj

# Functions
compress = _zlib.compress
decompress = _zlib.decompress
adler32 = _zlib.adler32
crc32 = _zlib.crc32


class ZlibFile(_io.RawIOBase):
    """A file-like object that provides transparent zlib (gzip-compatible) compression."""

    def __init__(self, filename=None, mode='rb', *, compresslevel=_zlib.Z_DEFAULT_COMPRESSION,
                 wbits=_zlib.MAX_WBITS | 16, fileobj=None):
        if mode not in ('r', 'rb', 'w', 'wb', 'a', 'ab'):
            raise ValueError(f"Invalid mode: {mode!r}")
        import gzip as _gz
        self._gz = _gz.GzipFile(filename=filename, mode=mode,
                                 compresslevel=compresslevel, fileobj=fileobj)
        self._mode = mode

    def read(self, size=-1):
        return self._gz.read(size)

    def write(self, data):
        return self._gz.write(data)

    def close(self):
        self._gz.close()
        super().close()

    def readable(self):
        return 'r' in self._mode

    def writable(self):
        return 'w' in self._mode or 'a' in self._mode

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open(filename, mode='rb', *, compresslevel=_zlib.Z_DEFAULT_COMPRESSION,
         wbits=_zlib.MAX_WBITS | 16, encoding=None, errors=None, newline=None):
    """Open a gzip-compressed file in binary or text mode."""
    import gzip as _gz
    return _gz.open(filename, mode, compresslevel=compresslevel,
                    encoding=encoding, errors=errors, newline=newline)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def czlib2_compress():
    """compress/decompress roundtrip works; returns True."""
    data = b'Hello, World! This is a test string for compression.'
    compressed = compress(data)
    decompressed = decompress(compressed)
    return (isinstance(compressed, bytes) and
            len(compressed) < len(data) * 2 and
            decompressed == data)


def czlib2_constants():
    """zlib constants are exposed; returns True."""
    return (DEFLATED == 8 and
            isinstance(Z_BEST_COMPRESSION, int) and
            isinstance(ZLIB_VERSION, str) and
            Z_BEST_COMPRESSION > Z_BEST_SPEED)


def czlib2_open():
    """open() function creates a writable compressed file; returns True."""
    import tempfile as _tf
    import os as _os
    with _tf.NamedTemporaryFile(suffix='.gz', delete=False) as f:
        fname = f.name
    try:
        with open(fname, 'wb') as gf:
            gf.write(b'test data for gzip')
        size = _os.path.getsize(fname)
        _os.unlink(fname)
        return size > 0
    except Exception:
        try:
            _os.unlink(fname)
        except Exception:
            pass
        return False


__all__ = [
    'compress', 'decompress', 'compressobj', 'decompressobj',
    'adler32', 'crc32', 'open', 'ZlibFile', 'error',
    'DEFLATED', 'DEF_BUF_SIZE', 'DEF_MEM_LEVEL', 'MAX_WBITS',
    'ZLIB_VERSION', 'ZLIB_RUNTIME_VERSION',
    'Z_BEST_COMPRESSION', 'Z_BEST_SPEED', 'Z_DEFAULT_COMPRESSION',
    'Z_DEFAULT_STRATEGY', 'Z_NO_FLUSH', 'Z_SYNC_FLUSH', 'Z_FULL_FLUSH', 'Z_FINISH',
    'czlib2_compress', 'czlib2_constants', 'czlib2_open',
]
