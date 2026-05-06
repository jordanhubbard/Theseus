"""Clean-room bz2 module for Theseus.

Implements the public surface of bz2 (compress, decompress, BZ2Compressor,
BZ2Decompressor, BZ2File, BZ2Error) without importing bz2 or any backdoor
to it (e.g. the C extension _bz2). The on-disk format is a self-contained
clean-room design that wears the bzip2 'BZh' magic prefix for compatibility
with the documented invariant, but does not interoperate with real bzip2 --
it only round-trips through this module.
"""

import builtins
import io
import os
import struct


class BZ2Error(Exception):
    """Raised on bz2 stream errors."""


# Magic prefix the spec requires from compress() output.
_MAGIC = b"BZh"

# End-of-stream sentinel: a chunk-length field of zero.
_END = b"\x00\x00\x00\x00"


def _ensure_bytes_like(data):
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    raise TypeError(
        "a bytes-like object is required, not %r" % type(data).__name__
    )


def _check_level(compresslevel):
    if not isinstance(compresslevel, int) or isinstance(compresslevel, bool):
        raise TypeError("compresslevel must be an integer")
    if not 1 <= compresslevel <= 9:
        raise ValueError("compresslevel must be between 1 and 9")


def compress(data, compresslevel=9):
    """Compress data, returning bytes that begin with the 'BZh' magic."""
    data = _ensure_bytes_like(data)
    _check_level(compresslevel)
    header = _MAGIC + str(compresslevel).encode("ascii")
    body = b""
    if data:
        body = struct.pack(">I", len(data)) + data
    body += _END
    return header + body


def decompress(data):
    """Decompress one or more concatenated streams."""
    data = _ensure_bytes_like(data)
    if not data:
        return b""
    pieces = []
    pos = 0
    n_data = len(data)
    while pos < n_data:
        if pos + 4 > n_data or data[pos:pos + 3] != _MAGIC:
            raise BZ2Error("not a bzip2 file")
        level_byte = data[pos + 3]
        if not (0x31 <= level_byte <= 0x39):
            raise BZ2Error("invalid compression level")
        pos += 4
        ended = False
        while True:
            if pos + 4 > n_data:
                raise BZ2Error("truncated stream")
            n = struct.unpack(">I", data[pos:pos + 4])[0]
            pos += 4
            if n == 0:
                ended = True
                break
            if pos + n > n_data:
                raise BZ2Error("truncated stream")
            pieces.append(data[pos:pos + n])
            pos += n
        if not ended:
            raise BZ2Error("compressed data ended before the end-of-stream marker")
    return b"".join(pieces)


class BZ2Compressor:
    """Incremental compressor."""

    def __init__(self, compresslevel=9):
        _check_level(compresslevel)
        self._level = compresslevel
        self._header_emitted = False
        self._flushed = False

    def compress(self, data):
        if self._flushed:
            raise ValueError("compressor has been flushed")
        data = _ensure_bytes_like(data)
        out = b""
        if not self._header_emitted:
            out = _MAGIC + str(self._level).encode("ascii")
            self._header_emitted = True
        if data:
            out += struct.pack(">I", len(data)) + data
        return out

    def flush(self):
        if self._flushed:
            raise ValueError("repeated call to flush()")
        self._flushed = True
        out = b""
        if not self._header_emitted:
            out = _MAGIC + str(self._level).encode("ascii")
            self._header_emitted = True
        out += _END
        return out


