"""
theseus_compression_zlib_cr — Clean-room compression.zlib module (Python 3.14+).

Pure-Python implementation of the DEFLATE / zlib stream format. Does not
import zlib, gzip, compression.zlib, or any other compression library.
Compression emits valid DEFLATE stored blocks; decompression handles
stored, fixed-Huffman, and dynamic-Huffman blocks.
"""

import io as _io
import struct as _struct
import builtins as _builtins


# ---------------------------------------------------------------------------
# Constants (matching the zlib API surface)
# ---------------------------------------------------------------------------

Z_NO_COMPRESSION = 0
Z_BEST_SPEED = 1
Z_BEST_COMPRESSION = 9
Z_DEFAULT_COMPRESSION = -1

Z_FILTERED = 1
Z_HUFFMAN_ONLY = 2
Z_RLE = 3
Z_FIXED = 4
Z_DEFAULT_STRATEGY = 0

Z_NO_FLUSH = 0
Z_PARTIAL_FLUSH = 1
Z_SYNC_FLUSH = 2
Z_FULL_FLUSH = 3
Z_FINISH = 4
Z_BLOCK = 5
Z_TREES = 6

DEFLATED = 8
DEF_BUF_SIZE = 16384
DEF_MEM_LEVEL = 8
MAX_WBITS = 15

ZLIB_VERSION = "1.2.13"
ZLIB_RUNTIME_VERSION = "1.2.13"


class error(Exception):
    """Raised on compression / decompression errors."""


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------

_ADLER_MOD = 65521


def adler32(data, value=1):
    s1 = value & 0xFFFF
    s2 = (value >> 16) & 0xFFFF
    for b in data:
        s1 += b
        if s1 >= _ADLER_MOD:
            s1 -= _ADLER_MOD
        s2 += s1
        if s2 >= _ADLER_MOD:
            s2 -= _ADLER_MOD
    return ((s2 << 16) | s1) & 0xFFFFFFFF


def _build_crc_table():
    table = []
    for n in range(256):
        c = n
        for _ in range(8):
            if c & 1:
                c = (c >> 1) ^ 0xEDB88320
            else:
                c >>= 1
        table.append(c)
    return table


_CRC_TABLE = _build_crc_table()


def crc32(data, value=0):
    crc = (~value) & 0xFFFFFFFF
    table = _CRC_TABLE
    for b in data:
        crc = table[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return (~crc) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# DEFLATE compression (stored blocks only — valid DEFLATE for any input)
# ---------------------------------------------------------------------------

def _deflate_stored(data):
    """Encode raw bytes as a sequence of DEFLATE stored blocks (BTYPE=00)."""
    out = bytearray()
    n = len(data)
    if n == 0:
        # Empty final stored block.
        out.extend(b'\x01\x00\x00\xff\xff')
        return bytes(out)

    offset = 0
    while offset < n:
        chunk_len = n - offset
        if chunk_len > 65535:
            chunk_len = 65535
        is_final = (offset + chunk_len) >= n
        # Header byte: BFINAL in bit 0, BTYPE=00 in bits 1-2.
        out.append(0x01 if is_final else 0x00)
        out.extend(_struct.pack('<HH', chunk_len, (~chunk_len) & 0xFFFF))
        out.extend(data[offset:offset + chunk_len])
        offset += chunk_len
    return bytes(out)


def compress(data, level=Z_DEFAULT_COMPRESSION, wbits=MAX_WBITS):
    """Return a zlib-compressed (or raw DEFLATE) bytes object."""
    if isinstance(data, str):
        raise TypeError("a bytes-like object is required, not 'str'")
    data = bytes(data)

    if not isinstance(level, int):
        raise TypeError("level must be an int")
    if level != -1 and not (0 <= level <= 9):
        raise error("Bad compression level")

    raw = False
    if wbits < 0:
        raw = True
        win = -wbits
        if win < 8 or win > 15:
            raise error("Invalid window size")
    elif wbits > 31:
        raise error("auto-detect window not supported in compress()")
    elif wbits > 15:
        # gzip wrapper not supported here — only zlib + raw.
        raise error("gzip wrapper not supported")
    elif wbits < 8 or wbits > 15:
        raise error("Invalid window size")

    body = _deflate_stored(data)

    if raw:
        return body

    # zlib wrapper: 2-byte header + DEFLATE + 4-byte big-endian Adler-32.
    # CMF: bits 0-3 method (8 = deflate), bits 4-7 window size (CINFO).
    cinfo = (wbits - 8) & 0x0F
    cmf = (cinfo << 4) | 0x08
    # FLG: bits 6-7 = FLEVEL, bit 5 = FDICT (0), bits 0-4 chosen so
    # (CMF*256 + FLG) % 31 == 0.
    if level == 0 or level == 1:
        flevel = 0
    elif level == 9:
        flevel = 3
    elif level == -1 or level == 6:
        flevel = 2
    else:
        flevel = 1
    flg = (flevel << 6)
    rem = (cmf * 256 + flg) % 31
    if rem != 0:
        flg += 31 - rem
    header = bytes([cmf, flg])

    trailer = _struct.pack('>I', adler32(data))
    return header + body + trailer


# ---------------------------------------------------------------------------
# DEFLATE decompression (stored, fixed Huffman, dynamic Huffman)
# ---------------------------------------------------------------------------

# Length codes 257..285
_LENGTH_BASE = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31,
                35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258]
