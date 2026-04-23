"""
theseus_queue_cr2 - Clean-room queue utilities implementation.
"""

import heapq


class Empty(Exception):
    """Exception raised when get() is called on an empty queue."""
    pass


class Queue:
    """Simple FIFO queue."""
    
    def __init__(self, maxsize=0):
        self._queue = []
        self._maxsize = maxsize
    
    def put(self, item):
        self._queue.append(item)
    
    def get(self):
        if not self._queue:
            raise Empty("Queue is empty")
        return self._queue.pop(0)
    
    def empty(self):
        return len(self._queue) == 0
    
    def qsize(self):
        return len(self._queue)


class PriorityQueue:
    """Min-heap priority queue where items are (priority, value) tuples."""
    
    def __init__(self, maxsize=0):
        self._heap = []
        self._maxsize = maxsize
    
    def put(self, item):
        heapq.heappush(self._heap, item)
    
    def get(self):
        if not self._heap:
            raise Empty("PriorityQueue is empty")
        return heapq.heappop(self._heap)
    
    def empty(self):
        return len(self._heap) == 0
    
    def qsize(self):
        return len(self._heap)


class SimpleQueue:
    """Simple FIFO queue with put/get, no blocking timeout."""
    
    def __init__(self):
        self._queue = []
    
    def put(self, item):
        self._queue.append(item)
    
    def get(self):
        if not self._queue:
            raise Empty("SimpleQueue is empty")
        return self._queue.pop(0)
    
    def empty(self):
        return len(self._queue) == 0


def queue2_priority():
    """
    Put (2,'b') and (1,'a') into a PriorityQueue; get() returns (1,'a').
    Returns [1, 'a'].
    """
    pq = PriorityQueue()
    pq.put((2, 'b'))
    pq.put((1, 'a'))
    result = pq.get()
    return [result[0], result[1]]


def queue2_simple_get():
    """
    SimpleQueue put then get returns same item.
    Returns True.
    """
    sq = SimpleQueue()
    item = ('test_item',)
    sq.put(item)
    result = sq.get()
    return result == item


def queue2_empty():
    """
    New Queue().empty() == True.
    Returns True.
    """
    q = Queue()
    return q.empty()