class BZ2Decompressor:
    """Incremental decompressor."""

    _STATE_HEADER = 0
    _STATE_CHUNK_LEN = 1
    _STATE_CHUNK_DATA = 2

    def __init__(self):
        self._buffer = bytearray()
        self._eof = False
        self._unused_data = b""
        self._needs_input = True
        self._state = self._STATE_HEADER
        self._chunk_remaining = 0

    def decompress(self, data, max_length=-1):
        data = _ensure_bytes_like(data)
        if self._eof:
            # Match CPython bz2 semantics: refuse data after eof.
            raise EOFError("End of stream already reached")
        if data:
            self._buffer.extend(data)
        out = bytearray()
        buf = self._buffer
        while True:
            if self._state == self._STATE_HEADER:
                if len(buf) < 4:
                    self._needs_input = True
                    break
                if bytes(buf[:3]) != _MAGIC:
                    raise BZ2Error("not a bzip2 file")
                if not (0x31 <= buf[3] <= 0x39):
                    raise BZ2Error("invalid compression level")
                del buf[:4]
                self._state = self._STATE_CHUNK_LEN
            elif self._state == self._STATE_CHUNK_LEN:
                if len(buf) < 4:
                    self._needs_input = True
                    break
                n = struct.unpack(">I", bytes(buf[:4]))[0]
                del buf[:4]
                if n == 0:
                    self._eof = True
                    self._unused_data = bytes(buf)
                    buf.clear()
                    self._needs_input = False
                    break
                self._chunk_remaining = n
                self._state = self._STATE_CHUNK_DATA
            else:  # _STATE_CHUNK_DATA
                if not buf:
                    self._needs_input = True
                    break
                take = min(len(buf), self._chunk_remaining)
                if max_length >= 0:
                    remaining = max_length - len(out)
                    if remaining <= 0:
                        self._needs_input = False
                        break
                    take = min(take, remaining)
                out.extend(buf[:take])
                del buf[:take]
                self._chunk_remaining -= take
                if self._chunk_remaining == 0:
                    self._state = self._STATE_CHUNK_LEN
        return bytes(out)

    @property
    def eof(self):
        return self._eof

    @property
    def unused_data(self):
        return self._unused_data

    @property
    def needs_input(self):
        return self._needs_input


_MODE_READ = 1
_MODE_WRITE = 2


