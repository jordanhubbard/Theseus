"""
theseus_io_cr2 - Clean-room implementation of in-memory I/O streams.
No import of the `io` module or any third-party libraries.
"""


class StringIO:
    """In-memory text stream supporting read/write/seek/tell/getvalue/readline."""

    def __init__(self, initial_value=""):
        self._buffer = list(initial_value)
        self._pos = len(self._buffer)

    def write(self, s):
        if not isinstance(s, str):
            raise TypeError("write() argument must be str, not bytes")
        chars = list(s)
        # Overwrite/extend from current position
        for i, ch in enumerate(chars):
            idx = self._pos + i
            if idx < len(self._buffer):
                self._buffer[idx] = ch
            else:
                # Extend with spaces if there's a gap
                while len(self._buffer) < idx:
                    self._buffer.append(' ')
                self._buffer.append(ch)
        self._pos += len(chars)
        return len(chars)

    def read(self, size=-1):
        if size is None or size < 0:
            result = "".join(self._buffer[self._pos:])
            self._pos = len(self._buffer)
        else:
            result = "".join(self._buffer[self._pos:self._pos + size])
            self._pos += len(result)
        return result

    def readline(self, size=-1):
        start = self._pos
        end = len(self._buffer)
        if size is not None and size >= 0:
            end = min(end, self._pos + size)
        result_chars = []
        i = self._pos
        while i < end:
            ch = self._buffer[i]
            result_chars.append(ch)
            i += 1
            if ch == '\n':
                break
        self._pos = i
        return "".join(result_chars)

    def readlines(self):
        lines = []
        while self._pos < len(self._buffer):
            lines.append(self.readline())
        return lines

    def seek(self, pos, whence=0):
        if whence == 0:
            self._pos = max(0, pos)
        elif whence == 1:
            self._pos = max(0, self._pos + pos)
        elif whence == 2:
            self._pos = max(0, len(self._buffer) + pos)
        else:
            raise ValueError("invalid whence value")
        return self._pos

    def tell(self):
        return self._pos

    def getvalue(self):
        return "".join(self._buffer)

    def truncate(self, size=None):
        if size is None:
            size = self._pos
        if size < len(self._buffer):
            self._buffer = self._buffer[:size]
        elif size > len(self._buffer):
            self._buffer.extend([' '] * (size - len(self._buffer)))
        return size

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class BytesIO:
    """In-memory binary stream supporting read/write/seek/tell/getvalue."""

    def __init__(self, initial_bytes=b""):
        if not isinstance(initial_bytes, (bytes, bytearray)):
            raise TypeError("initial_bytes must be bytes or bytearray")
        self._buffer = bytearray(initial_bytes)
        self._pos = len(self._buffer)

    def write(self, b):
        if not isinstance(b, (bytes, bytearray, memoryview)):
            raise TypeError("write() argument must be bytes-like object")
        data = bytes(b)
        end = self._pos + len(data)
        # Extend buffer if necessary
        if end > len(self._buffer):
            self._buffer.extend(b'\x00' * (end - len(self._buffer)))
        # Write data into buffer
        self._buffer[self._pos:end] = data
        self._pos = end
        return len(data)

    def read(self, size=-1):
        if size is None or size < 0:
            result = bytes(self._buffer[self._pos:])
            self._pos = len(self._buffer)
        else:
            result = bytes(self._buffer[self._pos:self._pos + size])
            self._pos += len(result)
        return result

    def readline(self, size=-1):
        end = len(self._buffer)
        if size is not None and size >= 0:
            end = min(end, self._pos + size)
        newline_pos = -1
        for i in range(self._pos, end):
            if self._buffer[i] == ord('\n'):
                newline_pos = i
                break
        if newline_pos >= 0:
            result = bytes(self._buffer[self._pos:newline_pos + 1])
            self._pos = newline_pos + 1
        else:
            result = bytes(self._buffer[self._pos:end])
            self._pos = end
        return result

    def readlines(self):
        lines = []
        while self._pos < len(self._buffer):
            lines.append(self.readline())
        return lines

    def seek(self, pos, whence=0):
        if whence == 0:
            self._pos = max(0, pos)
        elif whence == 1:
            self._pos = max(0, self._pos + pos)
        elif whence == 2:
            self._pos = max(0, len(self._buffer) + pos)
        else:
            raise ValueError("invalid whence value")
        return self._pos

    def tell(self):
        return self._pos

    def getvalue(self):
        return bytes(self._buffer)

    def truncate(self, size=None):
        if size is None:
            size = self._pos
        if size < len(self._buffer):
            del self._buffer[size:]
        elif size > len(self._buffer):
            self._buffer.extend(b'\x00' * (size - len(self._buffer)))
        return size

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class BufferedReader:
    """Wrap a raw stream and provide buffered reading."""

    def __init__(self, raw, buffer_size=8192):
        self._raw = raw
        self._buffer_size = buffer_size
        self._buffer = b""
        self._buf_pos = 0

    def _fill_buffer(self):
        data = self._raw.read(self._buffer_size)
        if data:
            self._buffer = self._buffer[self._buf_pos:] + data
            self._buf_pos = 0

    def read(self, size=-1):
        if size < 0:
            # Read all remaining
            leftover = self._buffer[self._buf_pos:]
            rest = self._raw.read()
            self._buffer = b""
            self._buf_pos = 0
            return leftover + rest
        result = b""
        while len(result) < size:
            available = self._buffer[self._buf_pos:]
            needed = size - len(result)
            if len(available) >= needed:
                result += available[:needed]
                self._buf_pos += needed
                break
            else:
                result += available
                self._buf_pos = 0
                self._buffer = b""
                chunk = self._raw.read(self._buffer_size)
                if not chunk:
                    break
                self._buffer = chunk
        return result

    def readline(self, size=-1):
        result = b""
        while True:
            available = self._buffer[self._buf_pos:]
            newline = available.find(b'\n')
            if newline >= 0:
                result += available[:newline + 1]
                self._buf_pos += newline + 1
                break
            else:
                result += available
                self._buf_pos = 0
                self._buffer = b""
                chunk = self._raw.read(self._buffer_size)
                if not chunk:
                    break
                self._buffer = chunk
        return result

    def seek(self, pos, whence=0):
        self._buffer = b""
        self._buf_pos = 0
        return self._raw.seek(pos, whence)

    def tell(self):
        raw_pos = self._raw.tell()
        # Adjust for buffered but unread data
        buffered_ahead = len(self._buffer) - self._buf_pos
        return raw_pos - buffered_ahead

    def close(self):
        self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ── Invariant functions ──────────────────────────────────────────────────────

def io_cr2_stringio_seek():
    """write 'hello'; seek(0); read() == 'hello'"""
    s = StringIO()
    s.write('hello')
    s.seek(0)
    return s.read()


def io_cr2_bytesio_tell():
    """write b'abc'; tell() == 3"""
    b = BytesIO()
    b.write(b'abc')
    return b.tell()


def io_cr2_stringio_readline():
    """write 'a\\nb'; seek(0); readline() == 'a\\n'"""
    s = StringIO()
    s.write('a\nb')
    s.seek(0)
    return s.readline()


__all__ = [
    "StringIO",
    "BytesIO",
    "BufferedReader",
    "io_cr2_stringio_seek",
    "io_cr2_bytesio_tell",
    "io_cr2_stringio_readline",
]