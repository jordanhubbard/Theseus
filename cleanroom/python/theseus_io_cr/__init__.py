"""Clean-room implementation of a minimal io module for Theseus.

This module provides BytesIO, StringIO, and open() implemented from scratch
without importing the standard library `io` module.
"""

import os as _os
import sys as _sys


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class UnsupportedOperation(OSError, ValueError):
    """Raised when an unsupported operation is attempted on a stream."""
    pass


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------

class IOBase:
    """Abstract base class for all I/O streams."""

    def __init__(self):
        self._closed = False

    @property
    def closed(self):
        return self._closed

    def close(self):
        self._closed = True

    def _check_closed(self):
        if self._closed:
            raise ValueError("I/O operation on closed stream")

    def readable(self):
        return False

    def writable(self):
        return False

    def seekable(self):
        return False

    def flush(self):
        self._check_closed()

    def __enter__(self):
        self._check_closed()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def readline(self, size=-1):
        raise UnsupportedOperation("readline")

    def readlines(self, hint=-1):
        result = []
        total = 0
        for line in self:
            result.append(line)
            total += len(line)
            if 0 < hint <= total:
                break
        return result

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def tell(self):
        return self.seek(0, 1)

    def seek(self, offset, whence=0):
        raise UnsupportedOperation("seek")

    def truncate(self, size=None):
        raise UnsupportedOperation("truncate")


# ---------------------------------------------------------------------------
# BytesIO
# ---------------------------------------------------------------------------

class BytesIO(IOBase):
    """In-memory binary stream backed by a bytearray."""

    def __init__(self, initial_bytes=b""):
        super().__init__()
        if initial_bytes is None:
            initial_bytes = b""
        if isinstance(initial_bytes, str):
            raise TypeError("a bytes-like object is required, not 'str'")
        self._buffer = bytearray(initial_bytes)
        self._pos = 0

    def readable(self):
        self._check_closed()
        return True

    def writable(self):
        self._check_closed()
        return True

    def seekable(self):
        self._check_closed()
        return True

    def getvalue(self):
        self._check_closed()
        return bytes(self._buffer)

    def getbuffer(self):
        self._check_closed()
        return memoryview(self._buffer)

    def read(self, size=-1):
        self._check_closed()
        if size is None or size < 0:
            end = len(self._buffer)
        else:
            end = min(self._pos + size, len(self._buffer))
        data = bytes(self._buffer[self._pos:end])
        self._pos = end
        return data

    def read1(self, size=-1):
        return self.read(size)

    def readline(self, size=-1):
        self._check_closed()
        if size is None:
            size = -1
        buf = self._buffer
        n = len(buf)
        start = self._pos
        if start >= n:
            return b""
        # find newline
        idx = buf.find(b"\n", start)
        if idx == -1:
            end = n
        else:
            end = idx + 1
        if size is not None and size >= 0:
            end = min(end, start + size)
        data = bytes(buf[start:end])
        self._pos = end
        return data

    def write(self, data):
        self._check_closed()
        if isinstance(data, str):
            raise TypeError("a bytes-like object is required, not 'str'")
        if not isinstance(data, (bytes, bytearray, memoryview)):
            data = bytes(data)
        if isinstance(data, memoryview):
            data = data.tobytes()
        n = len(data)
        if n == 0:
            return 0
        pos = self._pos
        end = pos + n
        buflen = len(self._buffer)
        if pos > buflen:
            # pad with zero bytes
            self._buffer.extend(b"\x00" * (pos - buflen))
            buflen = pos
        if end <= buflen:
            self._buffer[pos:end] = data
        else:
            # overwrite tail and extend
            self._buffer[pos:buflen] = data[: buflen - pos]
            self._buffer.extend(data[buflen - pos:])
        self._pos = end
        return n

    def seek(self, offset, whence=0):
        self._check_closed()
        if whence == 0:
            if offset < 0:
                raise ValueError("negative seek position %r" % (offset,))
            new_pos = offset
        elif whence == 1:
            new_pos = max(0, self._pos + offset)
        elif whence == 2:
            new_pos = max(0, len(self._buffer) + offset)
        else:
            raise ValueError("invalid whence (%r, should be 0, 1 or 2)" % (whence,))
        self._pos = new_pos
        return new_pos

    def tell(self):
        self._check_closed()
        return self._pos

    def truncate(self, size=None):
        self._check_closed()
        if size is None:
            size = self._pos
        if size < 0:
            raise ValueError("negative size")
        if size < len(self._buffer):
            del self._buffer[size:]
        else:
            self._buffer.extend(b"\x00" * (size - len(self._buffer)))
        return size