_LENGTH_EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
                 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0]

# Distance codes 0..29
_DIST_BASE = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193,
              257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145,
              8193, 12289, 16385, 24577]
_DIST_EXTRA = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
               7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13]

_CLEN_ORDER = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]


def _build_huffman(lengths):
    """Build a code -> symbol lookup keyed by (bit_length, code)."""
    if not lengths:
        return {}
    max_len = 0
    for L in lengths:
        if L > max_len:
            max_len = L
    if max_len == 0:
        return {}
    bl_count = [0] * (max_len + 1)
    for L in lengths:
        if L > 0:
            bl_count[L] += 1
    next_code = [0] * (max_len + 2)
    code = 0
    for bits in range(1, max_len + 1):
        code = (code + bl_count[bits - 1]) << 1
        next_code[bits] = code
    codes = {}
    for sym, L in enumerate(lengths):
        if L > 0:
            codes[(L, next_code[L])] = sym
            next_code[L] += 1
    return codes


# Pre-build the fixed Huffman tables (RFC 1951 §3.2.6).
_FIXED_LITLEN_LENGTHS = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
_FIXED_DIST_LENGTHS = [5] * 30
_FIXED_LITLEN = _build_huffman(_FIXED_LITLEN_LENGTHS)
_FIXED_DIST = _build_huffman(_FIXED_DIST_LENGTHS)


class _BitStream:
    __slots__ = ('data', 'byte_pos', 'bit_pos')

    def __init__(self, data, start=0):
        self.data = data
        self.byte_pos = start
        self.bit_pos = 0

    def read_bits(self, n):
        value = 0
        data = self.data
        bp = self.byte_pos
        bb = self.bit_pos
        for i in range(n):
            if bp >= len(data):
                raise error("truncated DEFLATE stream")
            bit = (data[bp] >> bb) & 1
            value |= bit << i
            bb += 1
            if bb == 8:
                bb = 0
                bp += 1
        self.byte_pos = bp
        self.bit_pos = bb
        return value

    def align_byte(self):
        if self.bit_pos != 0:
            self.bit_pos = 0
            self.byte_pos += 1

    def read_byte(self):
        if self.byte_pos >= len(self.data):
            raise error("truncated DEFLATE stream")
        b = self.data[self.byte_pos]
        self.byte_pos += 1
        return b


def _decode_symbol(stream, codes):
    code = 0
    length = 0
    while length < 16:
        length += 1
        code = (code << 1) | stream.read_bits(1)
        sym = codes.get((length, code))
        if sym is not None:
            return sym
    raise error("invalid Huffman code")


def _decode_huffman_block(stream, litlen, dist, out):
    while True:
        sym = _decode_symbol(stream, litlen)
        if sym < 256:
            out.append(sym)
        elif sym == 256:
            return
        elif sym <= 285:
            idx = sym - 257
            length = _LENGTH_BASE[idx]
            extra = _LENGTH_EXTRA[idx]
            if extra:
                length += stream.read_bits(extra)
            dsym = _decode_symbol(stream, dist)
            if dsym >= len(_DIST_BASE):
                raise error("invalid distance symbol")
            distance = _DIST_BASE[dsym]
            dextra = _DIST_EXTRA[dsym]
            if dextra:
                distance += stream.read_bits(dextra)
            if distance == 0 or distance > len(out):
                raise error("invalid distance")
            start = len(out) - distance
            # Byte-by-byte copy supports overlap (run-length style).
            for i in range(length):
                out.append(out[start + i])
        else:
            raise error("invalid literal/length symbol")


