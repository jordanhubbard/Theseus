"""
theseus_mmap_cr — clean-room reimplementation of a subset of Python's mmap module.

No use of the original `mmap` module. The memory-mapped file is emulated with a
bytearray buffer; this is sufficient for the behavioral invariants which only
exercise the in-memory buffer surface (read/write/find/seek/tell/slice).
"""

import os as _os

# Access mode constants (mirrors mmap module values, but defined locally).
ACCESS_DEFAULT = 0
ACCESS_READ = 1
ACCESS_WRITE = 2
ACCESS_COPY = 3

# Protection flags (POSIX-style).
PROT_NONE = 0
PROT_READ = 1
PROT_WRITE = 2
PROT_EXEC = 4

# MAP flags (POSIX-style).
MAP_SHARED = 1
MAP_PRIVATE = 2
MAP_ANON = 32
MAP_ANONYMOUS = 32

PAGESIZE = 4096
ALLOCATIONGRANULARITY = 4096


class error(OSError):
    """Raised for mmap-related errors. Mirrors mmap.error which aliases OSError."""
    pass


def _coerce_bytes(value):
    """Convert input to bytes — accepts bytes, bytearray, memoryview, int iterables."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, int):
        if not 0 <= value <= 0xFF:
            raise ValueError("byte must be in range(0, 256)")
        return bytes([value])
    try:
        return bytes(value)
    except TypeError:
        raise TypeError("a bytes-like object is required")


class mmap:
    """
    Clean-room mmap-like object backed by a bytearray.

    Supports the subset of behavior exercised by the Theseus invariants:
      - construction with an optional fileno (-1 means anonymous) and length
      - read/write/seek/tell/find/rfind
      - indexing and slicing (read & write)
      - len(), close(), context-manager protocol
      - flush() (no-op for the anonymous case)
    """

    def __init__(self, fileno=-1, length=0, flags=MAP_SHARED, prot=PROT_READ | PROT_WRITE,
                 access=ACCESS_DEFAULT, offset=0):
        if length < 0:
            raise ValueError("memory mapped length must be positive")
        if offset < 0:
            raise OverflowError("memory mapped offset must be positive")

        self._closed = False
        self._pos = 0
        self._access = access if access != ACCESS_DEFAULT else (
            ACCESS_READ if prot == PROT_READ else ACCESS_WRITE
        )

        if fileno == -1:
            # Anonymous mapping — pure in-memory buffer.
            if length == 0:
                raise ValueError("cannot mmap an empty file")
            self._buf = bytearray(length)
        else:
            # File-backed: read existing bytes from the descriptor.
            try:
                st = _os.fstat(fileno)
            except OSError as e:
                raise error(str(e))
            file_size = st.st_size
            if length == 0:
                if offset > file_size:
                    raise ValueError("mmap offset is greater than file size")
                length = file_size - offset
            if offset + length > file_size:
                # For write/copy access we conceptually grow the buffer;
                # for read-only mappings this is an error.
                if self._access == ACCESS_READ:
                    raise ValueError("mmap length is greater than file size")
            try:
                cur = _os.lseek(fileno, offset, 0)
                data = _os.read(fileno, length)
                # Restore position (best-effort).
                try:
                    _os.lseek(fileno, cur, 0)
                except OSError:
                    pass
            except OSError as e:
                raise error(str(e))
            if len(data) < length:
                data = data + bytes(length - len(data))
            self._buf = bytearray(data)

        self._size = len(self._buf)

    # ---- context manager ------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # ---- lifecycle ------------------------------------------------------
    def close(self):
        self._closed = True
        self._buf = bytearray()
        self._size = 0
        self._pos = 0

    @property
    def closed(self):
        return self._closed

    def _check(self):
        if self._closed:
            raise ValueError("mmap closed or invalid")

    def _check_writable(self):
        self._check()
        if self._access == ACCESS_READ:
            raise TypeError("mmap can't modify a read-only memory map")

    # ---- size / length --------------------------------------------------
    def __len__(self):
        self._check()
        return self._size

    def size(self):
        self._check()
        return self._size

    def resize(self, newsize):
        self._check_writable()
        if newsize < 0:
            raise ValueError("new size must be non-negative")
        if newsize < self._size:
            del self._buf[newsize:]
        else:
            self._buf.extend(bytes(newsize - self._size))
        self._size = newsize
        if self._pos > self._size:
            self._pos = self._size

    # ---- position management -------------------------------------------
    def tell(self):
        self._check()
        return self._pos

    def seek(self, pos, whence=0):
        self._check()
        if whence == 0:
            new_pos = pos
        elif whence == 1:
            new_pos = self._pos + pos
        elif whence == 2:
            new_pos = self._size + pos
        else:
            raise ValueError("unknown seek type")
        if new_pos < 0 or new_pos > self._size:
            raise ValueError("seek out of range")
        self._pos = new_pos
        # Real mmap.seek returns None.
        return None

    # ---- reading --------------------------------------------------------
    def read(self, n=None):
        self._check()
        remaining = self._size - self._pos
        if n is None or n < 0:
            n = remaining
        else:
            n = min(n, remaining)
        out = bytes(self._buf[self._pos:self._pos + n])
        self._pos += n
        return out

    def read_byte(self):
        self._check()
        if self._pos >= self._size:
            raise ValueError("read byte out of range")
        b = self._buf[self._pos]
        self._pos += 1
        return b

    def readline(self):
        self._check()
        start = self._pos
        idx = self._buf.find(b"\n", start, self._size)
        if idx == -1:
            end = self._size
        else:
            end = idx + 1
        out = bytes(self._buf[start:end])
        self._pos = end
        return out

    # ---- writing --------------------------------------------------------
    def write(self, data):
        self._check_writable()
        b = _coerce_bytes(data)
        end = self._pos + len(b)
        if end > self._size:
            raise ValueError("data out of range")
        self._buf[self._pos:end] = b
        self._pos = end
        return len(b)

    def write_byte(self, byte):
        self._check_writable()
        if isinstance(byte, (bytes, bytearray)):
            if len(byte) != 1:
                raise TypeError("write_byte requires a single byte")
            value = byte[0]
        elif isinstance(byte, int):
            if not 0 <= byte <= 0xFF:
                raise ValueError("byte must be in range(0, 256)")
            value = byte
        else:
            raise TypeError("write_byte requires a single byte")
        if self._pos >= self._size:
            raise ValueError("write byte out of range")
        self._buf[self._pos] = value
        self._pos += 1

    # ---- searching ------------------------------------------------------
    def find(self, sub, start=None, end=None):
        self._check()
        b = _coerce_bytes(sub)
        if start is None:
            start = self._pos
        if end is None:
            end = self._size
        # Clamp to buffer extents (mmap.find uses absolute offsets).
        if start < 0:
            start = max(0, self._size + start)
        if end < 0:
            end = max(0, self._size + end)
        start = min(start, self._size)
        end = min(end, self._size)
        return self._buf.find(b, start, end)

    def rfind(self, sub, start=None, end=None):
        self._check()
        b = _coerce_bytes(sub)
        if start is None:
            start = self._pos
        if end is None:
            end = self._size
        if start < 0:
            start = max(0, self._size + start)
        if end < 0:
            end = max(0, self._size + end)
        start = min(start, self._size)
        end = min(end, self._size)
        return self._buf.rfind(b, start, end)

    # ---- bulk operations ------------------------------------------------
    def move(self, dest, src, count):
        self._check_writable()
        if (dest < 0 or src < 0 or count < 0
                or dest + count > self._size or src + count > self._size):
            raise ValueError("source, destination, or count out of range")
        chunk = bytes(self._buf[src:src + count])
        self._buf[dest:dest + count] = chunk

    def flush(self, offset=0, size=None):
        self._check()
        if size is None:
            size = self._size
        if offset < 0 or size < 0 or offset + size > self._size:
            raise ValueError("flush values out of range")
        # Anonymous-only mapping — flush is a no-op but must succeed.
        return None

    def madvise(self, option, start=0, length=None):
        self._check()
        return None

    # ---- indexing / slicing --------------------------------------------
    def _normalize_index(self, idx):
        if idx < 0:
            idx += self._size
        if idx < 0 or idx >= self._size:
            raise IndexError("mmap index out of range")
        return idx

    def __getitem__(self, key):
        self._check()
        if isinstance(key, slice):
            return bytes(self._buf[key.start:key.stop:key.step] if False else self._buf.__getitem__(key))
        if isinstance(key, int):
            return self._buf[self._normalize_index(key)]
        raise TypeError("mmap indices must be integers or slices")

    def __setitem__(self, key, value):
        self._check_writable()
        if isinstance(key, slice):
            data = _coerce_bytes(value)
            indices = range(*key.indices(self._size))
            if len(indices) != len(data):
                raise IndexError("mmap slice assignment is wrong size")
            if key.step in (None, 1):
                self._buf[key.start if key.start is not None else 0:
                          key.stop if key.stop is not None else self._size] = data
            else:
                for i, b in zip(indices, data):
                    self._buf[i] = b
            return
        if isinstance(key, int):
            i = self._normalize_index(key)
            if isinstance(value, int):
                if not 0 <= value <= 0xFF:
                    raise ValueError("mmap byte must be in range(0, 256)")
                self._buf[i] = value
            else:
                b = _coerce_bytes(value)
                if len(b) != 1:
                    raise ValueError("mmap assignment must be a single byte")
                self._buf[i] = b[0]
            return
        raise TypeError("mmap indices must be integers or slices")

    def __iter__(self):
        self._check()
        for byte in bytes(self._buf):
            yield byte

    def __contains__(self, sub):
        self._check()
        return self.find(sub, 0, self._size) != -1


# ---------------------------------------------------------------------------
# Behavioral invariants
# ---------------------------------------------------------------------------

def mmap2_write_read():
    """
    Construct an anonymous mmap, write data into it, seek to the start,
    and verify the bytes can be read back. Also exercises slicing and
    write_byte / read_byte.
    """
    try:
        m = mmap(-1, 32)
    except Exception:
        return False

    try:
        # Initial contents are zero bytes.
        if len(m) != 32:
            return False
        if bytes(m[0:32]) != b"\x00" * 32:
            return False

        # Sequential write.
        payload = b"hello clean room mmap!"
        n = m.write(payload)
        if n != len(payload):
            return False
        if m.tell() != len(payload):
            return False

        # write_byte appends one more byte.
        m.write_byte(0x21)  # '!'
        if m.tell() != len(payload) + 1:
            return False

        # Read it back from the start.
        m.seek(0)
        first = m.read(len(payload))
        if first != payload:
            return False
        last = m.read_byte()
        if last != 0x21:
            return False

        # Slice access.
        if bytes(m[0:5]) != b"hello":
            return False

        # Slice assignment of equal length.
        m[0:5] = b"HELLO"
        if bytes(m[0:5]) != b"HELLO":
            return False

        # Single-byte item assignment.
        m[5] = ord("_")
        if m[5] != ord("_"):
            return False

        m.close()
    except Exception:
        return False
    return True


def mmap2_find():
    """
    Verify that find() locates substrings, returns -1 on miss, and that
    rfind() and the `in` operator behave correctly.
    """
    try:
        text = b"the quick brown fox jumps over the lazy dog"
        m = mmap(-1, len(text))
        m.write(text)
        m.seek(0)

        if m.find(b"quick") != 4:
            return False
        if m.find(b"fox") != 16:
            return False
        if m.find(b"cat") != -1:
            return False
        # Bounded find.
        if m.find(b"the", 1) != 31:
            return False
        if m.find(b"the", 0, 5) != 0:
            return False
        # rfind.
        if m.rfind(b"the") != 31:
            return False
        if m.rfind(b"the", 0, 10) != 0:
            return False
        # `in` operator.
        if b"lazy" not in m:
            return False
        if b"absent" in m:
            return False

        m.close()
    except Exception:
        return False
    return True


def mmap2_seek_tell():
    """
    Verify seek/tell semantics across SEEK_SET, SEEK_CUR, SEEK_END,
    out-of-range rejection, and that read/write update tell() correctly.
    """
    try:
        m = mmap(-1, 64)
        if m.tell() != 0:
            return False

        # SEEK_SET
        m.seek(10, 0)
        if m.tell() != 10:
            return False

        # SEEK_CUR
        m.seek(5, 1)
        if m.tell() != 15:
            return False
        m.seek(-3, 1)
        if m.tell() != 12:
            return False

        # SEEK_END
        m.seek(0, 2)
        if m.tell() != 64:
            return False
        m.seek(-4, 2)
        if m.tell() != 60:
            return False

        # Out-of-range raises ValueError.
        try:
            m.seek(1000, 0)
            return False
        except ValueError:
            pass
        try:
            m.seek(-1, 0)
            return False
        except ValueError:
            pass
        try:
            m.seek(0, 99)
            return False
        except ValueError:
            pass

        # write advances tell().
        m.seek(0)
        m.write(b"abcdef")
        if m.tell() != 6:
            return False
        # read advances tell().
        m.seek(0)
        if m.read(3) != b"abc":
            return False
        if m.tell() != 3:
            return False
        # seek to past-end exact boundary is allowed.
        m.seek(64, 0)
        if m.tell() != 64:
            return False

        m.close()
    except Exception:
        return False
    return True