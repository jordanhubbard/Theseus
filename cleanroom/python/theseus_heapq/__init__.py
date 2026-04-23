"""
theseus_heapq - Clean-room implementation of a binary min-heap.
No import of the original heapq module.
"""


def heappush(heap, item):
    """Push item onto heap, maintaining the heap invariant."""
    heap.append(item)
    _sift_up(heap, len(heap) - 1)


def heappop(heap):
    """Pop the smallest item off the heap, maintaining the heap invariant."""
    if not heap:
        raise IndexError("pop from an empty heap")
    # Move the last element to the root and sift down
    last = heap.pop()
    if heap:
        root = heap[0]
        heap[0] = last
        _sift_down(heap, 0)
        return root
    return last


def heapify(x):
    """Transform list x into a heap, in-place, in O(n) time."""
    n = len(x)
    # Start from the last non-leaf node and sift down each
    for i in reversed(range(n // 2)):
        _sift_down(x, i)


def nsmallest(n, iterable):
    """Return a list with the n smallest elements from the iterable."""
    data = list(iterable)
    heapify(data)
    result = []
    for _ in range(min(n, len(data))):
        result.append(heappop(data))
    return result


def _sift_up(heap, pos):
    """Move the item at pos up to its correct position (used after push)."""
    item = heap[pos]
    while pos > 0:
        parent = (pos - 1) >> 1
        if item < heap[parent]:
            heap[pos] = heap[parent]
            pos = parent
        else:
            break
    heap[pos] = item


def _sift_down(heap, pos):
    """Move the item at pos down to its correct position (used after pop/heapify)."""
    n = len(heap)
    item = heap[pos]
    while True:
        left = 2 * pos + 1
        right = 2 * pos + 2
        smallest = pos

        if left < n and heap[left] < heap[smallest]:
            smallest = left
        if right < n and heap[right] < heap[smallest]:
            smallest = right

        if smallest == pos:
            break

        heap[pos] = heap[smallest]
        pos = smallest

    heap[pos] = item


# --- Invariant verification functions ---

def heapq_min_of_three():
    """heappop after pushing 3, 1, 2 returns 1."""
    heap = []
    heappush(heap, 3)
    heappush(heap, 1)
    heappush(heap, 2)
    return heappop(heap)


def heapq_heapify_min():
    """min of heapified [5, 3, 1, 4, 2] == 1."""
    data = [5, 3, 1, 4, 2]
    heapify(data)
    return data[0]


def heapq_nsmallest():
    """nsmallest(3, [5, 3, 1, 4, 2]) == [1, 2, 3]."""
    return nsmallest(3, [5, 3, 1, 4, 2])