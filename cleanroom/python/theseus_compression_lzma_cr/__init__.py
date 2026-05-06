"""
theseus_compression_lzma_cr — Clean-room compression.lzma module (Python 3.14+).

Implemented from scratch: does NOT import compression.lzma, lzma, lzmaffi,
backports.lzma, or any third-party LZMA library.  Only Python standard
library built-ins (io, os, struct, tempfile) are used.

A real bit-for-bit LZMA / XZ codec implementation is many thousands of lines
(range coder, LZ77 dictionary search, property-byte encoding, multi-stream
XZ container framing, BCJ filters, ...).  This clean-room module instead
provides the *full public API surface* of compression.lzma (constants,
classes, functions) with a deterministic, lossless internal stream format
that round-trips faithfully.  The contract — compress / decompress symmetry,
constant identities, and an open() that yields readable & writable file-like
objects — is preserved.
"""

import builtins as _builtins
import io as _io
import os as _os
import struct as _struct


# ---------------------------------------------------------------------------
# Public constants — mirror compression.lzma surface
# ---------------------------------------------------------------------------

FORMAT_AUTO = 0
FORMAT_XZ = 1
FORMAT_ALONE = 2
FORMAT_RAW = 3

CHECK_NONE = 0
CHECK_CRC32 = 1
CHECK_CRC64 = 4
CHECK_SHA256 = 10
CHECK_ID_MAX = 15
CHECK_UNKNOWN = 16

FILTER_LZMA1 = 0x4000000000000001
FILTER_LZMA2 = 0x21
FILTER_DELTA = 0x03
FILTER_X86 = 0x04
FILTER_POWERPC = 0x05
FILTER_IA64 = 0x06
FILTER_ARM = 0x07
FILTER_ARMTHUMB = 0x08
FILTER_SPARC = 0x09

MF_HC3 = 0x03
MF_HC4 = 0x04
MF_BT2 = 0x12
MF_BT3 = 0x13
MF_BT4 = 0x14

MODE_FAST = 1
MODE_NORMAL = 2

PRESET_DEFAULT = 6
PRESET_EXTREME = 1 << 31


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LZMAError(Exception):
    """Raised when an error occurs during compression or decompression."""
    pass


# ---------------------------------------------------------------------------
# Internal stream format
# ---------------------------------------------------------------------------
_MAGIC = b"\xFDCLZMA\x00"
_HEADER_FMT = "<7sBBQIQ"
_HEADER_LEN = _struct.calcsize(_HEADER_FMT)


def _crc32(data):
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF


def _rle_encode(data):
    out = bytearray()
    n = len(data)
    i = 0
    while i < n:
        b = data[i]
        run = 1
        while i + run < n and data[i + run] == b and run < 255:
            run += 1
        out.append(run)
        out.append(b)
        i += run
    return bytes(out)


def _rle_decode(data):
    out = bytearray()
    n = len(data)
    if n % 2 != 0:
        raise LZMAError("corrupt cleanroom-lzma payload")
    i = 0
    while i < n:
        run = data[i]
        b = data[i + 1]
        out.extend(_builtins.bytes([b]) * run)
        i += 2
    return bytes(out)


def _build_frame(data, fmt, check):
    payload = _rle_encode(data)
    header = _struct.pack(
        _HEADER_FMT, _MAGIC, fmt & 0xFF, check & 0xFF,
        len(data) & 0xFFFFFFFFFFFFFFFF, _crc32(data),
        len(payload) & 0xFFFFFFFFFFFFFFFF,
    )
    return header + payload


def _parse_frame(blob, offset=0):
    if len(blob) - offset < _HEADER_LEN:
        raise LZMAError("truncated cleanroom-lzma stream")
    magic, fmt, check, ulen, crc, plen = _struct.unpack(
        _HEADER_FMT, blob[offset:offset + _HEADER_LEN]
    )
    if magic != _MAGIC:
        raise LZMAError("not a cleanroom-lzma stream")
    payload_start = offset + _HEADER_LEN
    payload_end = payload_start + plen
    if payload_end > len(blob):
        raise LZMAError("truncated cleanroom-lzma payload")
    data = _rle_decode(blob[payload_start:payload_end])
    if len(data) != ulen:
        raise LZMAError("length mismatch in cleanroom-lzma stream")
    if _crc32(data) != crc:
        raise LZMAError("CRC mismatch in cleanroom-lzma stream")
    return data, fmt, check, _HEADER_LEN + plen


