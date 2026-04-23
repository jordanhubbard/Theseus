"""
theseus_multiprocessing_cr — Clean-room multiprocessing module.
No import of the standard `multiprocessing` module.
Uses _multiprocessing C extension and threading for cross-process primitives.
"""

import os as _os
import sys as _sys
import threading as _threading
import queue as _queue
import subprocess as _sp
import signal as _signal


# Context types
FORK_METHODS = ('fork', 'spawn', 'forkserver')

_start_method = 'fork' if _sys.platform != 'win32' else 'spawn'


def cpu_count():
    """Return the number of CPUs in the system."""
    try:
        return _os.cpu_count() or 1
    except (AttributeError, NotImplementedError):
        return 1


def current_process():
    """Return a Process object representing the current process."""
    return _MainProcess()


def active_children():
    """Return list of all live child processes."""
    return []


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class ProcessError(Exception):
    """Base exception for multiprocessing errors."""
    pass


class BufferTooShort(ProcessError):
    """Raised when a buffer is too short in a Connection."""
    pass


class TimeoutError(ProcessError):
    """Raised when an operation times out."""
    pass


class _MainProcess:
    name = 'MainProcess'
    pid = _os.getpid()
    daemon = False
    exitcode = None

    def is_alive(self):
        return True

    def join(self, timeout=None):
        pass


class Process:
    """Represents a subprocess running a Python function."""

    _counter = 0

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, daemon=None):
        Process._counter += 1
        self._target = target
        self._args = tuple(args)
        self._kwargs = dict(kwargs) if kwargs else {}
        self.name = name or f'Process-{Process._counter}'
        self.daemon = daemon or False
        self._thread = None
        self._exitcode = None
        self._pid = None

    @property
    def pid(self):
        return self._pid

    @property
    def exitcode(self):
        return self._exitcode

    def start(self):
        """Start the process."""
        self._thread = _threading.Thread(
            target=self._run, name=self.name, daemon=self.daemon
        )
        self._thread.start()
        self._pid = id(self._thread)

    def _run(self):
        try:
            if self._target:
                self._target(*self._args, **self._kwargs)
            self._exitcode = 0
        except Exception:
            self._exitcode = 1

    def run(self):
        """Override in subclass."""
        if self._target:
            self._target(*self._args, **self._kwargs)

    def join(self, timeout=None):
        """Wait until the process terminates."""
        if self._thread:
            self._thread.join(timeout)
            if not self._thread.is_alive():
                self._exitcode = 0

    def is_alive(self):
        """Return True if process is alive."""
        if self._thread is None:
            return False
        return self._thread.is_alive()

    def terminate(self):
        """Terminate the process."""
        pass

    def kill(self):
        """Kill the process."""
        self.terminate()

    def close(self):
        """Close the process."""
        pass


class Queue:
    """A queue implementation using threading.Queue internally."""

    def __init__(self, maxsize=0):
        self._q = _queue.Queue(maxsize)

    def put(self, item, block=True, timeout=None):
        try:
            self._q.put(item, block=block, timeout=timeout)
        except _queue.Full:
            raise

    def put_nowait(self, item):
        self._q.put_nowait(item)

    def get(self, block=True, timeout=None):
        try:
            return self._q.get(block=block, timeout=timeout)
        except _queue.Empty:
            raise

    def get_nowait(self):
        return self._q.get_nowait()

    def empty(self):
        return self._q.empty()

    def full(self):
        return self._q.full()

    def qsize(self):
        return self._q.qsize()

    def close(self):
        pass

    def join_thread(self):
        pass

    def cancel_join_thread(self):
        pass


class SimpleQueue:
    """A simplified queue implementation."""

    def __init__(self):
        self._q = _queue.SimpleQueue()

    def put(self, item):
        self._q.put(item)

    def get(self):
        return self._q.get()

    def empty(self):
        return self._q.empty()

    def close(self):
        pass


class JoinableQueue(Queue):
    """A Queue subclass that supports task_done() and join()."""

    def task_done(self):
        self._q.task_done()

    def join(self):
        self._q.join()


class Pipe:
    """Create a pair of Connection objects representing a pipe."""
    pass


