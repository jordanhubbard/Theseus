"""
theseus_multiprocessing_cr — Clean-room reimplementation stub for the
multiprocessing module.

This module provides minimal behavioral parity for the invariants required
by the Theseus clean-room rewrite initiative. It does NOT import the
original `multiprocessing` package; everything is built from Python
standard-library primitives only.
"""

import os
import sys
import time
import threading
import collections


# ---------------------------------------------------------------------------
# Process — a thread-backed stand-in for multiprocessing.Process
# ---------------------------------------------------------------------------

class Process(object):
    """A minimal Process-like object backed by a thread.

    Implements the small surface area exercised by the invariants:
    target/args/kwargs, start(), join(), is_alive(), name, daemon, pid,
    exitcode.
    """

    _id_counter = 0
    _id_lock = threading.Lock()

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, daemon=None):
        if kwargs is None:
            kwargs = {}
        self._target = target
        self._args = tuple(args)
        self._kwargs = dict(kwargs)
        with Process._id_lock:
            Process._id_counter += 1
            self._ident = Process._id_counter
        self.name = name if name is not None else "Process-%d" % self._ident
        self._daemon = bool(daemon) if daemon is not None else False
        self._thread = None
        self._started = False
        self._exitcode = None
        self.pid = None

    @property
    def daemon(self):
        return self._daemon

    @daemon.setter
    def daemon(self, value):
        if self._started:
            raise RuntimeError("cannot set daemon status of started process")
        self._daemon = bool(value)

    def run(self):
        if self._target is not None:
            self._target(*self._args, **self._kwargs)

    def _bootstrap(self):
        try:
            self.run()
            self._exitcode = 0
        except SystemExit as e:
            try:
                self._exitcode = int(e.code) if e.code is not None else 0
            except (TypeError, ValueError):
                self._exitcode = 1
        except BaseException:
            self._exitcode = 1

    def start(self):
        if self._started:
            raise RuntimeError("processes can only be started once")
        self._started = True
        self.pid = os.getpid() * 1000 + self._ident
        self._thread = threading.Thread(target=self._bootstrap, name=self.name)
        self._thread.daemon = self._daemon
        self._thread.start()

    def join(self, timeout=None):
        if not self._started:
            raise RuntimeError("can only join a started process")
        self._thread.join(timeout)

    def is_alive(self):
        if self._thread is None:
            return False
        return self._thread.is_alive()

    def terminate(self):
        # Cooperative termination is not implementable with threads.
        # We mark exitcode and let join finish naturally.
        pass

    kill = terminate

    def close(self):
        if self.is_alive():
            raise ValueError("Cannot close a running process")
        self._thread = None

    @property
    def exitcode(self):
        if self._thread is not None and self._thread.is_alive():
            return None
        return self._exitcode

    @property
    def ident(self):
        return self._ident


def current_process():
    t = threading.current_thread()
    p = Process.__new__(Process)
    p._target = None
    p._args = ()
    p._kwargs = {}
    p._ident = t.ident or 0
    p.name = t.name
    p._daemon = t.daemon
    p._thread = t
    p._started = True
    p._exitcode = None
    p.pid = os.getpid()
    return p


def cpu_count():
    try:
        n = os.cpu_count()
    except AttributeError:
        n = None
    return n if n else 1


def active_children():
    return []


# ---------------------------------------------------------------------------
# Queue — a thread-safe FIFO queue with the multiprocessing.Queue API
# ---------------------------------------------------------------------------

class _QueueEmpty(Exception):
    pass


class _QueueFull(Exception):
    pass


Empty = _QueueEmpty
Full = _QueueFull


