"""Clean-room implementation of compression.gzip (Python 3.14+).

Implements gzip file reading/writing using only Python standard library
modules (zlib for DEFLATE, struct for binary packing, etc.). Does NOT
import the original compression.gzip or gzip modules.
"""

import zlib
import struct
import time
import os
import io
import builtins as _builtins


__all__ = ["BadGzipFile", "GzipFile", "open", "compress", "decompress"]

# Gzip header flag bits
FTEXT = 1
FHCRC = 2
FEXTRA = 4
FNAME = 8
FCOMMENT = 16

READ = 'rb'
WRITE = 'wb'

_COMPRESS_LEVEL_FAST = 1
_COMPRESS_LEVEL_TRADEOFF = 6
_COMPRESS_LEVEL_BEST = 9


class BadGzipFile(OSError):
    """Exception raised in some cases for invalid gzip files."""


def _make_header(compresslevel, mtime):
    """Build a 10-byte gzip header with no optional fields."""
    if mtime is None:
        mtime = 0
    if compresslevel == _COMPRESS_LEVEL_BEST:
        xfl = 2
    elif compresslevel == _COMPRESS_LEVEL_FAST:
        xfl = 4
    else:
        xfl = 0
    return struct.pack(
        "<BBBBLBB",
        0x1f, 0x8b,                       # magic bytes
        8,                                # compression method = deflate
        0,                                # no optional fields
        int(mtime) & 0xFFFFFFFF,          # modification time
        xfl,                              # extra flags
        255,                              # OS = unknown
    )


def compress(data, compresslevel=_COMPRESS_LEVEL_BEST, *, mtime=None):
    """Compress data into a gzip-format bytes object."""
    if mtime is None:
        mtime = 0
    if isinstance(data, (bytes, bytearray)):
        raw = bytes(data)
    else:
        raw = bytes(memoryview(data))
    header = _make_header(compresslevel, mtime)
    compressor = zlib.compressobj(
        compresslevel, zlib.DEFLATED, -zlib.MAX_WBITS,
        zlib.DEF_MEM_LEVEL, 0,
    )
    body = compressor.compress(raw) + compressor.flush()
    crc = zlib.crc32(raw) & 0xFFFFFFFF
    isize = len(raw) & 0xFFFFFFFF
    trailer = struct.pack("<LL", crc, isize)
    return header + body + trailer


def _read_header(fp):
    """Read a gzip header from fp. Returns mtime, or None if at clean EOF."""
    magic = fp.read(2)
    if not magic:
        return None
    if magic != b'\037\213':
        raise BadGzipFile("Not a gzipped file (%r)" % magic)

    rest = fp.read(8)
    if len(rest) < 8:
        raise EOFError(
            "Compressed file ended before the end-of-stream marker was reached"
        )
    method = rest[0]
    flag = rest[1]
    mtime = struct.unpack("<L", rest[2:6])[0]
    if method != 8:
        raise BadGzipFile("Unknown compression method")

    if flag & FEXTRA:
        elen_b = fp.read(2)
        if len(elen_b) < 2:
            raise EOFError("Truncated gzip extra-length field")
        extra_len = struct.unpack("<H", elen_b)[0]
        skipped = fp.read(extra_len)
        if len(skipped) < extra_len:
            raise EOFError("Truncated gzip extra field")
    if flag & FNAME:
        while True:
            s = fp.read(1)
            if not s or s == b'\x00':
                break
    if flag & FCOMMENT:
        while True:
            s = fp.read(1)
            if not s or s == b'\x00':
                break
    if flag & FHCRC:
        fp.read(2)

    return mtime


