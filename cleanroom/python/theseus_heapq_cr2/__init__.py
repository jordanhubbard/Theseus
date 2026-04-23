"""
Clean-room implementation of heapq utilities.
No import of heapq or any third-party library.
"""


def heappush(heap, item):
    """Push item onto heap, maintaining the heap invariant."""
    heap.append(item)
    _sift_up(heap, len(heap) - 1)


def heappop(heap):
    """Pop the smallest item off the heap, maintaining the heap invariant."""
    if not heap:
        raise IndexError("pop from an empty heap")
    last = heap.pop()
    if heap:
        return_item = heap[0]
        heap[0] = last
        _sift_down(heap, 0)
        return return_item
    return last


def heapreplace(heap, item):
    """
    Pop and return the smallest item from the heap, and also push the new item.
    The heap size doesn't change. If the heap is empty, IndexError is raised.
    This is more efficient than heappop() followed by heappush().
    """
    if not heap:
        raise IndexError("heap index out of range")
    return_item = heap[0]
    heap[0] = item
    _sift_down(heap, 0)
    return return_item


def heapify(heap):
    """Transform list into a heap, in-place, in O(len(heap)) time."""
    n = len(heap)
    # Start from the last non-leaf node and sift down
    for i in range(n // 2 - 1, -1, -1):
        _sift_down(heap, i)


def nlargest(n, iterable):
    """Return a list with the n largest elements from the dataset in descending order."""
    data = list(iterable)
    if n <= 0:
        return []
    if n >= len(data):
        return sorted(data, reverse=True)
    
    # Use a min-heap of size n to track the n largest elements
    # Build initial heap from first n elements
    heap = data[:n]
    heapify(heap)
    
    for item in data[n:]:
        if item > heap[0]:
            heapreplace(heap, item)
    
    return sorted(heap, reverse=True)


def nsmallest(n, iterable):
    """Return a list with the n smallest elements from the dataset in ascending order."""
    data = list(iterable)
    if n <= 0:
        return []
    if n >= len(data):
        return sorted(data)
    
    # Use a max-heap of size n to track the n smallest elements
    # We simulate a max-heap by negating values
    heap = [-x for x in data[:n]]
    heapify(heap)
    
    for item in data[n:]:
        if -item > heap[0]:  # item < -heap[0], i.e., item is smaller than current max
            heapreplace(heap, -item)
    
    return sorted(-x for x in heap)


def _sift_up(heap, pos):
    """Move the item at pos up to its correct position (used after append)."""
    item = heap[pos]
    while pos > 0:
        parent_pos = (pos - 1) >> 1
        parent = heap[parent_pos]
        if item < parent:
            heap[pos] = parent
            pos = parent_pos
        else:
            break
    heap[pos] = item


def _sift_down(heap, pos):
    """Move the item at pos down to its correct position."""
    n = len(heap)
    item = heap[pos]
    
    while True:
        left_child = 2 * pos + 1
        if left_child >= n:
            break
        
        # Find the smaller child
        right_child = left_child + 1
        min_child = left_child
        if right_child < n and heap[right_child] < heap[left_child]:
            min_child = right_child
        
        if heap[min_child] < item:
            heap[pos] = heap[min_child]
            pos = min_child
        else:
            break
    
    heap[pos] = item


# Zero-arg invariant functions

def heapq2_heapreplace():
    """
    Invariant test: h=[1,3,5]; heapreplace(h, 2); h[0] == 2
    Returns True.
    """
    h = [1, 3, 5]
    heapify(h)
    heapreplace(h, 2)
    return h[0] == 2


def heapq2_nlargest():
    """
    Invariant test: nlargest(2, [3,1,4,1,5]) == [5, 4]
    """
    return nlargest(2, [3, 1, 4, 1, 5])


def heapq2_nsmallest():
    """
    Invariant test: nsmallest(2, [3,1,4,1,5]) == [1, 1]
    """
    return nsmallest(2, [3, 1, 4, 1, 5])