"""
theseus_zlib_cr — Clean-room zlib module using ctypes to call libz directly.
No import of the standard `zlib` module.
"""

import ctypes as _ctypes
import ctypes.util as _ctypes_util
import struct as _struct

_libz_name = _ctypes_util.find_library('z')
if _libz_name is None:
    raise ImportError("Could not find libz (zlib C library)")
_libz = _ctypes.CDLL(_libz_name)

# Configure function signatures
_libz.zlibVersion.restype = _ctypes.c_char_p
_libz.zlibVersion.argtypes = []
_libz.adler32.restype = _ctypes.c_ulong
_libz.adler32.argtypes = [_ctypes.c_ulong, _ctypes.c_char_p, _ctypes.c_uint]
_libz.crc32.restype = _ctypes.c_ulong
_libz.crc32.argtypes = [_ctypes.c_ulong, _ctypes.c_char_p, _ctypes.c_uint]

ZLIB_VERSION = _libz.zlibVersion().decode('ascii')
ZLIB_RUNTIME_VERSION = ZLIB_VERSION

DEF_MEM_LEVEL = 8
DEF_BUF_SIZE = 16384
MAX_WBITS = 15
DEFLATED = 8
Z_NO_FLUSH = 0
Z_PARTIAL_FLUSH = 1
Z_SYNC_FLUSH = 2
Z_FULL_FLUSH = 3
Z_FINISH = 4
Z_BLOCK = 5
Z_DEFAULT_STRATEGY = 0
Z_FILTERED = 1
Z_HUFFMAN_ONLY = 2
Z_RLE = 3
Z_FIXED = 4
Z_DEFAULT_COMPRESSION = -1
Z_BEST_SPEED = 1
Z_BEST_COMPRESSION = 9
Z_NO_COMPRESSION = 0
Z_OK = 0
Z_STREAM_END = 1
Z_NEED_DICT = 2
Z_ERRNO = -1
Z_STREAM_ERROR = -2
Z_DATA_ERROR = -3
Z_MEM_ERROR = -4
Z_BUF_ERROR = -5
Z_VERSION_ERROR = -6


class error(Exception):
    pass


def _check(ret, ok=(Z_OK,)):
    if ret not in ok:
        raise error("zlib error %d" % ret)
    return ret


class _z_stream(_ctypes.Structure):
    _fields_ = [
        ('next_in', _ctypes.c_char_p),
        ('avail_in', _ctypes.c_uint),
        ('total_in', _ctypes.c_ulong),
        ('next_out', _ctypes.c_char_p),
        ('avail_out', _ctypes.c_uint),
        ('total_out', _ctypes.c_ulong),
        ('msg', _ctypes.c_char_p),
        ('state', _ctypes.c_void_p),
        ('zalloc', _ctypes.c_void_p),
        ('zfree', _ctypes.c_void_p),
        ('opaque', _ctypes.c_void_p),
        ('data_type', _ctypes.c_int),
        ('adler', _ctypes.c_ulong),
        ('reserved', _ctypes.c_ulong),
    ]


def adler32(data, value=1):
    """Compute an Adler-32 checksum."""
    result = _libz.adler32(_ctypes.c_ulong(value), data, len(data))
    return result & 0xFFFFFFFF


def crc32(data, value=0):
    """Compute a CRC-32 checksum."""
    result = _libz.crc32(_ctypes.c_ulong(value & 0xFFFFFFFF), data, len(data))
    return result & 0xFFFFFFFF


