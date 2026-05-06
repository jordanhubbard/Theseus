"""Clean-room gzip implementation.

Implements gzip-format compression/decompression using DEFLATE 'stored'
(uncompressed) blocks. No imports from gzip or zlib.
"""

import struct as _struct

_GZIP_MAGIC = b'\x1f\x8b'
_CM_DEFLATE = 0x08

# Flag bits for FLG byte
_FTEXT = 0x01
_FHCRC = 0x02
_FEXTRA = 0x04
_FNAME = 0x08
_FCOMMENT = 0x10

# Maximum size of a single DEFLATE stored block payload.
_MAX_STORED = 0xFFFF


# ---------------------------------------------------------------------------
# CRC-32 (IEEE 802.3, polynomial 0xedb88320)
# ---------------------------------------------------------------------------

def _build_crc_table():
    table = []
    for n in range(256):
        c = n
        for _ in range(8):
            if c & 1:
                c = 0xEDB88320 ^ (c >> 1)
            else:
                c = c >> 1
        table.append(c & 0xFFFFFFFF)
    return table


_CRC_TABLE = _build_crc_table()


def _crc32(data, crc=0):
    crc = (~crc) & 0xFFFFFFFF
    table = _CRC_TABLE
    for b in data:
        crc = table[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return (~crc) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# DEFLATE stored-block encoder / decoder
# ---------------------------------------------------------------------------

def _deflate_stored(data):
    """Encode `data` as one or more DEFLATE 'stored' blocks (BTYPE=00)."""
    out = bytearray()
    n = len(data)

    if n == 0:
        out.append(0x01)  # BFINAL=1, BTYPE=00
        out += _struct.pack('<HH', 0, 0xFFFF)
        return bytes(out)

    pos = 0
    while pos < n:
        remaining = n - pos
        chunk_len = remaining if remaining < _MAX_STORED else _MAX_STORED
        is_last = (pos + chunk_len) >= n
        out.append(0x01 if is_last else 0x00)
        out += _struct.pack('<HH', chunk_len, (~chunk_len) & 0xFFFF)
        out += data[pos:pos + chunk_len]
        pos += chunk_len
    return bytes(out)


def _inflate_stored(data, offset):
    out = bytearray()
    pos = offset
    end = len(data)

    while True:
        if pos >= end:
            raise ValueError("truncated DEFLATE stream")
        header = data[pos]
        pos += 1
        bfinal = header & 0x01
        btype = (header >> 1) & 0x03
        if btype != 0:
            raise ValueError("unsupported DEFLATE block type: %d" % btype)
        if pos + 4 > end:
            raise ValueError("truncated stored block header")
        length = data[pos] | (data[pos + 1] << 8)
        nlen = data[pos + 2] | (data[pos + 3] << 8)
        pos += 4
        if (length ^ 0xFFFF) != nlen:
            raise ValueError("stored block length check failed")
        if pos + length > end:
            raise ValueError("truncated stored block payload")
        out += data[pos:pos + length]
        pos += length
        if bfinal:
            break
    return bytes(out), pos


# ---------------------------------------------------------------------------
# Public compress / decompress
# ---------------------------------------------------------------------------

def compress(data, compresslevel=9, mtime=None):
    """Compress `data` (bytes) into a gzip-format byte string."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    if isinstance(data, bytearray):
        data = bytes(data)
    elif not isinstance(data, (bytes,)):
        try:
            data = bytes(memoryview(data))
        except TypeError:
            raise TypeError("compress() requires bytes-like data")

    out = bytearray()
    out += _GZIP_MAGIC
    out.append(_CM_DEFLATE)
    out.append(0x00)  # FLG
    out += _struct.pack('<I', 0 if mtime is None else (int(mtime) & 0xFFFFFFFF))
    out.append(0x00)  # XFL
    out.append(0xFF)  # OS = unknown

    out += _deflate_stored(data)

    out += _struct.pack('<I', _crc32(data))
    out += _struct.pack('<I', len(data) & 0xFFFFFFFF)
    return bytes(out)


def _read_cstring(data, pos):
    end = data.find(b'\x00', pos)
    if end < 0:
        raise ValueError("unterminated string field in gzip header")
    return data[pos:end], end + 1


def decompress(data):
    """Decompress `data`, a gzip-format byte string."""
    if isinstance(data, bytearray):
        data = bytes(data)
    elif not isinstance(data, bytes):
        try:
            data = bytes(memoryview(data))
        except TypeError:
            raise TypeError("decompress() requires bytes-like data")

    out = bytearray()
    pos = 0
    n = len(data)

    while pos < n:
        if n - pos < 18:
            raise ValueError("not a gzip file (too short)")
        if data[pos:pos + 2] != _GZIP_MAGIC:
            raise ValueError("not a gzip file (bad magic)")
        if data[pos + 2] != _CM_DEFLATE:
            raise ValueError("unknown gzip compression method: %d" % data[pos + 2])
        flg = data[pos + 3]
        pos += 10

        if flg & _FEXTRA:
            if pos + 2 > n:
                raise ValueError("truncated FEXTRA length")
            xlen = data[pos] | (data[pos + 1] << 8)
            pos += 2 + xlen
            if pos > n:
                raise ValueError("truncated FEXTRA field")
        if flg & _FNAME:
            _, pos = _read_cstring(data, pos)
        if flg & _FCOMMENT:
            _, pos = _read_cstring(data, pos)
        if flg & _FHCRC:
            pos += 2
            if pos > n:
                raise ValueError("truncated FHCRC field")

        decompressed, pos = _inflate_stored(data, pos)

        if pos + 8 > n:
            raise ValueError("truncated gzip trailer")
        expected_crc = _struct.unpack_from('<I', data, pos)[0]
        expected_size = _struct.unpack_from('<I', data, pos + 4)[0]
        pos += 8

        if _crc32(decompressed) != expected_crc:
            raise ValueError("CRC check failed")
        if (len(decompressed) & 0xFFFFFFFF) != expected_size:
            raise ValueError("incorrect length check")

        out += decompressed

        if pos == n:
            break
        if data[pos:pos + 2] != _GZIP_MAGIC:
            break

    return bytes(out)


# ---------------------------------------------------------------------------
# GzipFile: minimal file-like wrapper
# ---------------------------------------------------------------------------

class GzipFile:
    def __init__(self, filename=None, mode=None, compresslevel=9,
                 fileobj=None, mtime=None):
        if fileobj is None and filename is None:
            raise TypeError("GzipFile requires fileobj or filename")

        if mode is None:
            mode = 'rb'

        m = mode.replace('b', '').replace('t', '')
        if not m:
            m = 'r'
        if m not in ('r', 'w', 'a', 'x'):
            raise ValueError("invalid mode: %r" % mode)

        self._mode = m
        self._compresslevel = compresslevel
        self._mtime = mtime
        self._owns_fileobj = False

        if fileobj is None:
            file_mode = m + 'b'
            fileobj = open(filename, file_mode)
            self._owns_fileobj = True

        self.fileobj = fileobj
        self.name = filename if filename is not None else getattr(fileobj, 'name', '')
        self._closed = False

        self._write_buffer = bytearray()
        self._read_data = None
        self._read_pos = 0

    def writable(self):
        return self._mode in ('w', 'a', 'x')

    def readable(self):
        return self._mode == 'r'

    def write(self, data):
        if not self.writable():
            raise OSError("GzipFile not opened for writing")
        if self._closed:
            raise ValueError("write on closed GzipFile")
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(data, memoryview):
            data = bytes(data)
        self._write_buffer += data
        return len(data)

    def _ensure_read(self):
        if self._read_data is None:
            raw = self.fileobj.read()
            self._read_data = decompress(raw) if raw else b''
            self._read_pos = 0

    def read(self, size=-1):
        if not self.readable():
            raise OSError("GzipFile not opened for reading")
        if self._closed:
            raise ValueError("read on closed GzipFile")
        self._ensure_read()
        if size is None or size < 0:
            chunk = self._read_data[self._read_pos:]
            self._read_pos = len(self._read_data)
            return chunk
        end = self._read_pos + int(size)
        chunk = self._read_data[self._read_pos:end]
        self._read_pos = end
        return chunk

    def read1(self, size=-1):
        return self.read(size)

    def readline(self, size=-1):
        if not self.readable():
            raise OSError("GzipFile not opened for reading")
        self._ensure_read()
        data = self._read_data
        start = self._read_pos
        if start >= len(data):
            return b''
        idx = data.find(b'\n', start)
        if idx == -1:
            end = len(data)
        else:
            end = idx + 1
        if size is not None and size >= 0 and (end - start) > size:
            end = start + size
        line = data[start:end]
        self._read_pos = end
        return line

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def flush(self):
        if hasattr(self.fileobj, 'flush'):
            self.fileobj.flush()

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            if self.writable():
                payload = compress(bytes(self._write_buffer),
                                   compresslevel=self._compresslevel,
                                   mtime=self._mtime)
                self.fileobj.write(payload)
                if hasattr(self.fileobj, 'flush'):
                    self.fileobj.flush()
        finally:
            if self._owns_fileobj:
                try:
                    self.fileobj.close()
                except Exception:
                    pass

    @property
    def closed(self):
        return self._closed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


# ---------------------------------------------------------------------------
# Invariant helpers (gzip2_*) — zero-arg self-tests returning True
# ---------------------------------------------------------------------------

def gzip2_magic():
    """Verify gzip streams begin with the canonical two-byte magic 1f 8b."""
    sample_inputs = (b'', b'a', b'hello, world', b'\x00\x01\x02\x03')
    for sample in sample_inputs:
        blob = compress(sample)
        if blob[:2] != b'\x1f\x8b':
            return False
    return True


def gzip2_compress_decompress():
    """Verify compress/decompress round-trips a representative set of inputs."""
    samples = (
        b'',
        b'a',
        b'hello, world',
        b'\x00' * 100,
        b'The quick brown fox jumps over the lazy dog.',
        bytes(range(256)),
        b'abc' * 1000,
    )
    for sample in samples:
        if decompress(compress(sample)) != sample:
            return False
    return True


def gzip2_round_trip():
    """Verify a longer, varied round-trip including binary and repeated data."""
    payloads = (
        b'',
        b'\xff' * 1,
        b'gzip round trip self-test payload',
        bytes(range(256)) * 4,
        b'repeat-me ' * 500,
    )
    for payload in payloads:
        encoded = compress(payload)
        if encoded[:2] != b'\x1f\x8b':
            return False
        if encoded[2] != 0x08:
            return False
        decoded = decompress(encoded)
        if decoded != payload:
            return False
    return True


__all__ = [
    'compress',
    'decompress',
    'GzipFile',
    'gzip2_magic',
    'gzip2_compress_decompress',
    'gzip2_round_trip',
]