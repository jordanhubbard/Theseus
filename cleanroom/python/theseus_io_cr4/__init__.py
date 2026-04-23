"""
theseus_io_cr4 - Clean-room implementation of in-memory I/O streams.
Do NOT import io or any I/O library.
"""


class IOBase:
    """Base class for all I/O classes."""

    def __init__(self):
        self._closed = False

    def close(self):
        self._closed = True

    @property
    def closed(self):
        return self._closed

    def readable(self):
        return False

    def writable(self):
        return False

    def seekable(self):
        return False

    def flush(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if line == '' or line == b'':
            raise StopIteration
        return line

    def readline(self, size=-1):
        raise NotImplementedError

    def readlines(self, hint=-1):
        lines = []
        total = 0
        for line in self:
            lines.append(line)
            total += len(line)
            if hint != -1 and total >= hint:
                break
        return lines

    def writelines(self, lines):
        for line in lines:
            self.write(line)


class RawIOBase(IOBase):
    """Base class for raw binary I/O."""

    def read(self, size=-1):
        raise NotImplementedError

    def readall(self):
        return self.read(-1)

    def readinto(self, b):
        raise NotImplementedError

    def write(self, b):
        raise NotImplementedError

    def readable(self):
        return True

    def writable(self):
        return True


class BufferedIOBase(IOBase):
    """Base class for buffered binary I/O."""

    def read(self, size=-1):
        raise NotImplementedError

    def read1(self, size=-1):
        raise NotImplementedError

    def readinto(self, b):
        raise NotImplementedError

    def readinto1(self, b):
        raise NotImplementedError

    def write(self, b):
        raise NotImplementedError

    def detach(self):
        raise NotImplementedError

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True


class TextIOBase(IOBase):
    """Base class for text I/O."""

    def read(self, size=-1):
        raise NotImplementedError

    def readline(self, size=-1):
        raise NotImplementedError

    def write(self, s):
        raise NotImplementedError

    def seek(self, pos, whence=0):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True

    @property
    def encoding(self):
        return 'utf-8'

    @property
    def errors(self):
        return 'strict'

    @property
    def newlines(self):
        return None


class StringIO(TextIOBase):
    """
    In-memory text stream supporting read/write/seek/tell/readline.
    Internal buffer is str.
    """

    def __init__(self, initial_value='', newline='\n'):
        super().__init__()
        if not isinstance(initial_value, str):
            raise TypeError("initial_value must be str, not {!r}".format(
                type(initial_value).__name__))
        self._buffer = initial_value
        self._pos = 0
        self._newline = newline

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True

    def read(self, size=-1):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if size is None or size < 0:
            result = self._buffer[self._pos:]
            self._pos = len(self._buffer)
        else:
            result = self._buffer[self._pos:self._pos + size]
            self._pos += len(result)
        return result

    def readline(self, size=-1):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if self._pos >= len(self._buffer):
            return ''
        
        start = self._pos
        buf = self._buffer
        end = len(buf)
        
        # Find next newline
        newline_pos = buf.find('\n', start)
        
        if newline_pos == -1:
            # No newline found, read to end
            if size is None or size < 0:
                result = buf[start:]
                self._pos = end
            else:
                result = buf[start:start + size]
                self._pos = start + len(result)
        else:
            # Include the newline character
            line_end = newline_pos + 1
            if size is None or size < 0:
                result = buf[start:line_end]
                self._pos = line_end
            else:
                result = buf[start:min(start + size, line_end)]
                self._pos = start + len(result)
        
        return result

    def write(self, s):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if not isinstance(s, str):
            raise TypeError("string argument expected, got {!r}".format(
                type(s).__name__))
        if not s:
            return 0
        # Insert/overwrite at current position
        buf = self._buffer
        pos = self._pos
        self._buffer = buf[:pos] + s + buf[pos + len(s):]
        self._pos = pos + len(s)
        return len(s)

    def seek(self, pos, whence=0):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if whence == 0:
            if pos < 0:
                raise ValueError("negative seek position {}".format(pos))
            self._pos = pos
        elif whence == 1:
            self._pos = max(0, self._pos + pos)
        elif whence == 2:
            self._pos = max(0, len(self._buffer) + pos)
        else:
            raise ValueError("invalid whence ({}, should be 0, 1 or 2)".format(whence))
        return self._pos

    def tell(self):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        return self._pos

    def getvalue(self):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        return self._buffer

    def truncate(self, pos=None):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if pos is None:
            pos = self._pos
        if pos < 0:
            raise ValueError("negative truncate position {}".format(pos))
        self._buffer = self._buffer[:pos]
        return pos

    def __repr__(self):
        return '<theseus_io_cr4.StringIO object>'


class BytesIO(BufferedIOBase):
    """
    In-memory binary stream supporting read/write/seek/tell/getvalue.
    Internal buffer is bytes.
    """

    def __init__(self, initial_bytes=b''):
        super().__init__()
        if not isinstance(initial_bytes, (bytes, bytearray)):
            raise TypeError("a bytes-like object is required, not {!r}".format(
                type(initial_bytes).__name__))
        self._buffer = bytearray(initial_bytes)
        self._pos = 0

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True

    def read(self, size=-1):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if size is None or size < 0:
            result = bytes(self._buffer[self._pos:])
            self._pos = len(self._buffer)
        else:
            result = bytes(self._buffer[self._pos:self._pos + size])
            self._pos += len(result)
        return result

    def read1(self, size=-1):
        return self.read(size)

    def readline(self, size=-1):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if self._pos >= len(self._buffer):
            return b''
        
        start = self._pos
        buf = self._buffer
        end = len(buf)
        
        # Find next newline byte (0x0a)
        newline_pos = -1
        for i in range(start, end):
            if buf[i] == 0x0a:
                newline_pos = i
                break
        
        if newline_pos == -1:
            if size is None or size < 0:
                result = bytes(buf[start:])
                self._pos = end
            else:
                result = bytes(buf[start:start + size])
                self._pos = start + len(result)
        else:
            line_end = newline_pos + 1
            if size is None or size < 0:
                result = bytes(buf[start:line_end])
                self._pos = line_end
            else:
                result = bytes(buf[start:min(start + size, line_end)])
                self._pos = start + len(result)
        
        return result

    def readinto(self, b):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def readinto1(self, b):
        return self.readinto(b)

    def write(self, b):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if not isinstance(b, (bytes, bytearray, memoryview)):
            raise TypeError("a bytes-like object is required, not {!r}".format(
                type(b).__name__))
        b = bytes(b)
        if not b:
            return 0
        pos = self._pos
        buf_len = len(self._buffer)
        # Extend buffer if necessary
        if pos > buf_len:
            self._buffer.extend(b'\x00' * (pos - buf_len))
        # Overwrite or append
        end = pos + len(b)
        if end <= len(self._buffer):
            self._buffer[pos:end] = b
        else:
            self._buffer[pos:] = b[:len(self._buffer) - pos]
            self._buffer.extend(b[len(self._buffer) - pos:])
        self._pos = end
        return len(b)

    def seek(self, pos, whence=0):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if whence == 0:
            if pos < 0:
                raise ValueError("negative seek position {}".format(pos))
            self._pos = pos
        elif whence == 1:
            self._pos = max(0, self._pos + pos)
        elif whence == 2:
            self._pos = max(0, len(self._buffer) + pos)
        else:
            raise ValueError("invalid whence ({}, should be 0, 1 or 2)".format(whence))
        return self._pos

    def tell(self):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        return self._pos

    def getvalue(self):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        return bytes(self._buffer)

    def truncate(self, pos=None):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if pos is None:
            pos = self._pos
        if pos < 0:
            raise ValueError("negative truncate position {}".format(pos))
        del self._buffer[pos:]
        return pos

    def getbuffer(self):
        return memoryview(self._buffer)

    def __repr__(self):
        return '<theseus_io_cr4.BytesIO object>'


class TextIOWrapper(TextIOBase):
    """
    A buffered text stream over a BufferedIOBase binary stream.
    Wraps a binary stream and provides text encoding/decoding.
    """

    def __init__(self, buffer, encoding='utf-8', errors='strict', newline='\n',
                 line_buffering=False, write_through=False):
        super().__init__()
        self._buffer = buffer
        self._encoding = encoding
        self._errors = errors
        self._newline = newline
        self._line_buffering = line_buffering
        self._write_through = write_through
        self._text_buffer = ''
        self._text_pos = 0

    @property
    def encoding(self):
        return self._encoding

    @property
    def errors(self):
        return self._errors

    @property
    def buffer(self):
        return self._buffer

    def readable(self):
        return self._buffer.readable()

    def writable(self):
        return self._buffer.writable()

    def seekable(self):
        return self._buffer.seekable()

    def flush(self):
        self._buffer.flush()

    def close(self):
        if not self._closed:
            self.flush()
            self._buffer.close()
            super().close()

    def write(self, s):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if not isinstance(s, str):
            raise TypeError("write() argument must be str, not {!r}".format(
                type(s).__name__))
        encoded = s.encode(self._encoding, self._errors)
        self._buffer.write(encoded)
        return len(s)

    def read(self, size=-1):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if size is None or size < 0:
            data = self._buffer.read()
        else:
            data = self._buffer.read(size)
        return data.decode(self._encoding, self._errors)

    def readline(self, size=-1):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        # Read binary line and decode
        data = self._buffer.readline(size)
        return data.decode(self._encoding, self._errors)

    def seek(self, pos, whence=0):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        return self._buffer.seek(pos, whence)

    def tell(self):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        return self._buffer.tell()

    def __repr__(self):
        return '<theseus_io_cr4.TextIOWrapper encoding={!r}>'.format(self._encoding)


# ---------------------------------------------------------------------------
# Invariant functions (zero-arg, return hardcoded / computed results)
# ---------------------------------------------------------------------------

def io4_stringio_readline():
    """
    s = StringIO('a\\nb\\n'); s.readline() == 'a\\n'
    Returns 'a\\n'
    """
    s = StringIO('a\nb\n')
    return s.readline()


def io4_bytesio_getvalue():
    """
    b = BytesIO(); b.write(b'hi'); b.getvalue() == b'hi'
    Returns True
    """
    b = BytesIO()
    b.write(b'hi')
    return b.getvalue() == b'hi'


def io4_stringio_seek():
    """
    s = StringIO('hello'); s.read(); s.seek(0); s.read() == 'hello'
    Returns 'hello'
    """
    s = StringIO('hello')
    s.read()
    s.seek(0)
    return s.read()


__all__ = [
    'StringIO',
    'BytesIO',
    'TextIOWrapper',
    'IOBase',
    'RawIOBase',
    'BufferedIOBase',
    'TextIOBase',
    'io4_stringio_readline',
    'io4_bytesio_getvalue',
    'io4_stringio_seek',
]