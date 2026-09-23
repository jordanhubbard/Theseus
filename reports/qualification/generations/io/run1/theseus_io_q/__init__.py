# generation A bytes buffer

class _BytesStore(object):
    __slots__ = ("_data",)

    def __init__(self, data):
        self._data = bytes(data)


class BytesIO(object):
    def __init__(self, initial_bytes=b""):
        if initial_bytes is None:
            initial_bytes = b""
        self._store = _BytesStore(initial_bytes)
        self._pos = 0

    def getvalue(self):
        return self._store._data

    def read(self, size=-1):
        data = self._store._data
        if size is None or size < 0:
            chunk = data[self._pos :]
            self._pos = len(data)
            return chunk
        end = self._pos + size
        chunk = data[self._pos : end]
        self._pos += len(chunk)
        return chunk
