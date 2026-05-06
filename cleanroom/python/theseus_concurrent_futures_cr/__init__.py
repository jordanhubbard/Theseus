"""Clean-room reimplementation of concurrent.futures primitives.

This module provides a from-scratch implementation of the executor /
future / as_completed pattern without importing the original
``concurrent.futures`` package. Only Python standard-library built-ins
are used.
"""

import threading
import heapq
import time
import itertools


# ---------------------------------------------------------------------------
# Future states
# ---------------------------------------------------------------------------
_PENDING = "PENDING"
_RUNNING = "RUNNING"
_CANCELLED = "CANCELLED"
_CANCELLED_AND_NOTIFIED = "CANCELLED_AND_NOTIFIED"
_FINISHED = "FINISHED"

_DONE_STATES = (_CANCELLED, _CANCELLED_AND_NOTIFIED, _FINISHED)


class Error(Exception):
    """Base error for this clean-room module."""


class CancelledError(Error):
    """The future was cancelled."""


class TimeoutError(Error):  # noqa: A001 - mirrors stdlib name intentionally
    """The operation timed out."""


class InvalidStateError(Error):
    """The future is in an invalid state for the requested operation."""


# ---------------------------------------------------------------------------
# Future
# ---------------------------------------------------------------------------
class Future(object):
    """Represents the result of an asynchronous computation."""

    def __init__(self):
        self._condition = threading.Condition()
        self._state = _PENDING
        self._result = None
        self._exception = None
        self._done_callbacks = []
        self._waiters = []

    # -- introspection ------------------------------------------------------
    def cancel(self):
        with self._condition:
            if self._state in (_RUNNING, _FINISHED):
                return False
            if self._state in (_CANCELLED, _CANCELLED_AND_NOTIFIED):
                return True
            self._state = _CANCELLED
            self._condition.notify_all()
        self._invoke_callbacks()
        return True

    def cancelled(self):
        with self._condition:
            return self._state in (_CANCELLED, _CANCELLED_AND_NOTIFIED)

    def running(self):
        with self._condition:
            return self._state == _RUNNING

    def done(self):
        with self._condition:
            return self._state in _DONE_STATES

    # -- result retrieval ---------------------------------------------------
    def _get_result(self):
        if self._state in (_CANCELLED, _CANCELLED_AND_NOTIFIED):
            raise CancelledError()
        if self._exception is not None:
            raise self._exception
        return self._result

    def result(self, timeout=None):
        with self._condition:
            if self._state in _DONE_STATES:
                return self._get_result()
            self._condition.wait(timeout)
            if self._state in _DONE_STATES:
                return self._get_result()
            raise TimeoutError()

    def exception(self, timeout=None):
        with self._condition:
            if self._state in (_CANCELLED, _CANCELLED_AND_NOTIFIED):
                raise CancelledError()
            if self._state == _FINISHED:
                return self._exception
            self._condition.wait(timeout)
            if self._state in (_CANCELLED, _CANCELLED_AND_NOTIFIED):
                raise CancelledError()
            if self._state == _FINISHED:
                return self._exception
            raise TimeoutError()

    # -- callbacks ----------------------------------------------------------
    def add_done_callback(self, fn):
        with self._condition:
            if self._state not in _DONE_STATES:
                self._done_callbacks.append(fn)
                return
        try:
            fn(self)
        except Exception:
            pass

    def _invoke_callbacks(self):
        for cb in list(self._done_callbacks):
            try:
                cb(self)
            except Exception:
                pass
        self._done_callbacks = []

    # -- producer-side API --------------------------------------------------
    def set_running_or_notify_cancel(self):
        with self._condition:
            if self._state == _CANCELLED:
                self._state = _CANCELLED_AND_NOTIFIED
                for waiter in self._waiters:
                    waiter.add_cancelled(self)
                return False
            if self._state == _PENDING:
                self._state = _RUNNING
                return True
            raise InvalidStateError(
                "Future in unexpected state: %s" % self._state
            )

    def set_result(self, result):
        with self._condition:
            if self._state in _DONE_STATES:
                raise InvalidStateError(
                    "set_result on a finished future"
                )
            self._result = result
            self._state = _FINISHED
            for waiter in self._waiters:
                waiter.add_result(self)
            self._condition.notify_all()
        self._invoke_callbacks()

    def set_exception(self, exception):
        with self._condition:
            if self._state in _DONE_STATES:
                raise InvalidStateError(
                    "set_exception on a finished future"
                )
            self._exception = exception
            self._state = _FINISHED
            for waiter in self._waiters:
                waiter.add_exception(self)
            self._condition.notify_all()
        self._invoke_callbacks()


