"""Clean-room implementation of a heap queue (min-heap) module.

Implements the standard binary min-heap algorithms from scratch without
importing the original `heapq` module.
"""


def heappush(heap, item):
    """Push item onto heap, maintaining the heap invariant."""
    heap.append(item)
    _siftdown(heap, 0, len(heap) - 1)


def heappop(heap):
    """Pop the smallest item off the heap, maintaining the heap invariant."""
    last = heap.pop()  # raises IndexError if empty
    if heap:
        returnitem = heap[0]
        heap[0] = last
        _siftup(heap, 0)
        return returnitem
    return last


def heappushpop(heap, item):
    """Push item, then pop and return the smallest item from the heap."""
    if heap and heap[0] < item:
        item, heap[0] = heap[0], item
        _siftup(heap, 0)
    return item


def heapreplace(heap, item):
    """Pop and return the current smallest, then push the new item."""
    returnitem = heap[0]
    heap[0] = item
    _siftup(heap, 0)
    return returnitem


def heapify(x):
    """Transform list into a heap, in-place, in O(len(x)) time."""
    n = len(x)
    for i in range(n // 2 - 1, -1, -1):
        _siftup(x, i)


def _siftdown(heap, startpos, pos):
    newitem = heap[pos]
    while pos > startpos:
        parentpos = (pos - 1) >> 1
        parent = heap[parentpos]
        if newitem < parent:
            heap[pos] = parent
            pos = parentpos
            continue
        break
    heap[pos] = newitem


def _siftup(heap, pos):
    endpos = len(heap)
    startpos = pos
    newitem = heap[pos]
    childpos = 2 * pos + 1
    while childpos < endpos:
        rightpos = childpos + 1
        if rightpos < endpos and not heap[childpos] < heap[rightpos]:
            childpos = rightpos
        heap[pos] = heap[childpos]
        pos = childpos
        childpos = 2 * pos + 1
    heap[pos] = newitem
    _siftdown(heap, startpos, pos)


def nsmallest(n, iterable, key=None):
    """Return a list with the n smallest elements from the dataset."""
    if n <= 0:
        return []
    items = list(iterable)
    if key is None:
        keyed = [(v, i, v) for i, v in enumerate(items)]
    else:
        keyed = [(key(v), i, v) for i, v in enumerate(items)]
    if n >= len(keyed):
        # full sort
        return [v for _, _, v in _sorted(keyed)]
    # Use a max-heap of size n by negating comparisons via wrapper
    # Simpler approach: sort and slice (still correct)
    return [v for _, _, v in _sorted(keyed)[:n]]


def nlargest(n, iterable, key=None):
    """Return a list with the n largest elements from the dataset."""
    if n <= 0:
        return []
    items = list(iterable)
    if key is None:
        keyed = [(v, i, v) for i, v in enumerate(items)]
    else:
        keyed = [(key(v), i, v) for i, v in enumerate(items)]
    return [v for _, _, v in _sorted(keyed, reverse=True)[:n]]


def _sorted(seq, reverse=False):
    """A small mergesort to avoid relying on built-in sorted semantics quirks."""
    arr = list(seq)
    n = len(arr)
    if n <= 1:
        return arr
    width = 1
    buf = [None] * n
    while width < n:
        for i in range(0, n, 2 * width):
            left = i
            mid = min(i + width, n)
            right = min(i + 2 * width, n)
            _merge(arr, buf, left, mid, right, reverse)
        width *= 2
    return arr


def _merge(arr, buf, left, mid, right, reverse):
    i = left
    j = mid
    k = left
    while i < mid and j < right:
        if reverse:
            cond = arr[j] > arr[i]
        else:
            cond = arr[i] <= arr[j]
        if cond:
            buf[k] = arr[i]
            i += 1
        else:
            buf[k] = arr[j]
            j += 1
        k += 1
    while i < mid:
        buf[k] = arr[i]
        i += 1
        k += 1
    while j < right:
        buf[k] = arr[j]
        j += 1
        k += 1
    for x in range(left, right):
        arr[x] = buf[x]


def merge(*iterables, key=None, reverse=False):
    """Merge multiple sorted inputs into a single sorted output."""
    # Build initial heap of (key, index, value, iterator)
    h = []
    iterators = [iter(it) for it in iterables]
    for idx, it in enumerate(iterators):
        try:
            v = next(it)
        except StopIteration:
            continue
        k = v if key is None else key(v)
        if reverse:
            # Invert comparison by wrapping in a reverser
            h.append((_Reverse(k), idx, v, it))
        else:
            h.append((k, idx, v, it))
    heapify(h)
    while h:
        k, idx, v, it = h[0]
        yield v
        try:
            nv = next(it)
        except StopIteration:
            heappop(h)
            continue
        nk = nv if key is None else key(nv)
        if reverse:
            heapreplace(h, (_Reverse(nk), idx, nv, it))
        else:
            heapreplace(h, (nk, idx, nv, it))


class _Reverse:
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        return other.value < self.value

    def __le__(self, other):
        return other.value <= self.value

    def __eq__(self, other):
        return self.value == other.value


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def heapq2_push_pop():
    """Push several items, then pop them — confirm smallest comes out first.

    Returns 1 on success.
    """
    h = []
    data = [5, 2, 9, 1, 7, 3, 8, 4, 6]
    for x in data:
        heappush(h, x)
    out = []
    while h:
        out.append(heappop(h))
    if out == sorted(data):
        return 1
    return 0


def heapq2_heapify():
    """Heapify a list and verify the heap invariant holds.

    Returns True on success.
    """
    arr = [9, 4, 7, 1, 0, 3, 8, 2, 6, 5]
    heapify(arr)
    n = len(arr)
    for i in range(n):
        left = 2 * i + 1
        right = 2 * i + 2
        if left < n and arr[left] < arr[i]:
            return False
        if right < n and arr[right] < arr[i]:
            return False
    # Also verify popping yields sorted order
    popped = []
    while arr:
        popped.append(heappop(arr))
    return popped == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def heapq2_nsmallest():
    """Verify nsmallest returns the correct k smallest elements.

    Returns True on success.
    """
    data = [12, 3, 7, 1, 19, 4, 8, 2, 11, 5, 6]
    if nsmallest(3, data) != [1, 2, 3]:
        return False
    if nsmallest(5, data) != [1, 2, 3, 4, 5]:
        return False
    if nsmallest(0, data) != []:
        return False
    if nsmallest(20, data) != sorted(data):
        return False
    # With key
    words = ["apple", "fig", "banana", "kiwi"]
    if nsmallest(2, words, key=len) != ["fig", "kiwi"]:
        return False
    return True