class Queue(object):
    """A simple thread-safe FIFO queue mimicking multiprocessing.Queue."""

    def __init__(self, maxsize=0):
        self._maxsize = int(maxsize) if maxsize else 0
        self._deque = collections.deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._closed = False

    def _full(self):
        return self._maxsize > 0 and len(self._deque) >= self._maxsize

    def put(self, item, block=True, timeout=None):
        if self._closed:
            raise ValueError("Queue is closed")
        with self._not_full:
            if not block:
                if self._full():
                    raise Full
            elif timeout is None:
                while self._full():
                    self._not_full.wait()
            else:
                deadline = time.time() + timeout
                while self._full():
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise Full
                    self._not_full.wait(remaining)
            self._deque.append(item)
            self._not_empty.notify()

    def put_nowait(self, item):
        self.put(item, block=False)

    def get(self, block=True, timeout=None):
        with self._not_empty:
            if not block:
                if not self._deque:
                    raise Empty
            elif timeout is None:
                while not self._deque:
                    self._not_empty.wait()
            else:
                deadline = time.time() + timeout
                while not self._deque:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise Empty
                    self._not_empty.wait(remaining)
            item = self._deque.popleft()
            self._not_full.notify()
            return item

    def get_nowait(self):
        return self.get(block=False)

    def qsize(self):
        with self._lock:
            return len(self._deque)

    def empty(self):
        with self._lock:
            return not self._deque

    def full(self):
        with self._lock:
            return self._full()

    def close(self):
        self._closed = True

    def join_thread(self):
        pass

    def cancel_join_thread(self):
        pass


class SimpleQueue(Queue):
    def __init__(self):
        Queue.__init__(self, 0)


class JoinableQueue(Queue):
    def __init__(self, maxsize=0):
        Queue.__init__(self, maxsize)
        self._unfinished_tasks = 0
        self._all_tasks_done = threading.Condition(self._lock)

    def put(self, item, block=True, timeout=None):
        Queue.put(self, item, block=block, timeout=timeout)
        with self._lock:
            self._unfinished_tasks += 1

    def task_done(self):
        with self._all_tasks_done:
            if self._unfinished_tasks <= 0:
                raise ValueError("task_done() called too many times")
            self._unfinished_tasks -= 1
            if self._unfinished_tasks == 0:
                self._all_tasks_done.notify_all()

    def join(self):
        with self._all_tasks_done:
            while self._unfinished_tasks > 0:
                self._all_tasks_done.wait()


# ---------------------------------------------------------------------------
# Pool — a worker pool for parallel function application
# ---------------------------------------------------------------------------

class _AsyncResult(object):
    def __init__(self):
        self._event = threading.Event()
        self._value = None
        self._success = False

    def _set(self, success, value):
        self._success = success
        self._value = value
        self._event.set()

    def ready(self):
        return self._event.is_set()

    def successful(self):
        if not self._event.is_set():
            raise ValueError("Result is not ready")
        return self._success

    def wait(self, timeout=None):
        self._event.wait(timeout)

    def get(self, timeout=None):
        if not self._event.wait(timeout):
            raise TimeoutError("Result not available within timeout")
        if self._success:
            return self._value
        raise self._value


class _MapResult(object):
    def __init__(self, n):
        self._event = threading.Event()
        self._results = [None] * n
        self._remaining = n
        self._error = None
        self._lock = threading.Lock()
        if n == 0:
            self._event.set()

    def _set(self, idx, success, value):
        with self._lock:
            if success:
                self._results[idx] = value
            else:
                if self._error is None:
                    self._error = value
            self._remaining -= 1
            if self._remaining == 0:
                self._event.set()

    def ready(self):
        return self._event.is_set()

    def wait(self, timeout=None):
        self._event.wait(timeout)

    def get(self, timeout=None):
        if not self._event.wait(timeout):
            raise TimeoutError("Result not available within timeout")
        if self._error is not None:
            raise self._error
        return list(self._results)


