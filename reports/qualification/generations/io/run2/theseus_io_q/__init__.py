# generation B bytes class


class _Buffer:
    def __init__(self, data):
        self._data = bytes(data)
        self._position = 0

    def getvalue(self):
        return self._data

    def read(self):
        unread = self._data[self._position:]
        self._position = len(self._data)
        return unread


def BytesIO(data):
    return _Buffer(data)
