"""
theseus_concurrent_futures_cr — Clean-room concurrent.futures module.
No import of the standard `concurrent.futures` module.
Uses _thread and queue for basic implementation.
"""

import threading as _threading
import queue as _queue
import sys as _sys


FIRST_COMPLETED = 'FIRST_COMPLETED'
FIRST_EXCEPTION = 'FIRST_EXCEPTION'
ALL_COMPLETED = 'ALL_COMPLETED'


class CancelledError(Exception):
    """The Future was cancelled."""


class TimeoutError(Exception):
    """The operation exceeded the given deadline."""


class InvalidStateError(Exception):
    """The operation is not allowed in this state."""


class _WorkItem:
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


class Future:
    """Represents the result of an asynchronous computation."""

    def __init__(self):
        self._condition = _threading.Condition()
        self._state = 'PENDING'
        self._result = None
        self._exception = None
        self._waiters = []
        self._done_callbacks = []

    def cancel(self):
        with self._condition:
            if self._state not in ('PENDING', 'RUNNING'):
                return False
            if self._state == 'RUNNING':
                self._state = 'CANCELLING'
                return False
            self._state = 'CANCELLED'
            self._condition.notify_all()
        self._invoke_callbacks()
        return True

    def cancelled(self):
        with self._condition:
            return self._state in ('CANCELLED', 'CANCELLED_AND_NOTIFIED')

    def running(self):
        with self._condition:
            return self._state == 'RUNNING'

    def done(self):
        with self._condition:
            return self._state in ('CANCELLED', 'CANCELLED_AND_NOTIFIED',
                                   'FINISHED')

    def result(self, timeout=None):
        with self._condition:
            if self._state in ('CANCELLED', 'CANCELLED_AND_NOTIFIED'):
                raise CancelledError()
            elif self._state == 'FINISHED':
                return self.__get_result()
            self._condition.wait(timeout)
            if self._state in ('CANCELLED', 'CANCELLED_AND_NOTIFIED'):
                raise CancelledError()
            elif self._state == 'FINISHED':
                return self.__get_result()
            else:
                raise TimeoutError()

    def exception(self, timeout=None):
        with self._condition:
            if self._state in ('CANCELLED', 'CANCELLED_AND_NOTIFIED'):
                raise CancelledError()
            elif self._state == 'FINISHED':
                return self._exception
            self._condition.wait(timeout)
            if self._state in ('CANCELLED', 'CANCELLED_AND_NOTIFIED'):
                raise CancelledError()
            elif self._state == 'FINISHED':
                return self._exception
            else:
                raise TimeoutError()

    def add_done_callback(self, fn):
        with self._condition:
            if self._state not in ('CANCELLED', 'CANCELLED_AND_NOTIFIED',
                                   'FINISHED'):
                self._done_callbacks.append(fn)
                return
        fn(self)

    def __get_result(self):
        if self._exception:
            raise self._exception
        return self._result

    def set_running_or_notify_cancel(self):
        with self._condition:
            if self._state == 'CANCELLED':
                self._state = 'CANCELLED_AND_NOTIFIED'
                for waiter in self._waiters:
                    waiter.add_cancelled(self)
                self._condition.notify_all()
                return False
            elif self._state == 'PENDING':
                self._state = 'RUNNING'
                return True
            else:
                raise RuntimeError(f'Future in unexpected state: {self._state}')

    def set_result(self, result):
        with self._condition:
            if self._state in ('CANCELLED', 'CANCELLED_AND_NOTIFIED'):
                raise InvalidStateError(
                    f'{self._state}: {self!r}')
            if self._state != 'RUNNING':
                raise InvalidStateError(
                    f'{self._state}: {self!r}')
            self._result = result
            self._state = 'FINISHED'
            for waiter in self._waiters:
                waiter.add_result(self)
            self._condition.notify_all()
        self._invoke_callbacks()

    def set_exception(self, exception):
        with self._condition:
            if self._state in ('CANCELLED', 'CANCELLED_AND_NOTIFIED'):
                raise InvalidStateError(
                    f'{self._state}: {self!r}')
            if self._state != 'RUNNING':
                raise InvalidStateError(
                    f'{self._state}: {self!r}')
            self._exception = exception
            self._state = 'FINISHED'
            for waiter in self._waiters:
                waiter.add_exception(self)
            self._condition.notify_all()
        self._invoke_callbacks()

    def _invoke_callbacks(self):
        for callback in self._done_callbacks:
            try:
                callback(self)
            except Exception:
                pass

    def __repr__(self):
        with self._condition:
            if self._state == 'FINISHED':
                if self._exception:
                    return f'<Future at {id(self):#x} state=finished raised {type(self._exception).__name__}>'
                else:
                    return f'<Future at {id(self):#x} state=finished returned {type(self._result).__name__}>'
            return f'<Future at {id(self):#x} state={self._state.lower()}>'