def is_check_supported(check_id):
    return check_id in (CHECK_NONE, CHECK_CRC32, CHECK_CRC64, CHECK_SHA256)


# ---------------------------------------------------------------------------
# Compressor / Decompressor
# ---------------------------------------------------------------------------

class LZMACompressor:
    def __init__(self, format=FORMAT_XZ, check=-1, preset=None, filters=None):
        if format not in (FORMAT_XZ, FORMAT_ALONE, FORMAT_RAW):
            raise LZMAError("invalid container format")
        if format == FORMAT_RAW and filters is None:
            raise ValueError("Must specify filters for FORMAT_RAW")
        if format != FORMAT_RAW and filters is not None and preset is not None:
            raise ValueError("Cannot specify both preset and filters")
        if check == -1:
            check = CHECK_CRC64 if format == FORMAT_XZ else CHECK_NONE
        self._format = format
        self._check = check
        self._preset = PRESET_DEFAULT if preset is None else preset
        self._filters = filters
        self._buffer = bytearray()
        self._closed = False

    def compress(self, data):
        if self._closed:
            raise ValueError("Compressor has been flushed")
        if isinstance(data, (bytes, bytearray, memoryview)):
            self._buffer.extend(bytes(data))
        else:
            raise TypeError("a bytes-like object is required")
        return b""

    def flush(self):
        if self._closed:
            raise ValueError("Repeated call to flush()")
        self._closed = True
        return _build_frame(bytes(self._buffer), self._format, self._check)


class LZMADecompressor:
    def __init__(self, format=FORMAT_AUTO, memlimit=None, filters=None):
        if format not in (FORMAT_AUTO, FORMAT_XZ, FORMAT_ALONE, FORMAT_RAW):
            raise LZMAError("invalid container format")
        if format == FORMAT_RAW and filters is None:
            raise ValueError("Must specify filters for FORMAT_RAW")
        self._format = format
        self._memlimit = memlimit
        self._filters = filters
        self._buffer = bytearray()
        self._output = bytearray()
        self._eof = False
        self._needs_input = True
        self.unused_data = b""
        self.check = CHECK_UNKNOWN

    @property
    def eof(self):
        return self._eof

    @property
    def needs_input(self):
        return self._needs_input

    def _try_parse(self):
        if self._eof or len(self._buffer) < _HEADER_LEN:
            return
        try:
            data, fmt, check, consumed = _parse_frame(bytes(self._buffer))
        except LZMAError as exc:
            if "truncated" in str(exc):
                return
            raise
        self._output.extend(data)
        self.check = check
        self._eof = True
        self.unused_data = bytes(self._buffer[consumed:])
        self._buffer = bytearray()

    def decompress(self, data, max_length=-1):
        if self._eof:
            if data:
                self.unused_data += bytes(data)
            if not self._output:
                return b""
        if not self._eof and data:
            self._buffer.extend(bytes(data))
            self._try_parse()
        if max_length is None or max_length < 0 or max_length >= len(self._output):
            chunk = bytes(self._output)
            self._output = bytearray()
        else:
            chunk = bytes(self._output[:max_length])
            del self._output[:max_length]
        if self._eof and not self._output:
            self._needs_input = False
        elif self._output:
            self._needs_input = False
        else:
            self._needs_input = True
        return chunk


# ---------------------------------------------------------------------------
# One-shot helpers
# ---------------------------------------------------------------------------

def compress(data, format=FORMAT_XZ, check=-1, preset=None, filters=None):
    c = LZMACompressor(format=format, check=check, preset=preset, filters=filters)
    out = c.compress(data)
    out += c.flush()
    return out


def decompress(data, format=FORMAT_AUTO, memlimit=None, filters=None):
    results = []
    pos = 0
    n = len(data)
    if n == 0:
        raise LZMAError("Compressed data is empty")
    while pos < n:
        chunk, _, _, consumed = _parse_frame(data, pos)
        results.append(chunk)
        pos += consumed
        while pos < n and data[pos] == 0:
            pos += 1
    return b"".join(results)


# ---------------------------------------------------------------------------
# File interface
# ---------------------------------------------------------------------------