def decompress(data):
    """Decompress a gzip-format bytes object, supporting concatenated members."""
    if not data:
        return b''

    chunks = []
    fp = io.BytesIO(data)

    while True:
        mtime = _read_header(fp)
        if mtime is None:
            break

        decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
        rest = fp.read()
        try:
            decompressed = decompressor.decompress(rest)
        except zlib.error as err:
            raise BadGzipFile(str(err)) from err
        if not decompressor.eof:
            raise EOFError(
                "Compressed file ended before the end-of-stream marker was reached"
            )

        unused = decompressor.unused_data
        if len(unused) < 8:
            raise EOFError(
                "Compressed file ended before the end-of-stream marker was reached"
            )

        crc32, isize = struct.unpack("<LL", unused[:8])
        actual_crc = zlib.crc32(decompressed) & 0xFFFFFFFF
        if crc32 != actual_crc:
            raise BadGzipFile(
                "CRC check failed 0x%x != 0x%x" % (crc32, actual_crc)
            )
        if isize != (len(decompressed) & 0xFFFFFFFF):
            raise BadGzipFile("Incorrect length of data produced")

        chunks.append(decompressed)

        remainder = unused[8:]
        if not remainder:
            break
        # Continue with any concatenated gzip members
        fp = io.BytesIO(remainder)

    return b''.join(chunks)


class GzipFile(io.BufferedIOBase):
    """File-like object wrapping a gzip-compressed file.

    This clean-room implementation buffers the full payload in memory:
    on write, data is accumulated and gzipped on close; on read, the
    underlying fileobj is fully consumed and decompressed up front.
    """

    myfileobj = None

    def __init__(self, filename=None, mode=None,
                 compresslevel=_COMPRESS_LEVEL_BEST,
                 fileobj=None, mtime=None):
        if mode and ('t' in mode or 'U' in mode):
            raise ValueError("Invalid mode: %r" % mode)
        if mode and 'b' not in mode:
            mode = mode + 'b'

        if fileobj is None:
            fileobj = self.myfileobj = _builtins.open(filename, mode or 'rb')

        if filename is None:
            fname = getattr(fileobj, 'name', '')
            if not isinstance(fname, (str, bytes)):
                fname = ''
            filename = fname
        else:
            filename = os.fspath(filename)

        if mode is None:
            mode = getattr(fileobj, 'mode', 'rb')

        self.fileobj = fileobj
        self.name = filename
        self._compresslevel = compresslevel
        self._mtime = mtime

        if mode.startswith('r'):
            self.mode = READ
            self._read_buf = None
            self._read_pos = 0
        elif mode.startswith(('w', 'a', 'x')):
            self.mode = WRITE
            self._write_buf = bytearray()
        else:
            raise ValueError("Invalid mode: %r" % mode)

    # ---- helpers ------------------------------------------------------

    def _check_open(self):
        if self.fileobj is None:
            raise ValueError("I/O operation on closed file.")

    def _ensure_read(self):
        if self._read_buf is None:
            raw = self.fileobj.read()
            if raw:
                self._read_buf = decompress(raw)
            else:
                self._read_buf = b''

    # ---- read interface -----------------------------------------------

    def read(self, size=-1):
        self._check_open()
        if self.mode != READ:
            raise OSError("read() on write-only GzipFile object")
        self._ensure_read()
        if size is None or size < 0:
            result = self._read_buf[self._read_pos:]
            self._read_pos = len(self._read_buf)
        else:
            end = self._read_pos + size
            result = self._read_buf[self._read_pos:end]
            self._read_pos += len(result)
        return result

    def read1(self, size=-1):
        return self.read(size)

    def readinto(self, b):
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def peek(self, n=0):
        self._check_open()
        if self.mode != READ:
            raise OSError("peek() on write-only GzipFile object")
        self._ensure_read()
        return bytes(self._read_buf[self._read_pos:])

    # ---- write interface ----------------------------------------------

    def write(self, data):
        self._check_open()
        if self.mode != WRITE:
            raise OSError("write() on read-only GzipFile object")
        if isinstance(data, (bytes, bytearray)):
            length = len(data)
            self._write_buf.extend(data)
        else:
            mv = memoryview(data)
            length = mv.nbytes
            self._write_buf.extend(mv.tobytes())
        return length

    # ---- lifecycle ----------------------------------------------------

    def close(self):
        if self.fileobj is None:
            return
        try:
            if self.mode == WRITE:
                compressed = compress(
                    bytes(self._write_buf),
                    self._compresslevel,
                    mtime=self._mtime,
                )
                self.fileobj.write(compressed)
        finally:
            myfileobj = self.myfileobj
            self.myfileobj = None
            self.fileobj = None
            if myfileobj is not None:
                myfileobj.close()

    @property
    def closed(self):
        return self.fileobj is None

    def flush(self, zlib_mode=None):
        self._check_open()
        # Buffered implementation: nothing to flush mid-stream.
        flush = getattr(self.fileobj, 'flush', None)
        if flush is not None and self.mode == WRITE:
            try:
                flush()
            except Exception:
                pass

    def fileno(self):
        return self.fileobj.fileno()

    def readable(self):
        return self.mode == READ

    def writable(self):
        return self.mode == WRITE

    def seekable(self):
        return False

    def __enter__(self):
        if self.fileobj is None:
            raise ValueError("I/O operation on closed file.")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def open(filename, mode='rb', compresslevel=_COMPRESS_LEVEL_BEST,
         encoding=None, errors=None, newline=None):
    """Open a gzip-compressed file in binary or text mode."""
    if 't' in mode:
        if 'b' in mode:
            raise ValueError("Invalid mode: %r" % (mode,))
    else:
        if encoding is not None:
            raise ValueError(
                "Argument 'encoding' not supported in binary mode"
            )
        if errors is not None:
            raise ValueError(
                "Argument 'errors' not supported in binary mode"
            )
        if newline is not None:
            raise ValueError(
                "Argument 'newline' not supported in binary mode"
            )

    gz_mode = mode.replace('t', '')

    if isinstance(filename, (str, bytes, os.PathLike)):
        binary_file = GzipFile(filename, gz_mode, compresslevel)
    elif hasattr(filename, 'read') or hasattr(filename, 'write'):
        binary_file = GzipFile(None, gz_mode, compresslevel, filename)
    else:
        raise TypeError(
            "filename must be a str, bytes, or os.PathLike object, or a file"
        )

    if 't' in mode:
        return io.TextIOWrapper(binary_file, encoding, errors, newline)
    return binary_file


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def cgzip2_compress():
    """Round-trip through compress() and decompress() must reproduce input."""
    try:
        data = b"Hello, World! This is a test of gzip compression. " * 25
        compressed = compress(data)
        # Header sanity: must start with gzip magic.
        if not compressed.startswith(b'\037\213'):
            return False
        # Method byte must indicate DEFLATE.
        if compressed[2] != 8:
            return False
        decompressed = decompress(compressed)
        if decompressed != data:
            return False
        # Empty input round-trip should also work.
        if decompress(compress(b'')) != b'':
            return False
        # Concatenated members should decompress to the concatenation.
        combined = compress(b'AAA') + compress(b'BBB')
        if decompress(combined) != b'AAABBB':
            return False
        return True
    except Exception:
        return False