class compressobj:
    """Compression object."""

    def __init__(self, level=Z_DEFAULT_COMPRESSION, method=DEFLATED,
                 wbits=MAX_WBITS, memLevel=DEF_MEM_LEVEL,
                 strategy=Z_DEFAULT_STRATEGY, zdict=None):
        self._stream = _z_stream()
        self._zdict = zdict
        self._finished = False
        _libz.deflateInit2_.argtypes = [
            _ctypes.POINTER(_z_stream), _ctypes.c_int, _ctypes.c_int,
            _ctypes.c_int, _ctypes.c_int, _ctypes.c_int,
            _ctypes.c_char_p, _ctypes.c_int,
        ]
        _libz.deflateInit2_.restype = _ctypes.c_int
        ret = _libz.deflateInit2_(
            _ctypes.byref(self._stream), level, method, wbits, memLevel,
            strategy, ZLIB_VERSION.encode('ascii'), _ctypes.sizeof(_z_stream)
        )
        _check(ret)
        if zdict is not None:
            _libz.deflateSetDictionary.argtypes = [
                _ctypes.POINTER(_z_stream), _ctypes.c_char_p, _ctypes.c_uint
            ]
            _libz.deflateSetDictionary.restype = _ctypes.c_int
            _check(_libz.deflateSetDictionary(_ctypes.byref(self._stream), zdict, len(zdict)))

    def compress(self, data):
        """Compress data, returning a bytes object."""
        if self._finished:
            raise error("compressobj already flushed")
        if not data:
            return b''
        return self._do_compress(data, Z_NO_FLUSH)

    def _do_compress(self, data, flush):
        _libz.deflate.argtypes = [_ctypes.POINTER(_z_stream), _ctypes.c_int]
        _libz.deflate.restype = _ctypes.c_int
        result = b''
        buf_size = max(len(data) + 100, DEF_BUF_SIZE)
        buf = _ctypes.create_string_buffer(buf_size)
        self._stream.next_in = data
        self._stream.avail_in = len(data)
        while True:
            self._stream.next_out = _ctypes.cast(buf, _ctypes.c_char_p)
            self._stream.avail_out = buf_size
            ret = _libz.deflate(_ctypes.byref(self._stream), flush)
            if ret == Z_STREAM_ERROR:
                raise error("deflate error %d" % ret)
            produced = buf_size - self._stream.avail_out
            result += buf.raw[:produced]
            if self._stream.avail_in == 0 and self._stream.avail_out > 0:
                break
            if ret == Z_STREAM_END:
                break
        return result

    def flush(self, mode=Z_FINISH):
        """Flush remaining data."""
        if self._finished:
            return b''
        result = self._do_compress(b'', mode)
        if mode == Z_FINISH:
            _libz.deflateEnd.argtypes = [_ctypes.POINTER(_z_stream)]
            _libz.deflateEnd.restype = _ctypes.c_int
            _libz.deflateEnd(_ctypes.byref(self._stream))
            self._finished = True
        return result

    def copy(self):
        new_obj = object.__new__(compressobj)
        new_obj._stream = _z_stream()
        new_obj._finished = self._finished
        _libz.deflateCopy.argtypes = [_ctypes.POINTER(_z_stream), _ctypes.POINTER(_z_stream)]
        _libz.deflateCopy.restype = _ctypes.c_int
        _check(_libz.deflateCopy(_ctypes.byref(new_obj._stream), _ctypes.byref(self._stream)))
        return new_obj