# ---------------------------------------------------------------------------
# StringIO
# ---------------------------------------------------------------------------

class StringIO(IOBase):
    """In-memory text stream backed by a list of characters."""

    def __init__(self, initial_value="", newline="\n"):
        super().__init__()
        if newline is not None and newline not in ("", "\n", "\r", "\r\n"):
            raise ValueError("illegal newline value: %r" % (newline,))
        self._newline = newline
        # Stored value normalizes \r\n / \r per newline argument.
        if initial_value is None:
            initial_value = ""
        if not isinstance(initial_value, str):
            raise TypeError("initial_value must be str or None, not %s" %
                            type(initial_value).__name__)
        self._buffer = list(initial_value)
        self._pos = 0

    def readable(self):
        self._check_closed()
        return True

    def writable(self):
        self._check_closed()
        return True

    def seekable(self):
        self._check_closed()
        return True

    def getvalue(self):
        self._check_closed()
        return "".join(self._buffer)

    def read(self, size=-1):
        self._check_closed()
        if size is None or size < 0:
            end = len(self._buffer)
        else:
            end = min(self._pos + size, len(self._buffer))
        data = "".join(self._buffer[self._pos:end])
        self._pos = end
        return data

    def readline(self, size=-1):
        self._check_closed()
        if size is None:
            size = -1
        buf = self._buffer
        n = len(buf)
        start = self._pos
        if start >= n:
            return ""
        i = start
        while i < n:
            if buf[i] == "\n":
                i += 1
                break
            i += 1
        if size is not None and size >= 0:
            i = min(i, start + size)
        data = "".join(buf[start:i])
        self._pos = i
        return data

    def write(self, s):
        self._check_closed()
        if not isinstance(s, str):
            raise TypeError("string argument expected, got %r" %
                            (type(s).__name__,))
        # Apply newline translation similar to io.StringIO.
        if self._newline is None:
            # universal newline mode: translate \r\n and \r -> \n
            s = s.replace("\r\n", "\n").replace("\r", "\n")
        elif self._newline == "":
            # do not translate
            pass
        elif self._newline == "\n":
            pass
        else:
            # translate \n -> newline argument
            s = s.replace("\n", self._newline)
        n = len(s)
        if n == 0:
            return 0
        pos = self._pos
        buflen = len(self._buffer)
        if pos > buflen:
            self._buffer.extend(["\x00"] * (pos - buflen))
            buflen = pos
        end = pos + n
        chars = list(s)
        if end <= buflen:
            self._buffer[pos:end] = chars
        else:
            self._buffer[pos:buflen] = chars[: buflen - pos]
            self._buffer.extend(chars[buflen - pos:])
        self._pos = end
        return n

    def seek(self, offset, whence=0):
        self._check_closed()
        if whence == 0:
            if offset < 0:
                raise ValueError("negative seek position %r" % (offset,))
            new_pos = offset
        elif whence == 1:
            if offset != 0:
                raise UnsupportedOperation("can't do nonzero cur-relative seeks")
            new_pos = self._pos
        elif whence == 2:
            if offset != 0:
                raise UnsupportedOperation("can't do nonzero end-relative seeks")
            new_pos = len(self._buffer)
        else:
            raise ValueError("invalid whence (%r, should be 0, 1 or 2)" % (whence,))
        self._pos = new_pos
        return new_pos

    def tell(self):
        self._check_closed()
        return self._pos

    def truncate(self, size=None):
        self._check_closed()
        if size is None:
            size = self._pos
        if size < 0:
            raise ValueError("negative size")
        if size < len(self._buffer):
            del self._buffer[size:]
        else:
            self._buffer.extend(["\x00"] * (size - len(self._buffer)))
        return size


# ---------------------------------------------------------------------------
# File-backed streams
# ---------------------------------------------------------------------------

