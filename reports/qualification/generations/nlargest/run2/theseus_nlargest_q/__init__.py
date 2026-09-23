# generation B heap class


class _Heap:
    def __init__(self, limit):
        self.limit = limit
        self.values = []

    def _sift_up(self, index):
        values = self.values
        while index:
            parent = (index - 1) // 2
            if not values[index] < values[parent]:
                break
            values[index], values[parent] = values[parent], values[index]
            index = parent

    def _sift_down(self, index):
        values = self.values
        size = len(values)
        while True:
            left = index * 2 + 1
            if left >= size:
                return
            right = left + 1
            child = left
            if right < size and values[right] < values[left]:
                child = right
            if not values[child] < values[index]:
                return
            values[index], values[child] = values[child], values[index]
            index = child

    def add(self, value):
        if len(self.values) < self.limit:
            self.values.append(value)
            self._sift_up(len(self.values) - 1)
        elif self.values[0] < value:
            self.values[0] = value
            self._sift_down(0)

    def largest(self):
        return sorted(self.values, reverse=True)

    def select(self, iterable):
        if self.limit <= 0:
            return []
        for value in iterable:
            self.add(value)
        return self.largest()


def nlargest(n, iterable):
    return _Heap(n).select(iterable)
