"""
theseus_io_cr3 - Clean-room extended I/O utilities.
Do NOT import io or any third-party library.
"""

DEFAULT_BUFFER_SIZE = 8192


class RawIOBase:
    """Base class for raw I/O (binary, unbuffered)."""

    def read(self, size=-1):
        raise NotImplementedError

    def readinto(self, b):
        raise NotImplementedError

    def write(self, b):
        raise NotImplementedError

    def close(self):
        self._closed = True

    @property
    def closed(self):
        return getattr(self, '_closed', False)

    def readable(self):
        return False

    def writable(self):
        return False

    def seekable(self):
        return False

    def seek(self, pos, whence=0):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def flush(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class BufferedIOBase:
    """Base class for buffered I/O."""

    def read(self, size=-1):
        raise NotImplementedError

    def read1(self, size=-1):
        raise NotImplementedError

    def readinto(self, b):
        raise NotImplementedError

    def write(self, b):
        raise NotImplementedError

    def close(self):
        self._closed = True

    @property
    def closed(self):
        return getattr(self, '_closed', False)

    def readable(self):
        return False

    def writable(self):
        return False

    def seekable(self):
        return False

    def seek(self, pos, whence=0):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def flush(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TextIOBase:
    """Base class for text I/O."""

    def read(self, size=-1):
        raise NotImplementedError

    def readline(self, size=-1):
        raise NotImplementedError

    def write(self, s):
        raise NotImplementedError

    def close(self):
        self._closed = True

    @property
    def closed(self):
        return getattr(self, '_closed', False)

    def readable(self):
        return False

    def writable(self):
        return False

    def seekable(self):
        return False

    def seek(self, pos, whence=0):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def flush(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class IncrementalNewlineDecoder:
    """Translates newlines on read."""

    def __init__(self, decoder, translate, errors='strict'):
        self._decoder = decoder
        self._translate = translate
        self._errors = errors
        self._seennl = 0

    def decode(self, input, final=False):
        if self._decoder is not None:
            output = self._decoder.decode(input, final=final)
        else:
            output = input

        if self._translate:
            # Replace \r\n and \r with \n
            output = output.replace('\r\n', '\n')
            output = output.replace('\r', '\n')

        return output

    def getstate(self):
        if self._decoder is not None:
            buf, flag = self._decoder.getstate()
        else:
            buf, flag = b'', 0
        return buf, flag

    def setstate(self, state):
        buf, flag = state
        if self._decoder is not None:
            self._decoder.setstate((buf, flag))

    def reset(self):
        if self._decoder is not None:
            self._decoder.reset()

    @property
    def newlines(self):
        return None


class StringIO(TextIOBase):
    """In-memory text stream using a string buffer."""

    def __init__(self, initial_value='', newline='\n'):
        self._buffer = initial_value
        self._pos = 0
        self._newline = newline
        self._closed = False

    def _check_closed(self):
        if self._closed:
            raise ValueError("I/O operation on closed file.")

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True

    def read(self, size=-1):
        self._check_closed()
        if size is None or size < 0:
            result = self._buffer[self._pos:]
            self._pos = len(self._buffer)
        else:
            result = self._buffer[self._pos:self._pos + size]
            self._pos += len(result)
        return result

    def readline(self, size=-1):
        self._check_closed()
        start = self._pos
        buf = self._buffer
        length = len(buf)

        if self._pos >= length:
            return ''

        end = length
        newline_pos = buf.find('\n', start)
        if newline_pos != -1:
            end = newline_pos + 1

        if size is not None and size >= 0:
            end = min(end, start + size)

        result = buf[start:end]
        self._pos = start + len(result)
        return result

    def readlines(self, hint=-1):
        self._check_closed()
        lines = []
        total = 0
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
            total += len(line)
            if hint is not None and hint >= 0 and total >= hint:
                break
        return lines

    def write(self, s):
        self._check_closed()
        if not isinstance(s, str):
            raise TypeError("string argument expected, got '%s'" % type(s).__name__)
        if self._newline is not None and self._newline != '\n':
            s = s.replace('\n', self._newline)
        length = len(s)
        if self._pos == len(self._buffer):
            self._buffer += s
        else:
            buf = list(self._buffer)
            # Extend if needed
            while len(buf) < self._pos + length:
                buf.append('\x00')
            for i, ch in enumerate(s):
                buf[self._pos + i] = ch
            self._buffer = ''.join(buf)
        self._pos += length
        return length

    def getvalue(self):
        self._check_closed()
        return self._buffer

    def seek(self, pos, whence=0):
        self._check_closed()
        if whence == 0:
            if pos < 0:
                raise ValueError("negative seek position %r" % pos)
            self._pos = pos
        elif whence == 1:
            self._pos = max(0, self._pos + pos)
        elif whence == 2:
            self._pos = max(0, len(self._buffer) + pos)
        else:
            raise ValueError("invalid whence value")
        return self._pos

    def tell(self):
        self._check_closed()
        return self._pos

    def truncate(self, pos=None):
        self._check_closed()
        if pos is None:
            pos = self._pos
        if pos < 0:
            raise ValueError("negative truncate position %r" % pos)
        self._buffer = self._buffer[:pos]
        return pos

    def close(self):
        self._closed = True

    def __iter__(self):
        self._check_closed()
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line


class BytesIO(BufferedIOBase):
    """In-memory binary stream using a bytearray."""

    def __init__(self, initial_bytes=b''):
        if isinstance(initial_bytes, (bytes, bytearray, memoryview)):
            self._buffer = bytearray(initial_bytes)
        else:
            raise TypeError("a bytes-like object is required, not '%s'" % type(initial_bytes).__name__)
        self._pos = 0
        self._closed = False

    def _check_closed(self):
        if self._closed:
            raise ValueError("I/O operation on closed file.")

    def readable(self):
        return True

    def writable(self):
        return True

    def seekable(self):
        return True

    def read(self, size=-1):
        self._check_closed()
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
        self._check_closed()
        start = self._pos
        buf = self._buffer
        length = len(buf)

        if self._pos >= length:
            return b''

        end = length
        newline_pos = buf.find(b'\n', start)
        if newline_pos != -1:
            end = newline_pos + 1

        if size is not None and size >= 0:
            end = min(end, start + size)

        result = bytes(buf[start:end])
        self._pos = start + len(result)
        return result

    def readlines(self, hint=-1):
        self._check_closed()
        lines = []
        total = 0
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
            total += len(line)
            if hint is not None and hint >= 0 and total >= hint:
                break
        return lines

    def readinto(self, b):
        self._check_closed()
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def write(self, b):
        self._check_closed()
        if isinstance(b, memoryview):
            b = bytes(b)
        if not isinstance(b, (bytes, bytearray)):
            raise TypeError("a bytes-like object is required, not '%s'" % type(b).__name__)
        length = len(b)
        # Extend buffer if needed
        if self._pos + length > len(self._buffer):
            self._buffer.extend(b'\x00' * (self._pos + length - len(self._buffer)))
        self._buffer[self._pos:self._pos + length] = b
        self._pos += length
        return length

    def getvalue(self):
        self._check_closed()
        return bytes(self._buffer)

    def getbuffer(self):
        self._check_closed()
        return memoryview(self._buffer)

    def seek(self, pos, whence=0):
        self._check_closed()
        if whence == 0:
            if pos < 0:
                raise ValueError("negative seek position %r" % pos)
            self._pos = pos
        elif whence == 1:
            self._pos = max(0, self._pos + pos)
        elif whence == 2:
            self._pos = max(0, len(self._buffer) + pos)
        else:
            raise ValueError("invalid whence value")
        return self._pos

    def tell(self):
        self._check_closed()
        return self._pos

    def truncate(self, pos=None):
        self._check_closed()
        if pos is None:
            pos = self._pos
        if pos < 0:
            raise ValueError("negative truncate position %r" % pos)
        del self._buffer[pos:]
        return pos

    def close(self):
        self._closed = True

    def __iter__(self):
        self._check_closed()
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line


# --- Invariant test functions ---

def io3_default_buffer_size():
    """Returns DEFAULT_BUFFER_SIZE (should be 8192)."""
    return DEFAULT_BUFFER_SIZE


def io3_stringio_getvalue():
    """Creates a StringIO, writes 'hello', returns getvalue()."""
    s = StringIO()
    s.write('hello')
    return s.getvalue()


def io3_bytesio_read():
    """Creates a BytesIO with b'abc', reads 2 bytes, returns True if result == b'ab'."""
    b = BytesIO(b'abc')
    return b.read(2) == b'ab'


__all__ = [
    'DEFAULT_BUFFER_SIZE',
    'RawIOBase',
    'BufferedIOBase',
    'TextIOBase',
    'IncrementalNewlineDecoder',
    'StringIO',
    'BytesIO',
    'io3_default_buffer_size',
    'io3_stringio_getvalue',
    'io3_bytesio_read',
]