def _parse_mode(mode):
    """Parse a file mode string into a normalized dict of flags."""
    if not isinstance(mode, str):
        raise TypeError("mode must be a string")
    seen = set()
    for c in mode:
        if c in seen:
            raise ValueError("invalid mode: %r" % (mode,))
        seen.add(c)
    creating = "x" in mode
    reading = "r" in mode
    writing = "w" in mode
    appending = "a" in mode
    updating = "+" in mode
    binary = "b" in mode
    text = "t" in mode
    if binary and text:
        raise ValueError("can't have text and binary mode at once")
    if creating + reading + writing + appending > 1:
        raise ValueError("must have exactly one of create/read/write/append mode")
    if not (creating or reading or writing or appending):
        raise ValueError("Must have exactly one of create/read/write/append mode and at most one plus")
    return {
        "creating": creating,
        "reading": reading,
        "writing": writing,
        "appending": appending,
        "updating": updating,
        "binary": binary,
        "text": text or not binary,
    }


def _build_os_flags(flags):
    f = 0
    if flags["reading"] and not flags["updating"]:
        f |= _os.O_RDONLY
    elif flags["updating"]:
        f |= _os.O_RDWR
        if flags["writing"]:
            f |= _os.O_CREAT | _os.O_TRUNC
        elif flags["creating"]:
            f |= _os.O_CREAT | _os.O_EXCL
        elif flags["appending"]:
            f |= _os.O_CREAT | _os.O_APPEND
    else:
        f |= _os.O_WRONLY
        if flags["writing"]:
            f |= _os.O_CREAT | _os.O_TRUNC
        elif flags["creating"]:
            f |= _os.O_CREAT | _os.O_EXCL
        elif flags["appending"]:
            f |= _os.O_CREAT | _os.O_APPEND
    if hasattr(_os, "O_BINARY"):
        f |= _os.O_BINARY
    return f


class _FileStream(IOBase):
    """Minimal binary file stream wrapping an OS-level fd."""

    def __init__(self, file, mode="r", closefd=True):
        super().__init__()
        flags = _parse_mode(mode)
        self._flags = flags
        self._closefd = closefd
        if isinstance(file, int):
            self._fd = file
            self._name = file
        else:
            self._name = file
            os_flags = _build_os_flags(flags)
            self._fd = _os.open(file, os_flags, 0o666)
        self.mode = mode
        self.name = self._name

    def fileno(self):
        self._check_closed()
        return self._fd

    def isatty(self):
        self._check_closed()
        try:
            return _os.isatty(self._fd)
        except OSError:
            return False

    def readable(self):
        self._check_closed()
        return self._flags["reading"] or self._flags["updating"]

    def writable(self):
        self._check_closed()
        return (self._flags["writing"] or self._flags["appending"]
                or self._flags["creating"] or self._flags["updating"])

    def seekable(self):
        self._check_closed()
        try:
            _os.lseek(self._fd, 0, 1)
            return True
        except OSError:
            return False

    def read(self, size=-1):
        self._check_closed()
        if not self.readable():
            raise UnsupportedOperation("read")
        if size is None or size < 0:
            chunks = []
            while True:
                chunk = _os.read(self._fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)
        if size == 0:
            return b""
        return _os.read(self._fd, size)

    def readall(self):
        return self.read(-1)

    def readline(self, size=-1):
        self._check_closed()
        if not self.readable():
            raise UnsupportedOperation("read")
        if size is None:
            size = -1
        chunks = []
        total = 0
        while True:
            if size >= 0 and total >= size:
                break
            ch = _os.read(self._fd, 1)
            if not ch:
                break
            chunks.append(ch)
            total += 1
            if ch == b"\n":
                break
        return b"".join(chunks)

    def write(self, data):
        self._check_closed()
        if not self.writable():
            raise UnsupportedOperation("write")
        if isinstance(data, str):
            raise TypeError("a bytes-like object is required, not 'str'")
        if isinstance(data, memoryview):
            data = data.tobytes()
        elif isinstance(data, bytearray):
            data = bytes(data)
        return _os.write(self._fd, data)

    def seek(self, offset, whence=0):
        self._check_closed()
        return _os.lseek(self._fd, offset, whence)

    def tell(self):
        self._check_closed()
        return _os.lseek(self._fd, 0, 1)

    def truncate(self, size=None):
        self._check_closed()
        if size is None:
            size = self.tell()
        _os.ftruncate(self._fd, size)
        return size

    def flush(self):
        self._check_closed()
        # Unbuffered: nothing to flush.

    def close(self):
        if self._closed:
            return
        try:
            if self._closefd:
                _os.close(self._fd)
        finally:
            self._closed = True