def cgzip2_classes():
    """GzipFile and BadGzipFile must exist with the right inheritance."""
    try:
        if not isinstance(BadGzipFile, type):
            return False
        if not issubclass(BadGzipFile, OSError):
            return False
        if not isinstance(GzipFile, type):
            return False
        if not issubclass(GzipFile, io.BufferedIOBase):
            return False
        # Instantiating BadGzipFile should be possible.
        err = BadGzipFile("oops")
        if not isinstance(err, OSError):
            return False
        return True
    except Exception:
        return False


def cgzip2_open():
    """open() must support binary read/write and text mode round-trips."""
    import tempfile
    try:
        data = b"Test gzip open functionality with this string!" * 4
        fd, path = tempfile.mkstemp(suffix='.gz')
        os.close(fd)
        try:
            # Binary write/read round-trip.
            with open(path, 'wb') as f:
                if not isinstance(f, GzipFile):
                    return False
                f.write(data)
            with open(path, 'rb') as f:
                if not isinstance(f, GzipFile):
                    return False
                result = f.read()
            if result != data:
                return False

            # Text mode round-trip.
            text = "hello text mode\nsecond line\n"
            with open(path, 'wt', encoding='utf-8') as f:
                f.write(text)
            with open(path, 'rt', encoding='utf-8') as f:
                got = f.read()
            if got != text:
                return False

            # Wrapping a fileobj should also work.
            buf = io.BytesIO()
            with open(buf, 'wb') as f:
                f.write(b"in-memory")
            buf.seek(0)
            with open(buf, 'rb') as f:
                if f.read() != b"in-memory":
                    return False

            return True
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    except Exception:
        return False