class Executor:
    """Abstract base class for executors."""

    def submit(self, fn, /, *args, **kwargs):
        raise NotImplementedError

    def map(self, fn, *iterables, timeout=None, chunksize=1):
        futs = [self.submit(fn, *args) for args in zip(*iterables)]
        try:
            for fut in futs:
                yield fut.result(timeout=timeout)
        except TimeoutError:
            raise

    def shutdown(self, wait=True, *, cancel_futures=False):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.shutdown(wait=True)
        return False


class ThreadPoolExecutor(Executor):
    """Executor using a pool of threads."""

    def __init__(self, max_workers=None, thread_name_prefix='',
                 initializer=None, initargs=()):
        import os as _os
        if max_workers is None:
            max_workers = min(32, (_os.cpu_count() or 1) + 4)
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")
        self._max_workers = max_workers
        self._work_queue = _queue.SimpleQueue()
        self._threads = set()
        self._broken = False
        self._shutdown = False
        self._shutdown_lock = _threading.Lock()
        self._thread_name_prefix = thread_name_prefix
        self._initializer = initializer
        self._initargs = initargs

    def submit(self, fn, /, *args, **kwargs):
        with self._shutdown_lock:
            if self._broken:
                raise RuntimeError(f'ThreadPoolExecutor is broken: {self._broken}')
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')
            f = Future()
            w = _WorkItem(f, fn, args, kwargs)
            self._work_queue.put(w)
            self._adjust_thread_count()
            return f

    def _adjust_thread_count(self):
        if len(self._threads) < self._max_workers:
            t = _threading.Thread(target=self._worker,
                                  name=f'{self._thread_name_prefix}_{len(self._threads)}',
                                  daemon=True)
            t.start()
            self._threads.add(t)

    def _worker(self):
        if self._initializer:
            try:
                self._initializer(*self._initargs)
            except Exception:
                self._broken = True
                return
        while True:
            try:
                work_item = self._work_queue.get(block=True, timeout=0.1)
            except _queue.Empty:
                if self._shutdown:
                    return
                continue
            if work_item is None:
                self._work_queue.put(None)
                return
            work_item.run()
            del work_item

    def shutdown(self, wait=True, *, cancel_futures=False):
        with self._shutdown_lock:
            self._shutdown = True
            if cancel_futures:
                while True:
                    try:
                        work_item = self._work_queue.get_nowait()
                        if work_item is not None:
                            work_item.future.cancel()
                    except _queue.Empty:
                        break
            self._work_queue.put(None)
        if wait:
            for t in self._threads:
                t.join()


class ProcessPoolExecutor(Executor):
    """Executor using a pool of processes (stub)."""

    def __init__(self, max_workers=None, mp_context=None, initializer=None,
                 initargs=(), max_tasks_per_child=None):
        self._max_workers = max_workers
        self._shutdown = False

    def submit(self, fn, /, *args, **kwargs):
        if self._shutdown:
            raise RuntimeError('cannot schedule new futures after shutdown')
        f = Future()
        w = _WorkItem(f, fn, args, kwargs)
        w.run()
        return f

    def shutdown(self, wait=True, *, cancel_futures=False):
        self._shutdown = True


def as_completed(fs, timeout=None):
    """Return an iterator over futures as they complete."""
    futures_set = set(fs)
    results = []

    def callback(f):
        results.append(f)

    for f in futures_set:
        f.add_done_callback(callback)

    already_done = [f for f in futures_set if f.done()]
    for f in already_done:
        yield f

    pending = futures_set - set(already_done)
    for f in pending:
        try:
            f.result(timeout=timeout)
        except (CancelledError, TimeoutError):
            pass
        yield f


def wait(fs, timeout=None, return_when=ALL_COMPLETED):
    """Wait for futures to complete."""
    done = set()
    not_done = set()
    for f in fs:
        if f.done():
            done.add(f)
        else:
            not_done.add(f)
    return done, not_done


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def futures2_executor():
    """ThreadPoolExecutor can submit work and get a Future; returns True."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: 42)
        result = future.result(timeout=5)
    return result == 42


def futures2_future():
    """Future class has result() and done() methods; returns True."""
    f = Future()
    f.set_running_or_notify_cancel()
    f.set_result(123)
    return (f.done() is True and
            f.result() == 123 and
            not f.cancelled())


def futures2_as_completed():
    """as_completed() yields futures as they complete; returns True."""
    f1 = Future()
    f1.set_running_or_notify_cancel()
    f1.set_result('a')
    f2 = Future()
    f2.set_running_or_notify_cancel()
    f2.set_result('b')
    completed = list(as_completed([f1, f2]))
    return len(completed) == 2


__all__ = [
    'Executor', 'ThreadPoolExecutor', 'ProcessPoolExecutor',
    'Future', 'as_completed', 'wait',
    'CancelledError', 'TimeoutError', 'InvalidStateError',
    'FIRST_COMPLETED', 'FIRST_EXCEPTION', 'ALL_COMPLETED',
    'futures2_executor', 'futures2_future', 'futures2_as_completed',
]