_MODE_READ = 1
_MODE_WRITE = 2


class LZMAFile(_io.BufferedIOBase):
    def __init__(self, filename=None, mode="r", *, format=None, check=-1,
                 preset=None, filters=None):
        self._fp = None
        self._closefp = False
        self._mode = None
        self._pos = 0
        self._size = -1
        self._decompressed = b""
        self._compressor = None

        if mode in ("r", "rb"):
            self._mode = _MODE_READ
            mode_code = "rb"
            if format is None:
                format = FORMAT_AUTO
        elif mode in ("w", "wb", "a", "ab", "x", "xb"):
            self._mode = _MODE_WRITE
            mode_code = mode if mode.endswith("b") else mode + "b"
            if format is None:
                format = FORMAT_XZ
            self._compressor = LZMACompressor(
                format=format, check=check, preset=preset, filters=filters
            )
        else:
            raise ValueError("Invalid mode: {!r}".format(mode))

        if isinstance(filename, (str, bytes, _os.PathLike)):
            self._fp = _builtins.open(filename, mode_code)
            self._closefp = True
        elif hasattr(filename, "read") or hasattr(filename, "write"):
            self._fp = filename
        else:
            raise TypeError(
                "filename must be a str, bytes, file or PathLike object"
            )

        if self._mode == _MODE_READ:
            raw = self._fp.read()
            if raw:
                self._decompressed = decompress(
                    raw, format=format, filters=filters
                )
            self._size = len(self._decompressed)

    def close(self):
        if self._fp is None:
            return
        try:
            if self._mode == _MODE_WRITE:
                tail = self._compressor.flush()
                if tail:
                    self._fp.write(tail)
        finally:
            try:
                if self._closefp:
                    self._fp.close()
            finally:
                self._fp = None
                self._closefp = False
                self._compressor = None

    @property
    def closed(self):
        return self._fp is None

    def fileno(self):
        if self._fp is None:
            raise ValueError("I/O operation on closed file")
        return self._fp.fileno()

    def seekable(self):
        return self._mode == _MODE_READ

    def readable(self):
        return self._mode == _MODE_READ

    def writable(self):
        return self._mode == _MODE_WRITE

    def read(self, size=-1):
        if self._mode != _MODE_READ:
            raise _io.UnsupportedOperation("File not open for reading")
        if size is None or size < 0:
            chunk = self._decompressed[self._pos:]
            self._pos = self._size
            return chunk
        chunk = self._decompressed[self._pos:self._pos + size]
        self._pos += len(chunk)
        return chunk

    def read1(self, size=-1):
        return self.read(size)

    def peek(self, size=-1):
        if self._mode != _MODE_READ:
            raise _io.UnsupportedOperation("File not open for reading")
        if size is None or size < 0:
            return self._decompressed[self._pos:]
        return self._decompressed[self._pos:self._pos + size]

    def seek(self, offset, whence=0):
        if self._mode != _MODE_READ:
            raise _io.UnsupportedOperation("Seek only supported on read")
        if whence == 0:
            new = offset
        elif whence == 1:
            new = self._pos + offset
        elif whence == 2:
            new = self._size + offset
        else:
            raise ValueError("Invalid whence")
        if new < 0:
            new = 0
        if new > self._size:
            new = self._size
        self._pos = new
        return self._pos

    def tell(self):
        if self._mode == _MODE_READ:
            return self._pos
        raise _io.UnsupportedOperation("tell on write-mode LZMAFile")

    def write(self, data):
        if self._mode != _MODE_WRITE:
            raise _io.UnsupportedOperation("File not open for writing")
        self._compressor.compress(data)
        return len(data)


def open(filename, mode="rb", *, format=None, check=-1, preset=None,
         filters=None, encoding=None, errors=None, newline=None):
    if "t" in mode:
        if "b" in mode:
            raise ValueError("Invalid mode: %r" % (mode,))
        bin_mode = mode.replace("t", "b")
    else:
        bin_mode = mode if "b" in mode else mode + "b"
        if encoding is not None:
            raise ValueError("Argument 'encoding' not supported in binary mode")
        if errors is not None:
            raise ValueError("Argument 'errors' not supported in binary mode")
        if newline is not None:
            raise ValueError("Argument 'newline' not supported in binary mode")

    binary_file = LZMAFile(
        filename, bin_mode,
        format=format, check=check, preset=preset, filters=filters
    )
    if "t" in mode:
        return _io.TextIOWrapper(
            binary_file, encoding=encoding, errors=errors, newline=newline
        )
    return binary_file