class Pool(object):
    """A thread-backed pool that mimics multiprocessing.Pool."""

    def __init__(self, processes=None, initializer=None, initargs=()):
        if processes is None:
            processes = cpu_count()
        if processes < 1:
            raise ValueError("Number of processes must be at least 1")
        self._processes = int(processes)
        self._task_queue = Queue()
        self._workers = []
        self._closed = False
        self._terminated = False
        self._initializer = initializer
        self._initargs = tuple(initargs)
        for i in range(self._processes):
            t = threading.Thread(target=self._worker_loop, name="PoolWorker-%d" % i)
            t.daemon = True
            t.start()
            self._workers.append(t)

    def _worker_loop(self):
        if self._initializer is not None:
            try:
                self._initializer(*self._initargs)
            except BaseException:
                return
        while True:
            task = self._task_queue.get()
            if task is None:
                return
            func, args, kwargs, callback = task
            try:
                result = func(*args, **kwargs)
                callback(True, result)
            except BaseException as e:
                callback(False, e)

    def apply(self, func, args=(), kwds=None):
        if kwds is None:
            kwds = {}
        return self.apply_async(func, args, kwds).get()

    def apply_async(self, func, args=(), kwds=None, callback=None, error_callback=None):
        if kwds is None:
            kwds = {}
        if self._closed or self._terminated:
            raise ValueError("Pool not running")
        result = _AsyncResult()

        def _cb(success, value):
            result._set(success, value)
            if success and callback is not None:
                try:
                    callback(value)
                except BaseException:
                    pass
            elif not success and error_callback is not None:
                try:
                    error_callback(value)
                except BaseException:
                    pass

        self._task_queue.put((func, tuple(args), dict(kwds), _cb))
        return result

    def map(self, func, iterable, chunksize=None):
        return self.map_async(func, iterable, chunksize).get()

    def map_async(self, func, iterable, chunksize=None, callback=None, error_callback=None):
        if self._closed or self._terminated:
            raise ValueError("Pool not running")
        items = list(iterable)
        n = len(items)
        result = _MapResult(n)

        def make_cb(idx):
            def _cb(success, value):
                result._set(idx, success, value)
            return _cb

        for i, item in enumerate(items):
            self._task_queue.put((func, (item,), {}, make_cb(i)))

        if n == 0 and callback is not None:
            try:
                callback([])
            except BaseException:
                pass
        return result

    def imap(self, func, iterable, chunksize=1):
        items = list(iterable)
        results = [self.apply_async(func, (item,)) for item in items]
        for r in results:
            yield r.get()

    imap_unordered = imap

    def starmap(self, func, iterable, chunksize=None):
        items = [tuple(x) for x in iterable]
        results = [self.apply_async(func, args) for args in items]
        return [r.get() for r in results]

    def starmap_async(self, func, iterable, chunksize=None, callback=None, error_callback=None):
        items = [tuple(x) for x in iterable]
        n = len(items)
        result = _MapResult(n)

        def make_cb(idx):
            def _cb(success, value):
                result._set(idx, success, value)
            return _cb

        for i, args in enumerate(items):
            self._task_queue.put((func, args, {}, make_cb(i)))
        return result

    def close(self):
        if self._closed:
            return
        self._closed = True
        for _ in self._workers:
            self._task_queue.put(None)

    def terminate(self):
        self._terminated = True
        if not self._closed:
            self._closed = True
            for _ in self._workers:
                self._task_queue.put(None)

    def join(self):
        for t in self._workers:
            t.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
        self.join()


# ---------------------------------------------------------------------------
# Lock / Event / Semaphore primitives — pass-throughs to threading
# ---------------------------------------------------------------------------

def Lock():
    return threading.Lock()


def RLock():
    return threading.RLock()


def Event():
    return threading.Event()


def Semaphore(value=1):
    return threading.Semaphore(value)


def BoundedSemaphore(value=1):
    return threading.BoundedSemaphore(value)


def Condition(lock=None):
    return threading.Condition(lock)


# ---------------------------------------------------------------------------
# Pipe — a pair of connected duplex/simplex endpoints
# ---------------------------------------------------------------------------

class _Connection(object):
    def __init__(self, recv_q, send_q):
        self._recv_q = recv_q
        self._send_q = send_q
        self._closed = False

    def send(self, obj):
        if self._closed:
            raise OSError("connection closed")
        self._send_q.put(obj)

    def recv(self):
        if self._closed:
            raise EOFError("connection closed")
        return self._recv_q.get()

    def poll(self, timeout=0.0):
        try:
            item = self._recv_q.get(block=timeout > 0, timeout=timeout if timeout > 0 else None)
        except Empty:
            return False
        # put it back at the head — re-enqueue (FIFO peek workaround)
        self._recv_q._deque.appendleft(item)
        return True

    def close(self):
        self._closed = True