class _TextWrapper(IOBase):
    """Wraps a binary stream, performing encode/decode and newline translation."""

    def __init__(self, raw, encoding=None, errors=None, newline=None):
        super().__init__()
        self._raw = raw
        self.encoding = encoding or "utf-8"
        self.errors = errors or "strict"
        if newline not in (None, "", "\n", "\r", "\r\n"):
            raise ValueError("illegal newline value: %r" % (newline,))
        self._newline = newline
        self._read_buffer = ""
        self.mode = getattr(raw, "mode", "")
        self.name = getattr(raw, "name", None)

    def readable(self):
        return self._raw.readable()

    def writable(self):
        return self._raw.writable()

    def seekable(self):
        return self._raw.seekable()

    def fileno(self):
        return self._raw.fileno()

    def isatty(self):
        return self._raw.isatty()

    def _decode_more(self, size=4096):
        chunk = self._raw.read(size)
        if not chunk:
            return ""
        text = chunk.decode(self.encoding, self.errors)
        if self._newline is None:
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text

    def read(self, size=-1):
        self._check_closed()
        if size is None or size < 0:
            parts = [self._read_buffer]
            self._read_buffer = ""
            while True:
                more = self._decode_more(65536)
                if not more:
                    break
                parts.append(more)
            return "".join(parts)
        # Fill buffer up to size.
        while len(self._read_buffer) < size:
            more = self._decode_more(max(size - len(self._read_buffer), 4096))
            if not more:
                break
            self._read_buffer += more
        out = self._read_buffer[:size]
        self._read_buffer = self._read_buffer[size:]
        return out

    def readline(self, size=-1):
        self._check_closed()
        if size is None:
            size = -1
        result = []
        total = 0
        while True:
            if not self._read_buffer:
                more = self._decode_more(4096)
                if not more:
                    break
                self._read_buffer += more
            idx = self._read_buffer.find("\n")
            if idx == -1:
                if size >= 0 and total + len(self._read_buffer) >= size:
                    take = size - total
                    result.append(self._read_buffer[:take])
                    self._read_buffer = self._read_buffer[take:]
                    total += take
                    break
                result.append(self._read_buffer)
                total += len(self._read_buffer)
                self._read_buffer = ""
            else:
                end = idx + 1
                if size >= 0 and total + end > size:
                    take = size - total
                    result.append(self._read_buffer[:take])
                    self._read_buffer = self._read_buffer[take:]
                    total += take
                else:
                    result.append(self._read_buffer[:end])
                    self._read_buffer = self._read_buffer[end:]
                    total += end
                break
        return "".join(result)

    def write(self, s):
        self._check_closed()
        if not isinstance(s, str):
            raise TypeError("write() argument must be str, not %r" %
                            (type(s).__name__,))
        text = s
        if self._newline is None or self._newline == "\n":
            pass
        elif self._newline == "":
            pass
        else:
            text = text.replace("\n", self._newline)
        data = text.encode(self.encoding, self.errors)
        self._raw.write(data)
        return len(s)

    def flush(self):
        self._check_closed()
        self._raw.flush()

    def close(self):
        if self._closed:
            return
        try:
            self.flush()
        except Exception:
            pass
        try:
            self._raw.close()
        finally:
            self._closed = True

    def seek(self, offset, whence=0):
        self._check_closed()
        self._read_buffer = ""
        return self._raw.seek(offset, whence)

    def tell(self):
        self._check_closed()
        return self._raw.tell()


# ---------------------------------------------------------------------------
# open()
# ---------------------------------------------------------------------------

def open(file, mode="r", buffering=-1, encoding=None, errors=None,
         newline=None, closefd=True, opener=None):
    """Clean-room implementation of the builtin/io.open() function."""
    flags = _parse_mode(mode)
    if opener is not None:
        # Use opener to obtain fd.
        fd = opener(file, _build_os_flags(flags))
        raw = _FileStream(fd, mode=mode.replace("t", "").replace("b", "") +
                          ("b" if flags["binary"] else ""), closefd=closefd)
    else:
        raw = _FileStream(
            file,
            mode=mode.replace("t", "").replace("b", "") +
                 ("b" if flags["binary"] else ""),
            closefd=closefd,
        )
    if flags["binary"]:
        if encoding is not None:
            raise ValueError("binary mode doesn't take an encoding argument")
        if errors is not None:
            raise ValueError("binary mode doesn't take an errors argument")
        if newline is not None:
            raise ValueError("binary mode doesn't take a newline argument")
        return raw
    return _TextWrapper(raw, encoding=encoding, errors=errors, newline=newline)


