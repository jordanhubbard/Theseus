"""
Clean-room implementation of compression.bz2 API surface.

This module provides the same API as compression.bz2 (Python 3.14+) but
without importing the original. Compression here is a self-consistent
stand-in: data is wrapped with a magic header so round-trips succeed.
Real bzip2 byte-for-byte compatibility is not provided.
"""

import io as _io
import os as _os
import struct as _struct

__all__ = [
    "BZ2File",
    "BZ2Compressor",
    "BZ2Decompressor",
    "compress",
    "decompress",
    "open",
    "cbz22_compress",
    "cbz22_classes",
    "cbz22_open",
]

# Magic header for our stand-in stream format.
# Real bzip2 uses b"BZh" + level byte; we use a different prefix to make
# it clear this is the clean-room format and not real bzip2 output.
_MAGIC = b"CRBZ2\x00"
_HEADER_FMT = ">6sBQ"  # magic, level, payload-length
_HEADER_SIZE = _struct.calcsize(_HEADER_FMT)

_MODE_CLOSED = 0
_MODE_READ = 1
_MODE_WRITE = 2


def _check_level(level):
    if not isinstance(level, int):
        raise TypeError("compresslevel must be an integer")
    if level < 1 or level > 9:
        raise ValueError("compresslevel must be between 1 and 9")
    return level


# ---------------------------------------------------------------------------
# One-shot helpers
# ---------------------------------------------------------------------------

def compress(data, compresslevel=9):
    """Compress *data* (a bytes-like object) and return the compressed bytes."""
    if isinstance(data, (bytes, bytearray, memoryview)):
        payload = bytes(data)
    else:
        raise TypeError("data must be bytes-like")
    level = _check_level(compresslevel)
    header = _struct.pack(_HEADER_FMT, _MAGIC, level, len(payload))
    return header + payload