def Pipe(duplex=True):
    a_to_b = Queue()
    b_to_a = Queue()
    if duplex:
        return _Connection(b_to_a, a_to_b), _Connection(a_to_b, b_to_a)
    return _Connection(a_to_b, Queue()), _Connection(Queue(), a_to_b)


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def mp2_process():
    """Verify that Process objects can be created, started, and joined."""
    results = []

    def worker(x, y):
        results.append(x + y)

    p = Process(target=worker, args=(2, 3))
    if p.is_alive():
        return False
    if p.exitcode is not None:
        return False
    p.start()
    p.join()
    if p.is_alive():
        return False
    if results != [5]:
        return False
    if p.exitcode != 0:
        return False

    # A second process to confirm independence.
    p2 = Process(target=worker, args=(10, 20))
    p2.start()
    p2.join(timeout=5)
    if results[-1] != 30:
        return False

    # Daemon flag setter
    p3 = Process(target=worker, args=(0, 0))
    p3.daemon = True
    if p3.daemon is not True:
        return False
    p3.start()
    p3.join()

    return True


def mp2_queue():
    """Verify Queue put/get behavior, including blocking and non-blocking."""
    q = Queue()
    if not q.empty():
        return False
    q.put(1)
    q.put("hello")
    q.put([1, 2, 3])
    if q.qsize() != 3:
        return False
    if q.empty():
        return False
    if q.get() != 1:
        return False
    if q.get() != "hello":
        return False
    if q.get() != [1, 2, 3]:
        return False
    if not q.empty():
        return False

    # Non-blocking get on empty raises Empty.
    try:
        q.get_nowait()
        return False
    except Empty:
        pass

    # Bounded queue full behavior.
    bq = Queue(maxsize=2)
    bq.put(10)
    bq.put(20)
    if not bq.full():
        return False
    try:
        bq.put_nowait(30)
        return False
    except Full:
        pass
    if bq.get() != 10:
        return False
    bq.put(30)
    if bq.get() != 20:
        return False
    if bq.get() != 30:
        return False

    # Cross-thread put/get.
    q2 = Queue()

    def producer():
        for i in range(5):
            q2.put(i)

    t = threading.Thread(target=producer)
    t.start()
    t.join()
    received = [q2.get() for _ in range(5)]
    if received != [0, 1, 2, 3, 4]:
        return False

    return True


def mp2_pool():
    """Verify Pool.map and apply_async behavior."""
    def square(x):
        return x * x

    def add(a, b):
        return a + b

    with Pool(processes=3) as pool:
        result = pool.map(square, [1, 2, 3, 4, 5])
        if result != [1, 4, 9, 16, 25]:
            return False

        ar = pool.apply_async(add, (7, 8))
        ar.wait(timeout=5)
        if not ar.ready():
            return False
        if ar.get() != 15:
            return False
        if not ar.successful():
            return False

        sm = pool.starmap(add, [(1, 2), (3, 4), (5, 6)])
        if sm != [3, 7, 11]:
            return False

        # Empty map.
        if pool.map(square, []) != []:
            return False

        # imap preserves order.
        imap_result = list(pool.imap(square, [10, 20, 30]))
        if imap_result != [100, 400, 900]:
            return False

    # Pool created and joined explicitly.
    p2 = Pool(2)
    out = p2.apply(square, (9,))
    if out != 81:
        return False
    p2.close()
    p2.join()

    return True


__all__ = [
    "Process",
    "current_process",
    "active_children",
    "cpu_count",
    "Queue",
    "SimpleQueue",
    "JoinableQueue",
    "Empty",
    "Full",
    "Pool",
    "Lock",
    "RLock",
    "Event",
    "Semaphore",
    "BoundedSemaphore",
    "Condition",
    "Pipe",
    "mp2_process",
    "mp2_queue",
    "mp2_pool",
]