def _read_dynamic_tables(stream):
    hlit = stream.read_bits(5) + 257
    hdist = stream.read_bits(5) + 1
    hclen = stream.read_bits(4) + 4

    code_lengths = [0] * 19
    for i in range(hclen):
        code_lengths[_CLEN_ORDER[i]] = stream.read_bits(3)
    code_codes = _build_huffman(code_lengths)
    if not code_codes:
        raise error("empty code-length alphabet")

    total = hlit + hdist
    all_lengths = []
    while len(all_lengths) < total:
        sym = _decode_symbol(stream, code_codes)
        if sym < 16:
            all_lengths.append(sym)
        elif sym == 16:
            if not all_lengths:
                raise error("invalid code-length repeat")
            rep = stream.read_bits(2) + 3
            prev = all_lengths[-1]
            for _ in range(rep):
                all_lengths.append(prev)
        elif sym == 17:
            rep = stream.read_bits(3) + 3
            for _ in range(rep):
                all_lengths.append(0)
        elif sym == 18:
            rep = stream.read_bits(7) + 11
            for _ in range(rep):
                all_lengths.append(0)
        else:
            raise error("invalid code-length symbol")
    if len(all_lengths) != total:
        raise error("code-length sequence overran tables")

    litlen = _build_huffman(all_lengths[:hlit])
    dist = _build_huffman(all_lengths[hlit:hlit + hdist])
    return litlen, dist


def _inflate(data, start=0):
    """Decode a raw DEFLATE stream beginning at `start`. Returns (output, end)."""
    stream = _BitStream(data, start)
    out = bytearray()
    while True:
        bfinal = stream.read_bits(1)
        btype = stream.read_bits(2)
        if btype == 0:
            stream.align_byte()
            if stream.byte_pos + 4 > len(data):
                raise error("truncated stored block header")
            length = data[stream.byte_pos] | (data[stream.byte_pos + 1] << 8)
            nlength = data[stream.byte_pos + 2] | (data[stream.byte_pos + 3] << 8)
            stream.byte_pos += 4
            if (length ^ 0xFFFF) != nlength:
                raise error("invalid stored block length pair")
            if stream.byte_pos + length > len(data):
                raise error("truncated stored block")
            out.extend(data[stream.byte_pos:stream.byte_pos + length])
            stream.byte_pos += length
        elif btype == 1:
            _decode_huffman_block(stream, _FIXED_LITLEN, _FIXED_DIST, out)
        elif btype == 2:
            litlen, dist = _read_dynamic_tables(stream)
            _decode_huffman_block(stream, litlen, dist, out)
        else:
            raise error("invalid block type 3")
        if bfinal:
            break
    stream.align_byte()
    return bytes(out), stream.byte_pos


def decompress(data, wbits=MAX_WBITS, bufsize=DEF_BUF_SIZE):
    if isinstance(data, str):
        raise TypeError("a bytes-like object is required, not 'str'")
    data = bytes(data)

    raw = False
    if wbits < 0:
        raw = True
    elif wbits > 31:
        # auto-detect (zlib or gzip) — accept zlib wrapper only here.
        raw = False
    elif wbits > 15:
        # gzip-only — not supported in this clean-room build.
        raise error("gzip wrapper not supported")

    pos = 0
    if not raw:
        if len(data) < 2:
            raise error("incomplete zlib stream")
        cmf = data[0]
        flg = data[1]
        if (cmf * 256 + flg) % 31 != 0:
            raise error("incorrect header check")
        if (cmf & 0x0F) != 8:
            raise error("unknown compression method")
        pos = 2
        if flg & 0x20:
            # Preset dictionary — skip the 4-byte dict id (not supported for use).
            if pos + 4 > len(data):
                raise error("truncated FDICT")
            pos += 4

    output, end = _inflate(data, pos)

    if not raw:
        if end + 4 > len(data):
            raise error("truncated zlib trailer")
        expected = _struct.unpack('>I', data[end:end + 4])[0]
        if adler32(output) != expected:
            raise error("Adler-32 mismatch")
    return output


# ---------------------------------------------------------------------------
# Streaming compressor / decompressor objects
# ---------------------------------------------------------------------------

class Compress:
    """A buffering compressor — collects everything until flush(Z_FINISH)."""

    def __init__(self, level=Z_DEFAULT_COMPRESSION, wbits=MAX_WBITS):
        self._level = level
        self._wbits = wbits
        self._buf = bytearray()
        self._finished = False

    def compress(self, data):
        if self._finished:
            raise error("compressor finished")
        self._buf.extend(data)
        return b''

    def flush(self, mode=Z_FINISH):
        if mode == Z_FINISH:
            if self._finished:
                return b''
            self._finished = True
            out = compress(bytes(self._buf), self._level, self._wbits)
            self._buf = bytearray()
            return out
        return b''


