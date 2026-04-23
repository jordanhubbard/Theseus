"""
theseus_multiprocessing_utils - Clean-room multiprocessing primitives.
Implements Queue, SimpleChannel, and Value without importing multiprocessing.
"""

import threading
import collections


class Queue:
    """
    A thread-safe FIFO queue with put/get/empty/qsize operations.
    Designed as a multiprocessing Queue-like primitive.
    """

    def __init__(self, maxsize=0):
        self._maxsize = maxsize
        self._deque = collections.deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)

    def put(self, item, block=True, timeout=None):
        """Put an item into the queue."""
        with self._not_full:
            if self._maxsize > 0:
                if not block:
                    if len(self._deque) >= self._maxsize:
                        raise Exception("Queue is full")
                elif timeout is None:
                    while len(self._deque) >= self._maxsize:
                        self._not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a non-negative number")
                else:
                    import time
                    endtime = time.monotonic() + timeout
                    while len(self._deque) >= self._maxsize:
                        remaining = endtime - time.monotonic()
                        if remaining <= 0.0:
                            raise Exception("Queue is full")
                        self._not_full.wait(remaining)
            self._deque.append(item)
            self._not_empty.notify()

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue."""
        with self._not_empty:
            if not block:
                if not self._deque:
                    raise Exception("Queue is empty")
            elif timeout is None:
                while not self._deque:
                    self._not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                import time
                endtime = time.monotonic() + timeout
                while not self._deque:
                    remaining = endtime - time.monotonic()
                    if remaining <= 0.0:
                        raise Exception("Queue is empty")
                    self._not_empty.wait(remaining)
            item = self._deque.popleft()
            self._not_full.notify()
            return item

    def empty(self):
        """Return True if the queue is empty, False otherwise."""
        with self._lock:
            return len(self._deque) == 0

    def qsize(self):
        """Return the approximate size of the queue."""
        with self._lock:
            return len(self._deque)

    def put_nowait(self, item):
        """Put an item into the queue without blocking."""
        return self.put(item, block=False)

    def get_nowait(self):
        """Remove and return an item if one is immediately available."""
        return self.get(block=False)


class SimpleChannel:
    """
    A simple bidirectional message-passing channel (Pipe-like).
    Provides send/recv operations.
    """

    def __init__(self):
        self._queue = Queue()
        self._lock = threading.Lock()

    def send(self, obj):
        """Send an object through the channel."""
        self._queue.put(obj)

    def recv(self, block=True, timeout=None):
        """Receive an object from the channel."""
        return self._queue.get(block=block, timeout=timeout)

    def poll(self):
        """Return True if there is data available to receive."""
        return not self._queue.empty()

    def close(self):
        """Close the channel (no-op in this implementation)."""
        pass


def Pipe():
    """
    Create a pair of connected SimpleChannel objects.
    Returns (conn1, conn2) where each can send/recv.
    """
    # For a true pipe, we need two queues (one for each direction)
    class _PipeEnd:
        def __init__(self, send_queue, recv_queue):
            self._send_queue = send_queue
            self._recv_queue = recv_queue

        def send(self, obj):
            self._send_queue.put(obj)

        def recv(self, block=True, timeout=None):
            return self._recv_queue.get(block=block, timeout=timeout)

        def poll(self):
            return not self._recv_queue.empty()

        def close(self):
            pass

    q1 = Queue()
    q2 = Queue()
    conn1 = _PipeEnd(q1, q2)
    conn2 = _PipeEnd(q2, q1)
    return conn1, conn2


# Type code to Python type mapping
_TYPECODE_MAP = {
    'b': int,   # signed char
    'B': int,   # unsigned char
    'h': int,   # signed short
    'H': int,   # unsigned short
    'i': int,   # signed int
    'I': int,   # unsigned int
    'l': int,   # signed long
    'L': int,   # unsigned long
    'q': int,   # signed long long
    'Q': int,   # unsigned long long
    'f': float, # float
    'd': float, # double
    'c': bytes, # char
    'u': str,   # unicode char (deprecated but kept for compat)
}


class Value:
    """
    A shared typed value object, similar to multiprocessing.Value.
    Holds a single value of the specified typecode.
    """

    def __init__(self, typecode, val, lock=True):
        if typecode not in _TYPECODE_MAP:
            raise ValueError(f"Unknown typecode: {typecode!r}")
        self._typecode = typecode
        self._type = _TYPECODE_MAP[typecode]
        self._value = self._type(val)
        if lock:
            self._lock = threading.RLock()
        else:
            self._lock = None

    @property
    def value(self):
        """Get the current value."""
        if self._lock is not None:
            with self._lock:
                return self._value
        return self._value

    @value.setter
    def value(self, val):
        """Set the current value."""
        if self._lock is not None:
            with self._lock:
                self._value = self._type(val)
        else:
            self._value = self._type(val)

    def get_lock(self):
        """Return the lock used to synchronize access."""
        return self._lock

    def __repr__(self):
        return f"Value(typecode={self._typecode!r}, value={self._value!r})"


# --- Invariant functions ---

def multiprocessing_queue_put_get():
    """Queue().put(42); get() == 42 → returns 42"""
    q = Queue()
    q.put(42)
    return q.get()


def multiprocessing_queue_empty():
    """empty Queue is empty → returns True"""
    q = Queue()
    return q.empty()


def multiprocessing_value():
    """Value('i', 7).value == 7 → returns 7"""
    v = Value('i', 7)
    return v.value


__all__ = [
    'Queue',
    'SimpleChannel',
    'Value',
    'Pipe',
    'multiprocessing_queue_put_get',
    'multiprocessing_queue_empty',
    'multiprocessing_value',
]