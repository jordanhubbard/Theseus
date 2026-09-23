# generation A deque scan

class DequeScan(object):
    def __init__(self, iterable=()):
        self._items = list(iterable)

    def popleft(self):
        if not self._items:
            raise IndexError('pop from an empty deque')
        return self._items.pop(0)

    def pop(self):
        if not self._items:
            raise IndexError('pop from an empty deque')
        return self._items.pop()


def deque(iterable=()):
    return DequeScan(iterable)