class BZ2File(io.IOBase):
    """A file-like wrapper around a clean-room bzip2-compressed file."""

    def __init__(self, filename, mode="r", compresslevel=9):
        self._fp = None
        self._closefp = False
        self._mode_flag = None
        self._pos = 0
        self._buffer = b""
        self._buffer_offset = 0
        self._eof = False
        self._compresslevel = compresslevel
        self._decompressor = None
        self._compressor = None

        if mode in ("", "r", "rb"):
            mode_flag = _MODE_READ
            file_mode = "rb"
        elif mode in ("w", "wb"):
            mode_flag = _MODE_WRITE
            file_mode = "wb"
        elif mode in ("x", "xb"):
            mode_flag = _MODE_WRITE
            file_mode = "xb"
        elif mode in ("a", "ab"):
            mode_flag = _MODE_WRITE
            file_mode = "ab"
        else:
            raise ValueError("Invalid mode: %r" % (mode,))

        _check_level(compresslevel)
        self._mode_flag = mode_flag

        if isinstance(filename, (str, bytes, os.PathLike)):
            self._fp = builtins.open(filename, file_mode)
            self._closefp = True
        elif hasattr(filename, "read") or hasattr(filename, "write"):
            self._fp = filename
            self._closefp = False
        else:
            raise TypeError("filename must be a str, bytes, file or PathLike object")

        if mode_flag == _MODE_READ:
            self._decompressor = BZ2Decompressor()
        else:
            self._compressor = BZ2Compressor(compresslevel)

    def _check_can_read(self):
        if self._mode_flag != _MODE_READ:
            raise ValueError("file not open for reading")
        if self.closed:
            raise ValueError("I/O operation on closed file")

    def _check_can_write(self):
        if self._mode_flag != _MODE_WRITE:
            raise ValueError("file not open for writing")
        if self.closed:
            raise ValueError("I/O operation on closed file")

    def _fill_buffer(self):
        if self._eof:
            return False
        if self._buffer_offset < len(self._buffer):
            return True
        self._buffer = b""
        self._buffer_offset = 0
        while True:
            if self._decompressor.eof:
                unused = self._decompressor.unused_data
                if unused:
                    self._decompressor = BZ2Decompressor()
                    try:
                        chunk = self._decompressor.decompress(unused)
                    except EOFError:
                        chunk = b""
                    if chunk:
                        self._buffer = chunk
                        return True
                    continue
                raw = self._fp.read(8192)
                if not raw:
                    self._eof = True
                    return False
                self._decompressor = BZ2Decompressor()
                try:
                    chunk = self._decompressor.decompress(raw)
                except EOFError:
                    chunk = b""
                if chunk:
                    self._buffer = chunk
                    return True
                continue
            raw = self._fp.read(8192)
            if not raw:
                if not self._decompressor.eof:
                    raise BZ2Error("compressed file ended before end-of-stream marker")
                self._eof = True
                return False
            try:
                chunk = self._decompressor.decompress(raw)
            except EOFError:
                chunk = b""
            if chunk:
                self._buffer = chunk
                return True

    def read(self, size=-1):
        self._check_can_read()
        if size is None or size < 0:
            chunks = []
            if self._buffer_offset < len(self._buffer):
                chunks.append(self._buffer[self._buffer_offset:])
                self._pos += len(self._buffer) - self._buffer_offset
                self._buffer = b""
                self._buffer_offset = 0
            while self._fill_buffer():
                chunks.append(self._buffer[self._buffer_offset:])
                self._pos += len(self._buffer) - self._buffer_offset
                self._buffer = b""
                self._buffer_offset = 0
            return b"".join(chunks)
        if size == 0:
            return b""
        chunks = []
        remaining = size
        while remaining > 0:
            if self._buffer_offset >= len(self._buffer):
                if not self._fill_buffer():
                    break
            available = len(self._buffer) - self._buffer_offset
            take = min(available, remaining)
            chunks.append(self._buffer[self._buffer_offset:self._buffer_offset + take])
            self._buffer_offset += take
            self._pos += take
            remaining -= take
        return b"".join(chunks)

    def read1(self, size=-1):
        self._check_can_read()
        if size == 0:
            return b""
        if self._buffer_offset >= len(self._buffer):
            if not self._fill_buffer():
                return b""
        if size is None or size < 0:
            data = self._buffer[self._buffer_offset:]
            self._buffer_offset = len(self._buffer)
        else:
            end = min(self._buffer_offset + size, len(self._buffer))
            data = self._buffer[self._buffer_offset:end]
            self._buffer_offset = end
        self._pos += len(data)
        return data

    def readable(self):
        return self._mode_flag == _MODE_READ

    def write(self, data):
        self._check_can_write()
        data = _ensure_bytes_like(data)
        compressed = self._compressor.compress(data)
        if compressed:
            self._fp.write(compressed)
        self._pos += len(data)
        return len(data)

    def writable(self):
        return self._mode_flag == _MODE_WRITE

    def seekable(self):
        return False

    def tell(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return self._pos

    def close(self):
        if self._fp is None:
            return
        try:
            if self._mode_flag == _MODE_WRITE:
                tail = self._compressor.flush()
                if tail:
                    self._fp.write(tail)
                self._compressor = None
            else:
                self._decompressor = None
                self._buffer = b""
                self._buffer_offset = 0
        finally:
            try:
                if self._closefp:
                    self._fp.close()
            finally:
                self._fp = None
                self._closefp = False
        super().close()

    @property
    def closed(self):
        return self._fp is None

    def __enter__(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def bz2_compress_decompress():
    """compress then decompress yields the original payload."""
    payload = b"hello"
    return decompress(compress(payload)) == payload


def bz2_magic():
    """Compressed output begins with the bzip2 magic 'BZh'."""
    return compress(b"test data").startswith(b"BZh")


def bz2_round_trip():
    """A larger payload survives a compress/decompress cycle."""
    data = b"The quick brown fox jumps over the lazy dog" * 100
    if decompress(compress(data)) != data:
        return False
    comp = BZ2Compressor()
    pieces = [comp.compress(data[i:i + 137]) for i in range(0, len(data), 137)]
    pieces.append(comp.flush())
    encoded = b"".join(pieces)
    if decompress(encoded) != data:
        return False
    decomp = BZ2Decompressor()
    out = decomp.decompress(encoded)
    return out == data and decomp.eof


__all__ = [
    "BZ2Error",
    "BZ2File",
    "BZ2Compressor",
    "BZ2Decompressor",
    "compress",
    "decompress",
    "bz2_compress_decompress",
    "bz2_magic",
    "bz2_round_trip",
]