# ---------------------------------------------------------------------------
# Waiter — used by as_completed / wait
# ---------------------------------------------------------------------------
class _Waiter(object):
    def __init__(self):
        self.event = threading.Event()
        self.finished_futures = []

    def add_result(self, future):
        self.finished_futures.append(future)
        self.event.set()

    def add_exception(self, future):
        self.finished_futures.append(future)
        self.event.set()

    def add_cancelled(self, future):
        self.finished_futures.append(future)
        self.event.set()


def _create_and_install_waiters(fs):
    waiter = _Waiter()
    for f in fs:
        with f._condition:
            f._waiters.append(waiter)
    return waiter


def _yield_finished_futures(fs, waiter, ref_collect):
    while fs:
        f = fs[-1]
        for collection in ref_collect:
            collection.remove(f)
        fs.pop()
        with f._condition:
            f._waiters.remove(waiter)
        del f
        yield


# ---------------------------------------------------------------------------
# as_completed
# ---------------------------------------------------------------------------
def as_completed(fs, timeout=None):
    """Yield futures from ``fs`` as they complete."""
    if timeout is not None:
        end_time = timeout + time.monotonic()

    fs = set(fs)
    total_futures = len(fs)
    with _AcquireFutures(fs):
        finished = set(
            f for f in fs if f._state in _DONE_STATES
        )
        pending = fs - finished
        waiter = _create_and_install_waiters(pending)
    finished = list(finished)
    try:
        for future in finished:
            yield future

        while pending:
            if timeout is None:
                wait_timeout = None
            else:
                wait_timeout = end_time - time.monotonic()
                if wait_timeout < 0:
                    raise TimeoutError(
                        "%d (of %d) futures unfinished"
                        % (len(pending), total_futures)
                    )

            waiter.event.wait(wait_timeout)

            with waiter.event._cond if hasattr(waiter.event, "_cond") else threading.Lock():
                pass

            # Drain finished futures from the waiter under a simple lock.
            with _waiter_lock:
                finished_now = list(waiter.finished_futures)
                waiter.finished_futures = []
                waiter.event.clear()

            for future in finished_now:
                yield future
                pending.discard(future)
    finally:
        for f in fs:
            with f._condition:
                if waiter in f._waiters:
                    f._waiters.remove(waiter)


_waiter_lock = threading.Lock()


class _AcquireFutures(object):
    """Context manager that acquires the locks on a sequence of futures."""

    def __init__(self, futures):
        # Sort by id so locking order is stable across threads.
        self.futures = sorted(futures, key=id)

    def __enter__(self):
        for future in self.futures:
            future._condition.acquire()

    def __exit__(self, *args):
        for future in self.futures:
            future._condition.release()


# ---------------------------------------------------------------------------
# Executor base class
# ---------------------------------------------------------------------------
class Executor(object):
    """Abstract base for asynchronous executors."""

    def submit(self, fn, *args, **kwargs):
        raise NotImplementedError()

    def map(self, fn, *iterables, timeout=None, chunksize=1):
        if timeout is not None:
            end_time = timeout + time.monotonic()

        fs = [self.submit(fn, *args) for args in zip(*iterables)]

        def result_iterator():
            try:
                fs.reverse()
                while fs:
                    if timeout is None:
                        yield fs.pop().result()
                    else:
                        yield fs.pop().result(end_time - time.monotonic())
            finally:
                for future in fs:
                    future.cancel()

        return result_iterator()

    def shutdown(self, wait=True):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)
        return False


# ---------------------------------------------------------------------------
# ThreadPoolExecutor
# ---------------------------------------------------------------------------
class _WorkItem(object):
    __slots__ = ("future", "fn", "args", "kwargs")

    def __init__(self, future, fn, args, kwargs):
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        if not self.future.set_running_or_notify_cancel():
            return
        try:
            result = self.fn(*self.args, **self.kwargs)
        except BaseException as exc:
            self.future.set_exception(exc)
        else:
            self.future.set_result(result)


class _SimpleQueue(object):
    """Tiny thread-safe FIFO used by the executor (no stdlib queue import)."""

    def __init__(self):
        self._items = []
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def put(self, item):
        with self._not_empty:
            self._items.append(item)
            self._not_empty.notify()

    def get(self):
        with self._not_empty:
            while not self._items:
                self._not_empty.wait()
            return self._items.pop(0)


