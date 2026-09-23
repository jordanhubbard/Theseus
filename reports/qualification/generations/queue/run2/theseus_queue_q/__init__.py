# generation B queue class


class _Queue:
    def __init__(self):
        self._items = []

    def put(self, item, block=True, timeout=None):
        self._items.append(item)

    def qsize(self):
        return len(self._items)

    def empty(self):
        return not self._items


Queue = _Queue