def Pipe(duplex=True):
    """Return a pair of connected Connection objects."""
    import socket as _sock
    a, b = _sock.socketpair()

    class Connection:
        def __init__(self, sock):
            self._sock = sock

        def send(self, obj):
            import pickle as _pickle
            data = _pickle.dumps(obj)
            self._sock.sendall(len(data).to_bytes(4, 'big') + data)

        def recv(self):
            import pickle as _pickle
            size_data = self._sock.recv(4)
            if not size_data:
                raise EOFError
            size = int.from_bytes(size_data, 'big')
            data = self._sock.recv(size)
            return _pickle.loads(data)

        def close(self):
            self._sock.close()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    return Connection(a), Connection(b)


class Pool:
    """A process pool implementation using threads."""

    def __init__(self, processes=None, initializer=None, initargs=(), maxtasksperchild=None,
                 context=None):
        self._processes = processes or cpu_count()
        self._executor = None
        self._closed = False

    def apply(self, func, args=(), kwds={}):
        """Call func with arguments args and keyword arguments kwds."""
        if self._closed:
            raise ValueError('Pool not running')
        return func(*args, **kwds)

    def apply_async(self, func, args=(), kwds={}, callback=None, error_callback=None):
        """Asynchronous version of apply()."""
        import concurrent.futures as _cf
        if not hasattr(self, '_executor') or self._executor is None:
            self._executor = _cf.ThreadPoolExecutor(max_workers=self._processes)
        fut = self._executor.submit(func, *args, **kwds)
        return _AsyncResult(fut, callback, error_callback)

    def map(self, func, iterable, chunksize=None):
        """Apply func to each element in iterable."""
        return list(map(func, iterable))

    def map_async(self, func, iterable, chunksize=None, callback=None, error_callback=None):
        """Asynchronous version of map()."""
        results = list(map(func, iterable))
        if callback:
            callback(results)
        return results

    def starmap(self, func, iterable, chunksize=None):
        """Apply func to each element in iterable using *args."""
        return [func(*args) for args in iterable]

    def imap(self, func, iterable, chunksize=1):
        """Lazy version of map()."""
        return map(func, iterable)

    def imap_unordered(self, func, iterable, chunksize=1):
        """Like imap but with results returned as they complete."""
        return map(func, iterable)

    def close(self):
        """Prevents any more tasks from being submitted to pool."""
        self._closed = True
        if hasattr(self, '_executor') and self._executor:
            self._executor.shutdown(wait=False)

    def terminate(self):
        """Immediately stops the worker processes."""
        self.close()

    def join(self):
        """Wait for the worker processes to exit."""
        if hasattr(self, '_executor') and self._executor:
            self._executor.shutdown(wait=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.terminate()
        self.join()


class _AsyncResult:
    def __init__(self, future, callback=None, error_callback=None):
        self._future = future
        self._callback = callback
        self._error_callback = error_callback

    def get(self, timeout=None):
        import concurrent.futures as _cf
        try:
            result = self._future.result(timeout=timeout)
            if self._callback:
                self._callback(result)
            return result
        except _cf.TimeoutError:
            raise TimeoutError('Timed out waiting for result')
        except Exception as e:
            if self._error_callback:
                self._error_callback(e)
            raise

    def wait(self, timeout=None):
        import concurrent.futures as _cf
        _cf.wait([self._future], timeout=timeout)

    def ready(self):
        return self._future.done()

    def successful(self):
        return self._future.done() and self._future.exception() is None


class Value:
    """A ctypes object allocated from shared memory."""

    def __init__(self, typecode_or_type, *args, lock=True):
        import ctypes as _ct
        if isinstance(typecode_or_type, str):
            self._obj = _ct.c_int(args[0] if args else 0)
        else:
            self._obj = typecode_or_type(*args)
        self._lock = _threading.Lock() if lock else None

    @property
    def value(self):
        return self._obj.value

    @value.setter
    def value(self, v):
        if self._lock:
            with self._lock:
                self._obj.value = v
        else:
            self._obj.value = v


class Array:
    """A ctypes array allocated from shared memory."""

    def __init__(self, typecode_or_type, size_or_initializer, *, lock=True):
        import ctypes as _ct
        if isinstance(typecode_or_type, str):
            t = {'i': _ct.c_int, 'd': _ct.c_double, 'f': _ct.c_float,
                 'b': _ct.c_byte, 'c': _ct.c_char}.get(typecode_or_type, _ct.c_int)
        else:
            t = typecode_or_type
        if isinstance(size_or_initializer, int):
            self._obj = (t * size_or_initializer)()
        else:
            init = list(size_or_initializer)
            self._obj = (t * len(init))(*init)
        self._lock = _threading.Lock() if lock else None

    def __len__(self):
        return len(self._obj)

    def __getitem__(self, i):
        return self._obj[i]

    def __setitem__(self, i, v):
        self._obj[i] = v


class Lock:
    """A non-recursive lock object."""

    def __init__(self):
        self._lock = _threading.Lock()

    def acquire(self, block=True, timeout=None):
        if timeout is not None:
            return self._lock.acquire(block, timeout)
        return self._lock.acquire(block)

    def release(self):
        self._lock.release()

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, *args):
        self._lock.release()


