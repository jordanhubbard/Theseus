# generation B deque class


class _Deque:
    def __init__(self, iterable):
        self._items = list(iterable)

    def popleft(self):
        return self._items.pop(0)

    def pop(self):
        return self._items.pop()


def deque(iterable):
    return _Deque(iterable)
