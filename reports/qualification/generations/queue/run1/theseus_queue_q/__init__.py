# generation A queue functions

class ItemBuffer(object):
    def __init__(self):
        self._items = []


def buffer_empty(buf):
    return len(buf._items) == 0


def buffer_qsize(buf):
    return len(buf._items)


def buffer_put(buf, item):
    buf._items.append(item)


def buffer_get(buf):
    if buffer_empty(buf):
        raise Empty("get from empty queue")
    return buf._items.pop(0)


class Empty(Exception):
    pass


class Queue(object):
    def __init__(self):
        self._buf = ItemBuffer()

    def empty(self):
        return buffer_empty(self._buf)

    def qsize(self):
        return buffer_qsize(self._buf)

    def put(self, item, block=True, timeout=None):
        buffer_put(self._buf, item)

    def get(self, block=True, timeout=None):
        if block is False and buffer_empty(self._buf):
            raise Empty("get from empty queue")
        return buffer_get(self._buf)
