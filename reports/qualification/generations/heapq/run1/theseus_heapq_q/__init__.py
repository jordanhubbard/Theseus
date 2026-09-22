# generation A sift functions

__all__ = ["nlargest", "nsmallest", "heapify", "heappush", "heappop"]


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


def heapify(x):
    n = len(x)
    for i in range(n // 2 - 1, -1, -1):
        _siftup(x, i)


def heappush(heap, item):
    heap.append(item)
    _siftdown(heap, 0, len(heap) - 1)


def heappop(heap):
    lastelt = heap.pop()
    if heap:
        returnitem = heap[0]
        heap[0] = lastelt
        _siftup(heap, 0)
        return returnitem
    return lastelt


def nlargest(n, iterable):
    if n <= 0:
        return []
    it = iter(iterable)
    result = []
    try:
        for _ in range(n):
            result.append(next(it))
    except StopIteration:
        result.sort(reverse=True)
        return result
    heapify(result)
    for elem in it:
        if elem > result[0]:
            heappop(result)
            heappush(result, elem)
    result.sort(reverse=True)
    return result


def nsmallest(n, iterable):
    if n <= 0:
        return []
    it = iter(iterable)
    result = []
    try:
        for _ in range(n):
            result.append(-next(it))
    except StopIteration:
        return sorted(-x for x in result)
    heapify(result)
    for elem in it:
        if elem < -result[0]:
            heappop(result)
            heappush(result, -elem)
    return sorted(-x for x in result)
