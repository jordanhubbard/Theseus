"""
theseus_gzip_cr — Clean-room gzip compression module.
No import of the standard `gzip` module.
"""

import io
import struct
import time
import zlib


_GZIP_MAGIC = b'\x1f\x8b'
_GZIP_METHOD_DEFLATE = 8
_GZIP_OS_UNIX = 255  # unknown


def compress(data, compresslevel=9):
    """Compress data in gzip format."""
    buf = io.BytesIO()
    mtime = int(time.time())
    # Write gzip header
    buf.write(_GZIP_MAGIC)
    buf.write(bytes([_GZIP_METHOD_DEFLATE]))  # method
    buf.write(b'\x00')                         # flags
    buf.write(struct.pack('<I', mtime))         # mtime
    buf.write(b'\x00')                         # xfl
    buf.write(bytes([_GZIP_OS_UNIX]))           # OS
    # Deflate compressed data (raw, no zlib wrapper)
    compress_obj = zlib.compressobj(compresslevel, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed = compress_obj.compress(data) + compress_obj.flush()
    buf.write(compressed)
    # Write CRC32 and size
    crc = zlib.crc32(data) & 0xFFFFFFFF
    buf.write(struct.pack('<II', crc, len(data) & 0xFFFFFFFF))
    return buf.getvalue()


def decompress(data):
    """Decompress gzip-format data."""
    if len(data) < 10:
        raise OSError("Not a gzip file")
    if data[:2] != _GZIP_MAGIC:
        raise OSError("Not a gzip file")
    method = data[2]
    if method != _GZIP_METHOD_DEFLATE:
        raise OSError(f"Unknown compression method: {method}")
    flags = data[3]
    offset = 10
    # Skip extra field
    if flags & 4:
        xlen = struct.unpack_from('<H', data, offset)[0]
        offset += 2 + xlen
    # Skip original filename
    if flags & 8:
        while offset < len(data) and data[offset] != 0:
            offset += 1
        offset += 1
    # Skip comment
    if flags & 16:
        while offset < len(data) and data[offset] != 0:
            offset += 1
        offset += 1
    # Skip CRC16
    if flags & 2:
        offset += 2
    # Decompress raw deflate data (strip 8-byte trailer)
    raw = data[offset:-8]
    decompressed = zlib.decompress(raw, -zlib.MAX_WBITS)
    return decompressed


class GzipFile:
    """File-like object for gzip-compressed data."""

    def __init__(self, filename=None, mode='rb', compresslevel=9, fileobj=None):
        if mode not in ('rb', 'wb', 'r', 'w'):
            raise ValueError(f"Invalid mode: {mode!r}")
        self._mode = mode
        self._compresslevel = compresslevel
        if fileobj is not None:
            self._fileobj = fileobj
            self._own = False
        elif filename is not None:
            self._fileobj = open(filename, mode if 'b' in mode else mode + 'b')
            self._own = True
        else:
            raise ValueError("Either filename or fileobj required")
        self._buf = b''
        if 'r' in mode:
            raw = self._fileobj.read()
            self._buf = decompress(raw)
            self._pos = 0
        else:
            self._compressor = zlib.compressobj(compresslevel, zlib.DEFLATED, -zlib.MAX_WBITS)
            self._data = b''
            self._mtime = int(time.time())
            self._fileobj.write(_GZIP_MAGIC)
            self._fileobj.write(bytes([_GZIP_METHOD_DEFLATE, 0]))
            self._fileobj.write(struct.pack('<I', self._mtime))
            self._fileobj.write(b'\x00')
            self._fileobj.write(bytes([_GZIP_OS_UNIX]))

    def read(self, size=-1):
        if 'r' not in self._mode:
            raise OSError("File not open for reading")
        if size < 0:
            result = self._buf[self._pos:]
            self._pos = len(self._buf)
        else:
            result = self._buf[self._pos:self._pos + size]
            self._pos += len(result)
        return result

    def write(self, data):
        if 'w' not in self._mode:
            raise OSError("File not open for writing")
        self._data += data
        self._fileobj.write(self._compressor.compress(data))

    def close(self):
        if 'w' in self._mode:
            self._fileobj.write(self._compressor.flush())
            crc = zlib.crc32(self._data) & 0xFFFFFFFF
            self._fileobj.write(struct.pack('<II', crc, len(self._data) & 0xFFFFFFFF))
        if self._own:
            self._fileobj.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def gzip2_compress_decompress():
    """compress then decompress b'hello' returns b'hello'; returns True."""
    return decompress(compress(b'hello')) == b'hello'


def gzip2_magic():
    """Compressed data starts with gzip magic 0x1f 0x8b; returns True."""
    return compress(b'test').startswith(b'\x1f\x8b')


def gzip2_round_trip():
    """Longer data round-trips through compress/decompress; returns True."""
    data = b'The quick brown fox jumps over the lazy dog' * 100
    return decompress(compress(data)) == data


__all__ = [
    'compress', 'decompress', 'GzipFile',
    'gzip2_compress_decompress', 'gzip2_magic', 'gzip2_round_trip',
]