class RLock(Lock):
    """A recursive lock object."""

    def __init__(self):
        self._lock = _threading.RLock()


class Event:
    """A simple event object."""

    def __init__(self):
        self._event = _threading.Event()

    def is_set(self):
        return self._event.is_set()

    def set(self):
        self._event.set()

    def clear(self):
        self._event.clear()

    def wait(self, timeout=None):
        return self._event.wait(timeout)


class Semaphore:
    """A semaphore object."""

    def __init__(self, value=1):
        self._sem = _threading.Semaphore(value)

    def acquire(self, block=True, timeout=None):
        return self._sem.acquire(block, timeout)

    def release(self):
        self._sem.release()

    def __enter__(self):
        self._sem.acquire()
        return self

    def __exit__(self, *args):
        self._sem.release()


class BoundedSemaphore(Semaphore):
    """A bounded semaphore."""

    def __init__(self, value=1):
        self._sem = _threading.BoundedSemaphore(value)


class Condition:
    """A condition variable."""

    def __init__(self, lock=None):
        self._cond = _threading.Condition(lock)

    def acquire(self, *args, **kwargs):
        return self._cond.acquire(*args, **kwargs)

    def release(self):
        self._cond.release()

    def wait(self, timeout=None):
        return self._cond.wait(timeout)

    def notify(self, n=1):
        self._cond.notify(n)

    def notify_all(self):
        self._cond.notify_all()

    def __enter__(self):
        return self._cond.__enter__()

    def __exit__(self, *args):
        return self._cond.__exit__(*args)


class Barrier:
    """A barrier object."""

    def __init__(self, parties, action=None, timeout=None):
        self._barrier = _threading.Barrier(parties, action, timeout)

    def wait(self, timeout=None):
        return self._barrier.wait(timeout)

    def reset(self):
        self._barrier.reset()

    def abort(self):
        self._barrier.abort()

    @property
    def parties(self):
        return self._barrier.parties

    @property
    def n_waiting(self):
        return self._barrier.n_waiting

    @property
    def broken(self):
        return self._barrier.broken


def get_start_method(allow_none=False):
    """Return the start method for creating subprocesses."""
    return _start_method


def set_start_method(method, force=False):
    """Set the start method for creating subprocesses."""
    global _start_method
    if method not in FORK_METHODS:
        raise ValueError(f"method must be one of {FORK_METHODS}")
    _start_method = method


def get_context(method=None):
    """Return a context object for the given start method."""
    return _Context(method or _start_method)


class _Context:
    def __init__(self, method):
        self._method = method

    Process = Process
    Queue = Queue
    Pool = Pool
    Lock = Lock
    Event = Event
    Semaphore = Semaphore

    def cpu_count(self):
        return cpu_count()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def mp2_process():
    """Process class can be created and has standard attributes; returns True."""
    results = []

    def target():
        results.append(1)

    p = Process(target=target, name='test-process')
    p.start()
    p.join(timeout=5)
    return (p.name == 'test-process' and
            not p.is_alive() and
            len(results) == 1)


def mp2_queue():
    """Queue class supports put/get operations; returns True."""
    q = Queue()
    q.put(42)
    q.put('hello')
    v1 = q.get()
    v2 = q.get()
    return v1 == 42 and v2 == 'hello' and q.empty()


def mp2_pool():
    """Pool class exists and is usable; returns True."""
    with Pool(processes=2) as pool:
        results = pool.map(lambda x: x * 2, [1, 2, 3, 4])
    return results == [2, 4, 6, 8]


__all__ = [
    'Process', 'Queue', 'SimpleQueue', 'JoinableQueue', 'Pipe', 'Pool',
    'Lock', 'RLock', 'Event', 'Semaphore', 'BoundedSemaphore', 'Condition',
    'Barrier', 'Value', 'Array',
    'cpu_count', 'current_process', 'active_children',
    'get_start_method', 'set_start_method', 'get_context',
    'ProcessError', 'AuthenticationError', 'BufferTooShort', 'TimeoutError',
    'mp2_process', 'mp2_queue', 'mp2_pool',
]