class decompressobj:
    """Decompressor object."""

    def __init__(self, wbits=MAX_WBITS, zdict=b''):
        self._stream = _z_stream()
        self._zdict = zdict
        self._finished = False
        self.unconsumed_tail = b''
        self.unused_data = b''
        _libz.inflateInit2_.argtypes = [
            _ctypes.POINTER(_z_stream), _ctypes.c_int,
            _ctypes.c_char_p, _ctypes.c_int,
        ]
        _libz.inflateInit2_.restype = _ctypes.c_int
        ret = _libz.inflateInit2_(
            _ctypes.byref(self._stream), wbits,
            ZLIB_VERSION.encode('ascii'), _ctypes.sizeof(_z_stream)
        )
        _check(ret)

    def decompress(self, data, max_length=-1):
        """Decompress data."""
        if self._finished:
            raise error("decompressobj already ended")
        if not data:
            return b''
        _libz.inflate.argtypes = [_ctypes.POINTER(_z_stream), _ctypes.c_int]
        _libz.inflate.restype = _ctypes.c_int
        result = b''
        buf_size = max(len(data) * 4, DEF_BUF_SIZE)
        buf = _ctypes.create_string_buffer(buf_size)
        self._stream.next_in = data
        self._stream.avail_in = len(data)
        while True:
            self._stream.next_out = _ctypes.cast(buf, _ctypes.c_char_p)
            self._stream.avail_out = buf_size
            ret = _libz.inflate(_ctypes.byref(self._stream), Z_NO_FLUSH)
            if ret == Z_NEED_DICT:
                if self._zdict:
                    _libz.inflateSetDictionary.argtypes = [
                        _ctypes.POINTER(_z_stream), _ctypes.c_char_p, _ctypes.c_uint
                    ]
                    _libz.inflateSetDictionary.restype = _ctypes.c_int
                    _check(_libz.inflateSetDictionary(
                        _ctypes.byref(self._stream), self._zdict, len(self._zdict)
                    ))
                    continue
                raise error("No decompression dictionary provided")
            if ret == Z_DATA_ERROR:
                raise error("zlib data error during decompress")
            if ret not in (Z_OK, Z_STREAM_END, Z_BUF_ERROR):
                raise error("inflate error %d" % ret)
            produced = buf_size - self._stream.avail_out
            result += buf.raw[:produced]
            if ret == Z_STREAM_END:
                self._finished = True
                self.unused_data = self._stream.next_in[:self._stream.avail_in] if self._stream.avail_in else b''
                _libz.inflateEnd.argtypes = [_ctypes.POINTER(_z_stream)]
                _libz.inflateEnd.restype = _ctypes.c_int
                _libz.inflateEnd(_ctypes.byref(self._stream))
                break
            if self._stream.avail_in == 0:
                break
        return result

    def flush(self, length=DEF_BUF_SIZE):
        if self._finished:
            return b''
        return self.decompress(b'')


def compress(data, level=Z_DEFAULT_COMPRESSION, wbits=MAX_WBITS):
    """Compress data."""
    c = compressobj(level, DEFLATED, wbits)
    return c.compress(data) + c.flush()


def decompress(data, wbits=MAX_WBITS, bufsize=DEF_BUF_SIZE):
    """Decompress data."""
    d = decompressobj(wbits)
    return d.decompress(data) + d.flush()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def zlib2_compress():
    """compress and decompress round-trip correctly; returns True."""
    data = b'hello world ' * 100
    compressed = compress(data)
    return decompress(compressed) == data


def zlib2_crc32():
    """crc32 returns expected checksum for known data; returns True."""
    return crc32(b'hello world') == 222957957


def zlib2_adler32():
    """adler32 returns expected checksum for known data; returns True."""
    return adler32(b'hello world') == 436929629


__all__ = [
    'compress', 'decompress', 'compressobj', 'decompressobj',
    'adler32', 'crc32', 'error',
    'DEF_MEM_LEVEL', 'DEF_BUF_SIZE', 'MAX_WBITS',
    'DEFLATED', 'Z_NO_FLUSH', 'Z_PARTIAL_FLUSH', 'Z_SYNC_FLUSH',
    'Z_FULL_FLUSH', 'Z_FINISH', 'Z_BLOCK',
    'Z_DEFAULT_STRATEGY', 'Z_FILTERED', 'Z_HUFFMAN_ONLY',
    'Z_DEFAULT_COMPRESSION', 'Z_BEST_SPEED', 'Z_BEST_COMPRESSION', 'Z_NO_COMPRESSION',
    'ZLIB_VERSION', 'ZLIB_RUNTIME_VERSION',
    'zlib2_compress', 'zlib2_crc32', 'zlib2_adler32',
]