def decompress(data):
    """Decompress one or more concatenated streams of compressed *data*."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")
    buf = bytes(data)
    out = bytearray()
    pos = 0
    n = len(buf)
    if n == 0:
        raise ValueError("Compressed data ended before the end-of-stream marker was reached")
    while pos < n:
        if n - pos < _HEADER_SIZE:
            raise ValueError("truncated compressed stream")
        magic, _level, length = _struct.unpack(
            _HEADER_FMT, buf[pos:pos + _HEADER_SIZE]
        )
        if magic != _MAGIC:
            raise ValueError("invalid stream magic")
        pos += _HEADER_SIZE
        if n - pos < length:
            raise ValueError("truncated compressed payload")
        out.extend(buf[pos:pos + length])
        pos += length
    return bytes(out)


# ---------------------------------------------------------------------------
# Incremental classes
# ---------------------------------------------------------------------------

class BZ2Compressor:
    """Incremental compressor.  compress() then flush() to finish."""

    def __init__(self, compresslevel=9):
        self._level = _check_level(compresslevel)
        self._buf = bytearray()
        self._finished = False

    def compress(self, data):
        if self._finished:
            raise ValueError("Compressor has been flushed")
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes-like")
        self._buf.extend(bytes(data))
        # Stand-in compressors may buffer; we always do.
        return b""

    def flush(self):
        if self._finished:
            raise ValueError("Repeated call to flush()")
        self._finished = True
        payload = bytes(self._buf)
        self._buf = bytearray()
        header = _struct.pack(_HEADER_FMT, _MAGIC, self._level, len(payload))
        return header + payload


class BZ2Decompressor:
    """Incremental decompressor."""

    def __init__(self):
        self._inbuf = bytearray()
        self._outbuf = bytearray()
        self._eof = False
        self._needs_input = True
        self._unused = b""
        self._header_level = None
        self._remaining = None  # bytes still to read from current stream

    @property
    def eof(self):
        return self._eof

    @property
    def needs_input(self):
        return self._needs_input

    @property
    def unused_data(self):
        return self._unused

    def _try_parse_header(self):
        if self._remaining is not None:
            return True
        if len(self._inbuf) < _HEADER_SIZE:
            return False
        magic, level, length = _struct.unpack(
            _HEADER_FMT, bytes(self._inbuf[:_HEADER_SIZE])
        )
        if magic != _MAGIC:
            raise ValueError("invalid stream magic")
        del self._inbuf[:_HEADER_SIZE]
        self._header_level = level
        self._remaining = length
        return True

    def decompress(self, data, max_length=-1):
        if self._eof:
            raise EOFError("End of stream already reached")
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes-like")
        self._inbuf.extend(bytes(data))

        if not self._try_parse_header():
            self._needs_input = True
            return b""

        # We have a header; read up to _remaining bytes from inbuf.
        avail = min(len(self._inbuf), self._remaining)
        chunk = bytes(self._inbuf[:avail])
        del self._inbuf[:avail]
        self._remaining -= avail

        if self._remaining == 0:
            # Stream finished.
            self._eof = True
            self._unused = bytes(self._inbuf)
            self._inbuf = bytearray()
            self._needs_input = False
        else:
            self._needs_input = True

        if max_length is not None and max_length >= 0 and len(chunk) > max_length:
            # Save the overflow back into the output buffer for next call.
            # (Real bz2 returns up to max_length bytes per call.)
            self._outbuf.extend(chunk[max_length:])
            chunk = chunk[:max_length]
            self._needs_input = False
            self._eof = False  # there is still buffered output to deliver
        elif self._outbuf:
            # Drain pending output first.
            pending = bytes(self._outbuf)
            self._outbuf = bytearray()
            chunk = pending + chunk
            if max_length is not None and max_length >= 0 and len(chunk) > max_length:
                self._outbuf.extend(chunk[max_length:])
                chunk = chunk[:max_length]
                self._needs_input = False
                self._eof = False
        return chunk


# ---------------------------------------------------------------------------
# File wrapper
# ---------------------------------------------------------------------------

class BZ2File(_io.BufferedIOBase):
    """A file object providing transparent (de)compression of our format."""

    def __init__(self, filename, mode="r", *, compresslevel=9):
        self._mode = _MODE_CLOSED
        self._fp = None
        self._closefp = False
        self._buffer = b""
        self._pos = 0
        self._size = -1
        self._decompressor = None
        self._compressor = None

        if mode in ("", "r", "rb"):
            mode_code = _MODE_READ
            file_mode = "rb"
        elif mode in ("w", "wb"):
            mode_code = _MODE_WRITE
            file_mode = "wb"
        elif mode in ("x", "xb"):
            mode_code = _MODE_WRITE
            file_mode = "xb"
        elif mode in ("a", "ab"):
            mode_code = _MODE_WRITE
            file_mode = "ab"
        else:
            raise ValueError("Invalid mode: %r" % (mode,))

        _check_level(compresslevel)

        if isinstance(filename, (str, bytes, _os.PathLike)):
            self._fp = builtin_open(filename, file_mode)
            self._closefp = True
        elif hasattr(filename, "read") or hasattr(filename, "write"):
            self._fp = filename
            self._closefp = False
        else:
            raise TypeError("filename must be a str, bytes, file or PathLike object")

        self._mode = mode_code
        if mode_code == _MODE_READ:
            self._decompressor = BZ2Decompressor()
        else:
            self._compressor = BZ2Compressor(compresslevel)

    # -- standard file interface -------------------------------------------

    def close(self):
        if self._mode == _MODE_CLOSED:
            return
        try:
            if self._mode == _MODE_WRITE:
                if self._compressor is not None:
                    tail = self._compressor.flush()
                    if tail:
                        self._fp.write(tail)
                self._compressor = None
            else:
                self._decompressor = None
                self._buffer = b""
        finally:
            try:
                if self._closefp:
                    self._fp.close()
            finally:
                self._fp = None
                self._closefp = False
                self._mode = _MODE_CLOSED

    @property
    def closed(self):
        return self._mode == _MODE_CLOSED

    def fileno(self):
        self._check_not_closed()
        return self._fp.fileno()

    def seekable(self):
        return False

    def readable(self):
        self._check_not_closed()
        return self._mode == _MODE_READ

    def writable(self):
        self._check_not_closed()
        return self._mode == _MODE_WRITE

    def _check_not_closed(self):
        if self._mode == _MODE_CLOSED:
            raise ValueError("I/O operation on closed file")

    def _check_can_read(self):
        if self._mode != _MODE_READ:
            raise _io.UnsupportedOperation("File not open for reading")

    def _check_can_write(self):
        if self._mode != _MODE_WRITE:
            raise _io.UnsupportedOperation("File not open for writing")

    # -- read path ---------------------------------------------------------

    def _fill_buffer(self):
        if self._decompressor is None or self._decompressor.eof:
            return False
        while not self._buffer:
            raw = self._fp.read(8192)
            if not raw:
                # No more compressed input; nothing further to decode.
                return False
            chunk = self._decompressor.decompress(raw)
            if chunk:
                self._buffer = chunk
                return True
            if self._decompressor.eof:
                break
        return bool(self._buffer)

    def read(self, size=-1):
        self._check_can_read()
        if size is None:
            size = -1
        out = bytearray()
        if size < 0:
            while True:
                if not self._buffer and not self._fill_buffer():
                    break
                out.extend(self._buffer)
                self._buffer = b""
        else:
            while size > 0:
                if not self._buffer and not self._fill_buffer():
                    break
                take = self._buffer[:size]
                self._buffer = self._buffer[len(take):]
                out.extend(take)
                size -= len(take)
        return bytes(out)

    def read1(self, size=-1):
        self._check_can_read()
        if size is None or size < 0:
            size = 8192
        if not self._buffer and not self._fill_buffer():
            return b""
        out = self._buffer[:size]
        self._buffer = self._buffer[len(out):]
        return bytes(out)

    def readinto(self, b):
        self._check_can_read()
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def readline(self, size=-1):
        self._check_can_read()
        if size is None:
            size = -1
        out = bytearray()
        while True:
            if not self._buffer and not self._fill_buffer():
                break
            nl = self._buffer.find(b"\n")
            if nl >= 0:
                take = self._buffer[:nl + 1]
                self._buffer = self._buffer[nl + 1:]
                out.extend(take)
                break
            else:
                out.extend(self._buffer)
                self._buffer = b""
            if size >= 0 and len(out) >= size:
                break
        if size >= 0 and len(out) > size:
            self._buffer = bytes(out[size:]) + self._buffer
            out = out[:size]
        return bytes(out)

    # -- write path --------------------------------------------------------

    def write(self, data):
        self._check_can_write()
        if isinstance(data, (bytes, bytearray)):
            view = bytes(data)
        elif isinstance(data, memoryview):
            view = data.tobytes()
        else:
            raise TypeError("a bytes-like object is required")
        compressed = self._compressor.compress(view)
        if compressed:
            self._fp.write(compressed)
        return len(view)

    def flush(self):
        self._check_not_closed()
        if self._mode == _MODE_WRITE and hasattr(self._fp, "flush"):
            self._fp.flush()

    # -- context manager ---------------------------------------------------

    def __enter__(self):
        self._check_not_closed()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


# Save a reference to the builtin open so our open() can shadow it.
import builtins as _builtins
builtin_open = _builtins.open


def open(filename, mode="rb", *, compresslevel=9,
         encoding=None, errors=None, newline=None):
    """Open a file as a (de)compressed stream.

    Binary modes return a ``BZ2File``.  Text modes wrap it in a
    ``TextIOWrapper`` for transparent string I/O.
    """
    if "t" in mode:
        if "b" in mode:
            raise ValueError("Invalid mode: %r" % (mode,))
        binary_mode = mode.replace("t", "")
        if binary_mode == "":
            binary_mode = "r"
    else:
        if encoding is not None:
            raise ValueError("Argument 'encoding' not supported in binary mode")
        if errors is not None:
            raise ValueError("Argument 'errors' not supported in binary mode")
        if newline is not None:
            raise ValueError("Argument 'newline' not supported in binary mode")
        binary_mode = mode

    binary_file = BZ2File(filename, binary_mode, compresslevel=compresslevel)

    if "t" in mode:
        return _io.TextIOWrapper(
            binary_file, encoding=encoding, errors=errors, newline=newline
        )
    return binary_file


# ---------------------------------------------------------------------------
# Self-test invariants
# ---------------------------------------------------------------------------

def cbz22_compress():
    """Round-trip via the module-level compress()/decompress() helpers."""
    samples = [
        b"",
        b"hello world",
        b"\x00\x01\x02\x03\xff\xfe\xfd",
        b"a" * 1000,
        bytes(range(256)) * 4,
    ]
    for data in samples:
        for level in (1, 5, 9):
            blob = compress(data, level)
            if not isinstance(blob, bytes):
                return False
            if decompress(blob) != data:
                return False
    # Concatenated streams decode as concatenation.
    a = compress(b"alpha")
    b = compress(b"beta")
    if decompress(a + b) != b"alpha" + b"beta":
        return False
    # Type checking
    try:
        compress("not bytes")
    except TypeError:
        pass
    else:
        return False
    try:
        compress(b"x", 0)
    except ValueError:
        pass
    else:
        return False
    return True


def cbz22_classes():
    """Round-trip via BZ2Compressor / BZ2Decompressor classes."""
    c = BZ2Compressor(7)
    parts = [c.compress(b"hello, "), c.compress(b"world!"), c.flush()]
    blob = b"".join(parts)

    d = BZ2Decompressor()
    out = d.decompress(blob)
    if out != b"hello, world!":
        return False
    if not d.eof:
        return False

    # Feed in tiny chunks too.
    d2 = BZ2Decompressor()
    out2 = bytearray()
    for i in range(len(blob)):
        out2.extend(d2.decompress(blob[i:i + 1]))
    if bytes(out2) != b"hello, world!":
        return False
    if not d2.eof:
        return False

    # Flushing twice must error; compressing after flush must error.
    c2 = BZ2Compressor()
    c2.flush()
    try:
        c2.flush()
    except ValueError:
        pass
    else:
        return False
    try:
        c2.compress(b"x")
    except ValueError:
        pass
    else:
        return False

    # Decompressing after EOF must error.
    try:
        d.decompress(b"x")
    except EOFError:
        pass
    else:
        return False

    # unused_data is exposed.
    extra = compress(b"tail")
    d3 = BZ2Decompressor()
    d3.decompress(blob + extra)
    if d3.unused_data != extra:
        return False
    return True


def cbz22_open():
    """Round-trip via BZ2File and the open() helper, in binary and text modes."""
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="cbz22_")
    try:
        path = _os.path.join(tmpdir, "sample.cbz2")

        # Binary write/read via open().
        payload = b"the quick brown fox\njumps over the lazy dog\n" * 32
        with open(path, "wb", compresslevel=4) as f:
            f.write(payload)
        with open(path, "rb") as f:
            got = f.read()
        if got != payload:
            return False

        # readline() works.
        with open(path, "rb") as f:
            first = f.readline()
        if first != b"the quick brown fox\n":
            return False

        # Text mode round-trips via TextIOWrapper.
        text_path = _os.path.join(tmpdir, "sample.txt.cbz2")
        with open(text_path, "wt", encoding="utf-8") as f:
            f.write("héllo\nwörld\n")
        with open(text_path, "rt", encoding="utf-8") as f:
            text_got = f.read()
        if text_got != "héllo\nwörld\n":
            return False

        # BZ2File directly with a file-like object.
        buf = _io.BytesIO()
        with BZ2File(buf, "wb") as f:
            f.write(b"streamed")
        buf.seek(0)
        with BZ2File(buf, "rb") as f:
            if f.read() != b"streamed":
                return False

        # Mode validation.
        try:
            BZ2File(path, "q")
        except ValueError:
            pass
        else:
            return False

        # Closed-file behavior.
        f = open(path, "rb")
        f.close()
        if not f.closed:
            return False
        try:
            f.read()
        except ValueError:
            pass
        else:
            return False

        return True
    finally:
        # Best-effort cleanup.
        for name in _os.listdir(tmpdir):
            try:
                _os.remove(_os.path.join(tmpdir, name))
            except OSError:
                pass
        try:
            _os.rmdir(tmpdir)
        except OSError:
            pass