class Decompress:
    """A buffering decompressor — collects everything, decodes on flush()."""

    def __init__(self, wbits=MAX_WBITS):
        self._wbits = wbits
        self._buf = bytearray()
        self.unused_data = b''
        self.unconsumed_tail = b''
        self.eof = False

    def decompress(self, data, max_length=0):
        self._buf.extend(data)
        return b''

    def flush(self, length=DEF_BUF_SIZE):
        if self.eof:
            return b''
        out = decompress(bytes(self._buf), self._wbits)
        self.eof = True
        self._buf = bytearray()
        return out


def compressobj(level=Z_DEFAULT_COMPRESSION, method=DEFLATED,
                wbits=MAX_WBITS, memLevel=DEF_MEM_LEVEL,
                strategy=Z_DEFAULT_STRATEGY, zdict=None):
    if method != DEFLATED:
        raise error("only DEFLATED method supported")
    return Compress(level=level, wbits=wbits)


def decompressobj(wbits=MAX_WBITS, zdict=b''):
    return Decompress(wbits=wbits)


# ---------------------------------------------------------------------------
# File-like wrappers and open()
# ---------------------------------------------------------------------------

class _ZlibReader:
    def __init__(self, raw, own_raw):
        self._raw = raw
        self._own = own_raw
        # Slurp and decompress eagerly — simple and correct.
        compressed = raw.read()
        self._buffer = decompress(compressed)
        self._pos = 0
        self._closed = False

    def read(self, size=-1):
        if self._closed:
            raise ValueError("read on closed file")
        if size is None or size < 0:
            data = self._buffer[self._pos:]
            self._pos = len(self._buffer)
            return bytes(data)
        end = self._pos + size
        data = self._buffer[self._pos:end]
        self._pos += len(data)
        return bytes(data)

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return False

    @property
    def closed(self):
        return self._closed

    def close(self):
        if not self._closed:
            self._closed = True
            if self._own:
                self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class _ZlibWriter:
    def __init__(self, raw, level, own_raw):
        self._raw = raw
        self._own = own_raw
        self._level = level
        self._buffer = bytearray()
        self._closed = False

    def write(self, data):
        if self._closed:
            raise ValueError("write on closed file")
        self._buffer.extend(data)
        return len(data)

    def readable(self):
        return False

    def writable(self):
        return True

    def seekable(self):
        return False

    @property
    def closed(self):
        return self._closed

    def close(self):
        if not self._closed:
            self._closed = True
            self._raw.write(compress(bytes(self._buffer), self._level))
            if self._own:
                self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open(file, mode='rb', level=Z_DEFAULT_COMPRESSION):
    """Open a zlib-compressed file or file-like object as a binary stream."""
    if 'b' not in mode:
        mode = mode + 'b'

    is_path = isinstance(file, (str, bytes)) or hasattr(file, '__fspath__')
    if is_path:
        raw = _builtins.open(file, mode)
        own = True
    else:
        raw = file
        own = False

    if 'r' in mode:
        return _ZlibReader(raw, own)
    if 'w' in mode or 'a' in mode or 'x' in mode:
        return _ZlibWriter(raw, level, own)
    raise ValueError("invalid mode: %r" % mode)


# ---------------------------------------------------------------------------
# Invariant self-tests
# ---------------------------------------------------------------------------

def czlib2_compress():
    """compress / decompress / checksum roundtrip works."""
    try:
        cases = [
            b"",
            b"a",
            b"Hello, World!",
            b"The quick brown fox jumps over the lazy dog. " * 32,
            bytes(range(256)),
            b"\x00" * 1024,
            b"abracadabra" * 100,
        ]
        for data in cases:
            for lvl in (Z_DEFAULT_COMPRESSION, Z_NO_COMPRESSION,
                        Z_BEST_SPEED, 6, Z_BEST_COMPRESSION):
                blob = compress(data, lvl)
                if not isinstance(blob, bytes):
                    return False
                if blob[:1] != b'\x78':
                    return False
                if (blob[0] * 256 + blob[1]) % 31 != 0:
                    return False
                back = decompress(blob)
                if back != data:
                    return False
        # Raw deflate roundtrip.
        raw = compress(b"raw deflate test", 6, -MAX_WBITS)
        if decompress(raw, -MAX_WBITS) != b"raw deflate test":
            return False
        # Checksums.
        if adler32(b"") != 1:
            return False
        if adler32(b"abc") != 0x024D0127:
            return False
        if crc32(b"") != 0:
            return False
        if crc32(b"abc") != 0x352441C2:
            return False
        # Streaming compressor.
        co = compressobj()
        chunk = co.compress(b"streaming ")
        chunk += co.compress(b"data here")
        chunk += co.flush(Z_FINISH)
        if decompress(chunk) != b"streaming data here":
            return False
        # Streaming decompressor.
        do = decompressobj()
        do.decompress(compress(b"hello"))
        if do.flush() != b"hello":
            return False
        return True
    except Exception:
        return False