# ---------------------------------------------------------------------------
# Invariant entry points
# ---------------------------------------------------------------------------

def io2_bytesio():
    """Verify that BytesIO behaves correctly across read/write/seek/truncate."""
    try:
        b = BytesIO(b"hello")
        if b.read() != b"hello":
            return False
        b.seek(0)
        if b.read(2) != b"he":
            return False
        if b.tell() != 2:
            return False
        b.seek(0, 2)
        b.write(b" world")
        if b.getvalue() != b"hello world":
            return False
        b.seek(0)
        if b.readline() != b"hello world":
            return False
        b.seek(0)
        b.write(b"HELLO")
        if b.getvalue() != b"HELLO world":
            return False
        b.truncate(5)
        if b.getvalue() != b"HELLO":
            return False
        if not b.readable() or not b.writable() or not b.seekable():
            return False
        b.close()
        if not b.closed:
            return False
        # Newline-aware readline.
        b2 = BytesIO(b"line1\nline2\nline3")
        if b2.readline() != b"line1\n":
            return False
        if b2.readline() != b"line2\n":
            return False
        if b2.readline() != b"line3":
            return False
        if b2.readline() != b"":
            return False
        # Type checking on write
        b3 = BytesIO()
        try:
            b3.write("oops")
        except TypeError:
            pass
        else:
            return False
        return True
    except Exception:
        return False


def io2_stringio():
    """Verify that StringIO behaves correctly across read/write/seek."""
    try:
        s = StringIO("hello")
        if s.read() != "hello":
            return False
        s.seek(0)
        if s.read(2) != "he":
            return False
        s.seek(0, 2)
        s.write(" world")
        if s.getvalue() != "hello world":
            return False
        s.seek(0)
        if s.readline() != "hello world":
            return False
        # Multiline
        s2 = StringIO("a\nb\nc")
        if s2.readline() != "a\n":
            return False
        if s2.readline() != "b\n":
            return False
        if s2.readline() != "c":
            return False
        if s2.readline() != "":
            return False
        # Type checking
        s3 = StringIO()
        try:
            s3.write(b"oops")
        except TypeError:
            pass
        else:
            return False
        # Newline translation default
        s4 = StringIO(newline="")
        s4.write("a\nb")
        if s4.getvalue() != "a\nb":
            return False
        if not s.readable() or not s.writable() or not s.seekable():
            return False
        s.close()
        if not s.closed:
            return False
        return True
    except Exception:
        return False


def io2_open():
    """Verify that open() can round-trip text and binary content via temp files."""
    import tempfile as _tempfile
    path = None
    try:
        # Write & read back binary.
        fd, path = _tempfile.mkstemp(prefix="theseus_io_cr_")
        _os.close(fd)
        with open(path, "wb") as f:
            n = f.write(b"hello world")
            if n != 11:
                return False
        with open(path, "rb") as f:
            if f.read() != b"hello world":
                return False
            if not f.readable():
                return False
            if f.writable():
                return False
        # Append binary.
        with open(path, "ab") as f:
            f.write(b"!")
        with open(path, "rb") as f:
            if f.read() != b"hello world!":
                return False
        # Text round trip with utf-8 by default.
        with open(path, "w", encoding="utf-8") as f:
            f.write("héllo\nwørld")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
            if text != "héllo\nwørld":
                return False
        # Text readline.
        with open(path, "w", encoding="utf-8") as f:
            f.write("a\nb\nc\n")
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines != ["a\n", "b\n", "c\n"]:
                return False
        # Binary mode rejects encoding kwarg.
        try:
            open(path, "rb", encoding="utf-8").close()
        except ValueError:
            pass
        else:
            return False
        # Invalid mode.
        try:
            open(path, "rwx")
        except ValueError:
            pass
        else:
            return False
        return True
    except Exception:
        return False
    finally:
        if path is not None:
            try:
                _os.remove(path)
            except OSError:
                pass


__all__ = [
    "BytesIO",
    "StringIO",
    "IOBase",
    "UnsupportedOperation",
    "open",
    "io2_bytesio",
    "io2_stringio",
    "io2_open",
]