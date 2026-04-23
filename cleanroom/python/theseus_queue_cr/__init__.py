# theseus_queue_cr: Clean-room queue implementation
# No imports of queue, threading, or collections allowed.


class Queue:
    """FIFO queue implementation."""

    def __init__(self, maxsize=0):
        self._maxsize = maxsize
        self._data = []

    def put(self, item):
        self._data.append(item)

    def get(self):
        if not self._data:
            raise IndexError("get from empty queue")
        return self._data.pop(0)

    def empty(self):
        return len(self._data) == 0

    def qsize(self):
        return len(self._data)


class LifoQueue:
    """LIFO (stack) queue implementation."""

    def __init__(self, maxsize=0):
        self._maxsize = maxsize
        self._data = []

    def put(self, item):
        self._data.append(item)

    def get(self):
        if not self._data:
            raise IndexError("get from empty LifoQueue")
        return self._data.pop()

    def empty(self):
        return len(self._data) == 0

    def qsize(self):
        return len(self._data)


class PriorityQueue:
    """Priority queue: lowest-value-first (min-heap) implementation."""

    def __init__(self, maxsize=0):
        self._maxsize = maxsize
        self._heap = []

    def _sift_up(self, pos):
        """Move element at pos up to its correct position."""
        item = self._heap[pos]
        while pos > 0:
            parent = (pos - 1) >> 1
            parent_item = self._heap[parent]
            if item < parent_item:
                self._heap[pos] = parent_item
                pos = parent
            else:
                break
        self._heap[pos] = item

    def _sift_down(self, pos):
        """Move element at pos down to its correct position."""
        n = len(self._heap)
        item = self._heap[pos]
        while True:
            left = 2 * pos + 1
            right = 2 * pos + 2
            smallest = pos

            if left < n and self._heap[left] < self._heap[smallest]:
                smallest = left
            if right < n and self._heap[right] < self._heap[smallest]:
                smallest = right

            if smallest == pos:
                break

            self._heap[pos] = self._heap[smallest]
            pos = smallest

        self._heap[pos] = item

    def put(self, item):
        self._heap.append(item)
        self._sift_up(len(self._heap) - 1)

    def get(self):
        if not self._heap:
            raise IndexError("get from empty PriorityQueue")
        n = len(self._heap)
        if n == 1:
            return self._heap.pop()
        # Swap root with last element, pop last, then sift down
        min_item = self._heap[0]
        self._heap[0] = self._heap.pop()
        self._sift_down(0)
        return min_item

    def empty(self):
        return len(self._heap) == 0

    def qsize(self):
        return len(self._heap)


def queue_fifo():
    """Demonstrates FIFO behavior: put(1), put(2), get() == 1."""
    q = Queue()
    q.put(1)
    q.put(2)
    return q.get()


def queue_lifo():
    """Demonstrates LIFO behavior: put(1), put(2), get() == 2."""
    q = LifoQueue()
    q.put(1)
    q.put(2)
    return q.get()


def queue_empty():
    """Demonstrates empty check: new Queue().empty() == True."""
    q = Queue()
    return q.empty()