"""Clean-room subset of io for Theseus invariants."""

import builtins

DEFAULT_BUFFER_SIZE = 8192


class UnsupportedOperation(OSError):
    pass


class IOBase:
    pass


class RawIOBase(IOBase):
    pass


class BufferedIOBase(IOBase):
    pass


class TextIOBase(IOBase):
    pass


class BytesIO(BufferedIOBase):
    def __init__(self, initial_bytes=b""):
        self._data = bytearray(initial_bytes)
        self._pos = 0

    def write(self, data):
        data = bytes(data)
        end = self._pos + len(data)
        if end > len(self._data):
            self._data.extend(b"\x00" * (end - len(self._data)))
        self._data[self._pos:end] = data
        self._pos = end
        return len(data)

    def seek(self, pos, whence=0):
        if whence == 1:
            pos = self._pos + pos
        elif whence == 2:
            pos = len(self._data) + pos
        self._pos = max(0, pos)
        return self._pos

    def read(self, size=-1):
        end = len(self._data) if size is None or size < 0 else self._pos + size
        data = bytes(self._data[self._pos:end])
        self._pos += len(data)
        return data


class StringIO(TextIOBase):
    def __init__(self, initial_value=""):
        self._data = str(initial_value)
        self._pos = 0

    def write(self, data):
        data = str(data)
        self._data = self._data[:self._pos] + data + self._data[self._pos + len(data):]
        self._pos += len(data)
        return len(data)

    def seek(self, pos, whence=0):
        if whence == 1:
            pos = self._pos + pos
        elif whence == 2:
            pos = len(self._data) + pos
        self._pos = max(0, pos)
        return self._pos

    def read(self, size=-1):
        end = len(self._data) if size is None or size < 0 else self._pos + size
        data = self._data[self._pos:end]
        self._pos += len(data)
        return data


FileIO = builtins.open
BufferedReader = object
BufferedWriter = object
BufferedRandom = object
BufferedRWPair = object
IncrementalNewlineDecoder = object
TextIOWrapper = object


def open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    return builtins.open(file, mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline, closefd=closefd, opener=opener)


def open_code(path):
    return open(path, "rb")


def io2_bytesio():
    buf = BytesIO()
    buf.write(b"hello")
    buf.write(b" world")
    buf.seek(0)
    return buf.read() == b"hello world"


def io2_stringio():
    buf = StringIO()
    buf.write("hello")
    buf.write(" world")
    buf.seek(0)
    return buf.read() == "hello world"


def io2_open():
    import os as _os
    fname = _os.path.join(_os.environ.get("TMPDIR", "/tmp"), "theseus_io_test.bin")
    with builtins.open(fname, "wb") as f:
        f.write(b"test content")
    try:
        with open(fname, "rb") as f:
            return f.read() == b"test content"
    finally:
        try:
            _os.unlink(fname)
        except OSError:
            pass


__all__ = [
    "DEFAULT_BUFFER_SIZE", "IOBase", "RawIOBase", "BufferedIOBase", "TextIOBase",
    "FileIO", "BytesIO", "StringIO", "BufferedReader", "BufferedWriter",
    "BufferedRandom", "BufferedRWPair", "IncrementalNewlineDecoder",
    "TextIOWrapper", "UnsupportedOperation", "open", "open_code",
    "io2_bytesio", "io2_stringio", "io2_open",
]
