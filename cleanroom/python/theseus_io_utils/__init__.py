class StringIO:
    def __init__(self, initial_value=''):
        self._buffer = initial_value
        self._pos = 0

    def write(self, s):
        if not isinstance(s, str):
            raise TypeError("string argument expected")
        before = self._buffer[:self._pos]
        after = self._buffer[self._pos + len(s):]
        self._buffer = before + s + after
        self._pos += len(s)
        return len(s)

    def read(self, size=-1):
        if size is None or size < 0:
            result = self._buffer[self._pos:]
            self._pos = len(self._buffer)
        else:
            result = self._buffer[self._pos:self._pos + size]
            self._pos += len(result)
        return result

    def seek(self, pos, whence=0):
        if whence == 0:
            self._pos = pos
        elif whence == 1:
            self._pos += pos
        elif whence == 2:
            self._pos = len(self._buffer) + pos
        if self._pos < 0:
            self._pos = 0
        return self._pos

    def tell(self):
        return self._pos

    def getvalue(self):
        return self._buffer

    def truncate(self, size=None):
        if size is None:
            size = self._pos
        self._buffer = self._buffer[:size]
        return size

    def readline(self, size=-1):
        end = self._buffer.find('\n', self._pos)
        if end == -1:
            end = len(self._buffer)
        else:
            end += 1
        if size is not None and size >= 0:
            end = min(end, self._pos + size)
        result = self._buffer[self._pos:end]
        self._pos = end
        return result

    def readlines(self):
        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def close(self):
        pass

    @property
    def closed(self):
        return False


class BytesIO:
    def __init__(self, initial_bytes=b''):
        if isinstance(initial_bytes, (bytes, bytearray)):
            self._buffer = bytearray(initial_bytes)
        else:
            raise TypeError("bytes-like object expected")
        self._pos = 0

    def write(self, b):
        if not isinstance(b, (bytes, bytearray, memoryview)):
            raise TypeError("bytes-like object expected")
        b = bytes(b)
        end = self._pos + len(b)
        if end > len(self._buffer):
            self._buffer.extend(b'\x00' * (end - len(self._buffer)))
        self._buffer[self._pos:end] = b
        self._pos = end
        return len(b)

    def read(self, size=-1):
        if size is None or size < 0:
            result = bytes(self._buffer[self._pos:])
            self._pos = len(self._buffer)
        else:
            result = bytes(self._buffer[self._pos:self._pos + size])
            self._pos += len(result)
        return result

    def seek(self, pos, whence=0):
        if whence == 0:
            self._pos = pos
        elif whence == 1:
            self._pos += pos
        elif whence == 2:
            self._pos = len(self._buffer) + pos
        if self._pos < 0:
            self._pos = 0
        return self._pos

    def tell(self):
        return self._pos

    def getvalue(self):
        return bytes(self._buffer)

    def truncate(self, size=None):
        if size is None:
            size = self._pos
        del self._buffer[size:]
        return size

    def readline(self, size=-1):
        end = self._buffer.find(b'\n', self._pos)
        if end == -1:
            end = len(self._buffer)
        else:
            end += 1
        if size is not None and size >= 0:
            end = min(end, self._pos + size)
        result = bytes(self._buffer[self._pos:end])
        self._pos = end
        return result

    def readlines(self):
        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def close(self):
        pass

    @property
    def closed(self):
        return False


def io_stringio_write_read():
    s = StringIO()
    s.write('hello')
    s.seek(0)
    return s.read()


def io_bytesio_write_read():
    b = BytesIO()
    b.write(b'hello')
    b.seek(0)
    return b.read() == b'hello'


def io_stringio_seek_read():
    s = StringIO()
    s.write('hello world')
    s.seek(6)
    return s.read()