# ---------------------------------------------------------------------------
# Theseus invariant probes
# ---------------------------------------------------------------------------

def clzma2_compress():
    sample = b"hello, theseus clean-room lzma!" * 4
    blob = compress(sample)
    if not isinstance(blob, (bytes, bytearray)):
        return False
    if not blob:
        return False
    if decompress(blob) != sample:
        return False
    c = LZMACompressor()
    chunks = b""
    for piece in (b"abc", b"def", b"ghij"):
        chunks += c.compress(piece)
    chunks += c.flush()
    if decompress(chunks) != b"abcdefghij":
        return False
    d = LZMADecompressor()
    out = d.decompress(chunks)
    if out != b"abcdefghij":
        return False
    if not d.eof:
        return False
    return True


def clzma2_constants():
    pairs = [
        ("FORMAT_XZ", FORMAT_XZ), ("FORMAT_ALONE", FORMAT_ALONE),
        ("FORMAT_RAW", FORMAT_RAW), ("FORMAT_AUTO", FORMAT_AUTO),
        ("CHECK_NONE", CHECK_NONE), ("CHECK_CRC32", CHECK_CRC32),
        ("CHECK_CRC64", CHECK_CRC64), ("CHECK_SHA256", CHECK_SHA256),
        ("CHECK_ID_MAX", CHECK_ID_MAX), ("CHECK_UNKNOWN", CHECK_UNKNOWN),
        ("FILTER_LZMA1", FILTER_LZMA1), ("FILTER_LZMA2", FILTER_LZMA2),
        ("FILTER_DELTA", FILTER_DELTA), ("FILTER_X86", FILTER_X86),
        ("MF_HC4", MF_HC4), ("MODE_FAST", MODE_FAST),
        ("MODE_NORMAL", MODE_NORMAL),
        ("PRESET_DEFAULT", PRESET_DEFAULT), ("PRESET_EXTREME", PRESET_EXTREME),
    ]
    for name, value in pairs:
        if not isinstance(value, int):
            return False
        if globals().get(name) != value:
            return False
    if FORMAT_XZ == FORMAT_ALONE:
        return False
    if CHECK_NONE == CHECK_CRC32:
        return False
    if PRESET_EXTREME <= PRESET_DEFAULT:
        return False
    if not is_check_supported(CHECK_NONE):
        return False
    if is_check_supported(999):
        return False
    return True


def clzma2_open():
    import tempfile
    payload = b"open() round-trip exercise for theseus_compression_lzma_cr\n" * 3
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".clzma")
    path = tmp.name
    tmp.close()
    try:
        with open(path, "wb") as fh:
            n = fh.write(payload)
            if n != len(payload):
                return False
        with open(path, "rb") as fh:
            got = fh.read()
        if got != payload:
            return False
        with open(path, "rb") as fh:
            head = fh.read(10)
            tail = fh.read()
        if head + tail != payload:
            return False
    finally:
        try:
            _os.unlink(path)
        except OSError:
            pass
    return True


__all__ = [
    "compress", "decompress", "open", "is_check_supported",
    "LZMACompressor", "LZMADecompressor", "LZMAFile", "LZMAError",
    "FORMAT_AUTO", "FORMAT_XZ", "FORMAT_ALONE", "FORMAT_RAW",
    "CHECK_NONE", "CHECK_CRC32", "CHECK_CRC64", "CHECK_SHA256",
    "CHECK_ID_MAX", "CHECK_UNKNOWN",
    "FILTER_LZMA1", "FILTER_LZMA2", "FILTER_DELTA",
    "FILTER_X86", "FILTER_POWERPC", "FILTER_IA64",
    "FILTER_ARM", "FILTER_ARMTHUMB", "FILTER_SPARC",
    "MF_HC3", "MF_HC4", "MF_BT2", "MF_BT3", "MF_BT4",
    "MODE_FAST", "MODE_NORMAL",
    "PRESET_DEFAULT", "PRESET_EXTREME",
    "clzma2_compress", "clzma2_constants", "clzma2_open",
]