def czlib2_constants():
    """The full set of zlib constants exists with the canonical values."""
    try:
        if Z_NO_COMPRESSION != 0: return False
        if Z_BEST_SPEED != 1: return False
        if Z_BEST_COMPRESSION != 9: return False
        if Z_DEFAULT_COMPRESSION != -1: return False
        if Z_DEFAULT_STRATEGY != 0: return False
        if Z_FILTERED != 1: return False
        if Z_HUFFMAN_ONLY != 2: return False
        if Z_RLE != 3: return False
        if Z_FIXED != 4: return False
        if Z_NO_FLUSH != 0: return False
        if Z_PARTIAL_FLUSH != 1: return False
        if Z_SYNC_FLUSH != 2: return False
        if Z_FULL_FLUSH != 3: return False
        if Z_FINISH != 4: return False
        if Z_BLOCK != 5: return False
        if Z_TREES != 6: return False
        if DEFLATED != 8: return False
        if MAX_WBITS != 15: return False
        if not isinstance(DEF_BUF_SIZE, int) or DEF_BUF_SIZE <= 0: return False
        if not isinstance(DEF_MEM_LEVEL, int) or DEF_MEM_LEVEL <= 0: return False
        if not isinstance(ZLIB_VERSION, str) or not ZLIB_VERSION: return False
        if not isinstance(ZLIB_RUNTIME_VERSION, str): return False
        if not (Z_BEST_COMPRESSION > Z_BEST_SPEED): return False
        if not issubclass(error, Exception): return False
        return True
    except Exception:
        return False


def czlib2_open():
    """open() round-trips data through a file-like sink/source."""
    try:
        payload = b"open() function test payload " * 25

        # Write through open().
        sink = _io.BytesIO()
        with open(sink, 'wb') as fp:
            fp.write(payload)
        compressed = sink.getvalue()
        if not compressed or len(compressed) < 2:
            return False
        if (compressed[0] * 256 + compressed[1]) % 31 != 0:
            return False

        # Read through open().
        with open(_io.BytesIO(compressed), 'rb') as fp:
            got = fp.read()
        if got != payload:
            return False

        # open() should also read what compress() produced directly.
        direct = compress(payload, Z_BEST_COMPRESSION)
        with open(_io.BytesIO(direct), 'rb') as fp:
            if fp.read() != payload:
                return False

        # Partial reads.
        with open(_io.BytesIO(direct), 'rb') as fp:
            head = fp.read(10)
            tail = fp.read()
            if head + tail != payload:
                return False

        # Context-manager close behavior.
        sink2 = _io.BytesIO()
        writer = open(sink2, 'wb', level=1)
        writer.write(b"x" * 50)
        writer.close()
        if writer.closed is not True:
            return False
        if decompress(sink2.getvalue()) != b"x" * 50:
            return False
        return True
    except Exception:
        return False


__all__ = [
    'compress', 'decompress', 'compressobj', 'decompressobj',
    'adler32', 'crc32', 'open', 'error',
    'DEFLATED', 'DEF_BUF_SIZE', 'DEF_MEM_LEVEL', 'MAX_WBITS',
    'ZLIB_VERSION', 'ZLIB_RUNTIME_VERSION',
    'Z_NO_COMPRESSION', 'Z_BEST_COMPRESSION', 'Z_BEST_SPEED',
    'Z_DEFAULT_COMPRESSION', 'Z_DEFAULT_STRATEGY',
    'Z_FILTERED', 'Z_HUFFMAN_ONLY', 'Z_RLE', 'Z_FIXED',
    'Z_NO_FLUSH', 'Z_PARTIAL_FLUSH', 'Z_SYNC_FLUSH',
    'Z_FULL_FLUSH', 'Z_FINISH', 'Z_BLOCK', 'Z_TREES',
    'czlib2_compress', 'czlib2_constants', 'czlib2_open',
]
