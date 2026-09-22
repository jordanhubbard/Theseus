# generation B heap class

"""Small clean-room implementation of the documented ``heapq`` surface."""


class _Heap:
    def __init__(self, values):
        self.values = values

    def _rise(self, index):
        values = self.values
        item = values[index]
        while index:
            parent = (index - 1) // 2
            parent_item = values[parent]
            if not item < parent_item:
                break
            values[index] = parent_item
            index = parent
        values[index] = item

    def _sink(self, index):
        values = self.values
        end = len(values)
        item = values[index]
        child = index * 2 + 1
        while child < end:
            right = child + 1
            if right < end and values[right] < values[child]:
                child = right
            if not values[child] < item:
                break
            values[index] = values[child]
            index = child
            child = index * 2 + 1
        values[index] = item

    def heapify(self):
        for index in range(len(self.values) // 2 - 1, -1, -1):
            self._sink(index)

    def push(self, item):
        self.values.append(item)
        self._rise(len(self.values) - 1)

    def pop(self):
        values = self.values
        if not values:
            raise IndexError("index out of range")
        last = values.pop()
        if not values:
            return last
        smallest = values[0]
        values[0] = last
        self._sink(0)
        return smallest

    @staticmethod
    def nsmallest(n, iterable, key=None):
        if n <= 0:
            return []
        return sorted(iterable, key=key)[:n]

    @staticmethod
    def nlargest(n, iterable, key=None):
        if n <= 0:
            return []
        return sorted(iterable, key=key, reverse=True)[:n]


def heapify(heap):
    _Heap(heap).heapify()


def heappush(heap, item):
    _Heap(heap).push(item)


def heappop(heap):
    return _Heap(heap).pop()


def nsmallest(n, iterable, key=None):
    return _Heap.nsmallest(n, iterable, key=key)


def nlargest(n, iterable, key=None):
    return _Heap.nlargest(n, iterable, key=key)


__all__ = ["nlargest", "nsmallest", "heapify", "heappush", "heappop"]