class ThreadPoolExecutor(Executor):
    _counter = itertools.count().__next__

    def __init__(self, max_workers=None, thread_name_prefix=""):
        if max_workers is None:
            max_workers = 4
        if max_workers <= 0:
            raise ValueError("max_workers must be > 0")
        self._max_workers = max_workers
        self._thread_name_prefix = thread_name_prefix or (
            "ThreadPoolExecutor-%d" % ThreadPoolExecutor._counter()
        )
        self._work_queue = _SimpleQueue()
        self._threads = set()
        self._shutdown = False
        self._shutdown_lock = threading.Lock()

    def submit(self, fn, *args, **kwargs):
        with self._shutdown_lock:
            if self._shutdown:
                raise RuntimeError("cannot schedule after shutdown")
            f = Future()
            w = _WorkItem(f, fn, args, kwargs)
            self._work_queue.put(w)
            self._adjust_thread_count()
            return f

    def _adjust_thread_count(self):
        if len(self._threads) < self._max_workers:
            t = threading.Thread(
                target=self._worker,
                name="%s_%d" % (self._thread_name_prefix, len(self._threads)),
            )
            t.daemon = True
            t.start()
            self._threads.add(t)

    def _worker(self):
        try:
            while True:
                work_item = self._work_queue.get()
                if work_item is None:
                    # Shutdown sentinel — re-broadcast and exit.
                    self._work_queue.put(None)
                    return
                work_item.run()
                del work_item
        except BaseException:
            return

    def shutdown(self, wait=True):
        with self._shutdown_lock:
            self._shutdown = True
            self._work_queue.put(None)
        if wait:
            for t in list(self._threads):
                t.join()


# ---------------------------------------------------------------------------
# wait()
# ---------------------------------------------------------------------------
FIRST_COMPLETED = "FIRST_COMPLETED"
FIRST_EXCEPTION = "FIRST_EXCEPTION"
ALL_COMPLETED = "ALL_COMPLETED"


class DoneAndNotDoneFutures(tuple):
    """Result of :func:`wait`."""

    __slots__ = ()

    def __new__(cls, done, not_done):
        obj = super().__new__(cls, (done, not_done))
        return obj

    @property
    def done(self):
        return self[0]

    @property
    def not_done(self):
        return self[1]


def wait(fs, timeout=None, return_when=ALL_COMPLETED):
    fs = set(fs)
    with _AcquireFutures(fs):
        done = set(f for f in fs if f._state in _DONE_STATES)
        not_done = fs - done

        if return_when == FIRST_COMPLETED and done:
            return DoneAndNotDoneFutures(done, not_done)
        if return_when == FIRST_EXCEPTION and any(
            f._exception is not None or f._state in (_CANCELLED, _CANCELLED_AND_NOTIFIED)
            for f in done
        ):
            return DoneAndNotDoneFutures(done, not_done)
        if return_when == ALL_COMPLETED and not not_done:
            return DoneAndNotDoneFutures(done, not_done)

        waiter = _create_and_install_waiters(not_done)

    try:
        waiter.event.wait(timeout)
    finally:
        for f in fs:
            with f._condition:
                if waiter in f._waiters:
                    f._waiters.remove(waiter)

    done = set(f for f in fs if f._state in _DONE_STATES)
    not_done = fs - done
    return DoneAndNotDoneFutures(done, not_done)


# ---------------------------------------------------------------------------
# Required invariant probes
# ---------------------------------------------------------------------------
def futures2_executor():
    """Invariant: confirms an Executor type is exposed and usable."""
    return (
        isinstance(Executor, type)
        and issubclass(ThreadPoolExecutor, Executor)
        and callable(getattr(ThreadPoolExecutor, "submit", None))
    )


def futures2_future():
    """Invariant: confirms a Future type is exposed and usable."""
    f = Future()
    if f.done():
        return False
    f.set_result(123)
    return f.done() and f.result() == 123


def futures2_as_completed():
    """Invariant: confirms as_completed yields finished futures."""
    a = Future()
    b = Future()
    a.set_result("a")
    b.set_result("b")
    seen = []
    for fut in as_completed([a, b]):
        seen.append(fut.result())
    return sorted(seen) == ["a", "b"]


__all__ = [
    "Future",
    "Executor",
    "ThreadPoolExecutor",
    "as_completed",
    "wait",
    "CancelledError",
    "TimeoutError",
    "InvalidStateError",
    "FIRST_COMPLETED",
    "FIRST_EXCEPTION",
    "ALL_COMPLETED",
    "DoneAndNotDoneFutures",
    "futures2_executor",
    "futures2_future",
    "futures2_as_completed",
]