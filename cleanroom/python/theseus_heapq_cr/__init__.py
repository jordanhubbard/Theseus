"""
theseus_heapq_cr — Clean-room heapq module.
No import of the standard `heapq` module.
"""


def heappush(heap, item):
    """Push item onto heap, maintaining the heap invariant."""
    heap.append(item)
    _siftdown(heap, 0, len(heap) - 1)


def heappop(heap):
    """Pop the smallest item off the heap."""
    lastelt = heap.pop()
    if heap:
        returnitem = heap[0]
        heap[0] = lastelt
        _siftup(heap, 0)
        return returnitem
    return lastelt


def heapreplace(heap, item):
    """Pop and return the smallest item, pushing item instead."""
    returnitem = heap[0]
    heap[0] = item
    _siftup(heap, 0)
    return returnitem


def heappushpop(heap, item):
    """Push item then pop and return the smallest."""
    if heap and heap[0] < item:
        item, heap[0] = heap[0], item
        _siftup(heap, 0)
    return item


def heapify(x):
    """Transform list x into a heap, in-place."""
    n = len(x)
    for i in reversed(range(n // 2)):
        _siftup(x, i)


def _siftdown(heap, startpos, pos):
    newitem = heap[pos]
    while pos > startpos:
        parentpos = (pos - 1) >> 1
        parent = heap[parentpos]
        if newitem < parent:
            heap[pos] = parent
            pos = parentpos
        else:
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
    """Return the n smallest elements of iterable."""
    if key is None:
        result = sorted(iterable)[:n]
    else:
        result = sorted(iterable, key=key)[:n]
    return result


def nlargest(n, iterable, key=None):
    """Return the n largest elements of iterable."""
    if key is None:
        result = sorted(iterable, reverse=True)[:n]
    else:
        result = sorted(iterable, key=key, reverse=True)[:n]
    return result


def merge(*iterables, key=None, reverse=False):
    """Merge sorted iterables into a single sorted iterator."""
    if key is None:
        items = sorted((item for it in iterables for item in it), reverse=reverse)
    else:
        items = sorted((item for it in iterables for item in it), key=key, reverse=reverse)
    return iter(items)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def heapq2_push_pop():
    """heappush([3,2], 1); heappop returns 1; returns 1."""
    h = [3, 2]
    heapify(h)
    heappush(h, 1)
    return heappop(h)


def heapq2_heapify():
    """heapify converts list to valid heap; root is minimum; returns True."""
    h = [5, 3, 8, 1, 4]
    heapify(h)
    return h[0] == 1


def heapq2_nsmallest():
    """nsmallest(3, [5,3,1,4,2]) returns [1,2,3]; returns True."""
    return nsmallest(3, [5, 3, 1, 4, 2]) == [1, 2, 3]


__all__ = [
    'heappush', 'heappop', 'heapreplace', 'heappushpop',
    'heapify', 'nsmallest', 'nlargest', 'merge',
    'heapq2_push_pop', 'heapq2_heapify', 'heapq2_nsmallest',
]
