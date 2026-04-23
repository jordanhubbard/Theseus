"""
theseus_asyncio_cr2 - Clean-room asyncio utilities implementation.
No import of asyncio or any third-party libraries.
"""

import inspect
import types
import threading
import collections


class InvalidStateError(Exception):
    """Raised when a Future's result is accessed before it's set."""
    pass


class CancelledError(Exception):
    """Raised when a Future is cancelled."""
    pass


class Future:
    """
    A Future represents a pending result.
    
    Attributes:
        _asyncio_future_blocking: marker attribute for isfuture() detection
    """
    
    _asyncio_future_blocking = False
    
    def __init__(self):
        self._result = None
        self._exception = None
        self._state = 'PENDING'  # PENDING, FINISHED, CANCELLED
        self._callbacks = []
        self._loop = None
    
    def set_result(self, result):
        """Set the result of the Future."""
        if self._state != 'PENDING':
            raise InvalidStateError(f"Future is in state {self._state}, cannot set result.")
        self._result = result
        self._state = 'FINISHED'
        self._schedule_callbacks()
    
    def set_exception(self, exception):
        """Set an exception on the Future."""
        if self._state != 'PENDING':
            raise InvalidStateError(f"Future is in state {self._state}, cannot set exception.")
        if isinstance(exception, type):
            exception = exception()
        self._exception = exception
        self._state = 'FINISHED'
        self._schedule_callbacks()
    
    def result(self):
        """Return the result of the Future, or raise if not yet set."""
        if self._state == 'CANCELLED':
            raise CancelledError("Future was cancelled.")
        if self._state == 'PENDING':
            raise InvalidStateError("Future result is not yet set.")
        if self._exception is not None:
            raise self._exception
        return self._result
    
    def exception(self):
        """Return the exception set on the Future, or None."""
        if self._state == 'CANCELLED':
            raise CancelledError("Future was cancelled.")
        if self._state == 'PENDING':
            raise InvalidStateError("Future result is not yet set.")
        return self._exception
    
    def cancel(self):
        """Cancel the Future."""
        if self._state != 'PENDING':
            return False
        self._state = 'CANCELLED'
        self._schedule_callbacks()
        return True
    
    def cancelled(self):
        """Return True if the Future was cancelled."""
        return self._state == 'CANCELLED'
    
    def done(self):
        """Return True if the Future is done (finished or cancelled)."""
        return self._state != 'PENDING'
    
    def add_done_callback(self, callback):
        """Add a callback to be called when the Future is done."""
        if self._state != 'PENDING':
            callback(self)
        else:
            self._callbacks.append(callback)
    
    def _schedule_callbacks(self):
        """Schedule all registered callbacks."""
        callbacks = self._callbacks[:]
        self._callbacks.clear()
        for callback in callbacks:
            try:
                callback(self)
            except Exception:
                pass
    
    def __repr__(self):
        state = self._state
        if state == 'FINISHED':
            if self._exception is not None:
                return f'<Future state={state} exception={self._exception!r}>'
            return f'<Future state={state} result={self._result!r}>'
        return f'<Future state={state}>'
    
    def __await__(self):
        """Allow Future to be awaited."""
        if not self.done():
            self._asyncio_future_blocking = True
            yield self
        if not self.done():
            raise RuntimeError("await wasn't used with future")
        return self.result()


def iscoroutine(obj):
    """
    Return True if obj is a coroutine object.
    
    Checks using inspect module's coroutine detection logic.
    """
    return inspect.iscoroutine(obj)


def isfuture(obj):
    """
    Return True if obj is a Future-like object.
    
    Checks for _asyncio_future_blocking attribute or isinstance of Future.
    """
    if isinstance(obj, Future):
        return True
    # Check for future-like objects (duck typing)
    if hasattr(obj, '_asyncio_future_blocking'):
        return True
    return False


class _EventLoop:
    """
    A simple event loop implementation.
    """
    
    def __init__(self):
        self._ready = collections.deque()
        self._running = False
        self._closed = False
    
    def run_until_complete(self, coro_or_future):
        """Run until the coroutine or future is complete."""
        if iscoroutine(coro_or_future):
            future = self._ensure_future(coro_or_future)
        elif isfuture(coro_or_future):
            future = coro_or_future
        else:
            raise TypeError(f"Expected coroutine or Future, got {type(coro_or_future)}")
        
        self._run_loop(future)
        return future.result()
    
    def _ensure_future(self, coro):
        """Wrap a coroutine in a Task (Future subclass)."""
        task = Task(coro, self)
        return task
    
    def _run_loop(self, future):
        """Run the event loop until the future is done."""
        self._running = True
        try:
            while not future.done():
                if self._ready:
                    callback = self._ready.popleft()
                    try:
                        callback()
                    except Exception:
                        pass
                else:
                    # No more callbacks but future not done - something is wrong
                    break
        finally:
            self._running = False
    
    def call_soon(self, callback, *args):
        """Schedule a callback to be called soon."""
        def _cb():
            callback(*args)
        self._ready.append(_cb)
    
    def close(self):
        """Close the event loop."""
        self._closed = True
    
    def is_running(self):
        return self._running
    
    def is_closed(self):
        return self._closed


class Task(Future):
    """
    A Task wraps a coroutine and drives it to completion.
    """
    
    def __init__(self, coro, loop):
        super().__init__()
        self._coro = coro
        self._loop = loop
        # Schedule the first step
        self._loop.call_soon(self._step)
    
    def _step(self, exc=None):
        """Advance the coroutine one step."""
        coro = self._coro
        try:
            if exc is None:
                result = coro.send(None)
            else:
                result = coro.throw(type(exc), exc, exc.__traceback__)
        except StopIteration as e:
            # Coroutine finished normally
            self.set_result(e.value)
        except CancelledError:
            self.cancel()
        except Exception as e:
            self.set_exception(e)
        else:
            # Coroutine yielded something (awaiting a future)
            if isfuture(result):
                result.add_done_callback(self._wakeup)
            else:
                # Unknown yield value, just reschedule
                self._loop.call_soon(self._step)
    
    def _wakeup(self, future):
        """Called when an awaited future completes."""
        try:
            future.result()
        except Exception as exc:
            self._loop.call_soon(self._step, exc)
        else:
            self._loop.call_soon(self._step)


# Global event loop instance
_global_loop = None
_loop_lock = threading.Lock()


def get_event_loop():
    """Get the current event loop, creating one if necessary."""
    global _global_loop
    with _loop_lock:
        if _global_loop is None or _global_loop.is_closed():
            _global_loop = _EventLoop()
        return _global_loop


def run(coro):
    """
    Run a coroutine to completion and return its result.
    
    This is the main entry point for running async code.
    """
    if not iscoroutine(coro):
        raise TypeError(f"Expected a coroutine, got {type(coro)}")
    
    loop = _EventLoop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================================
# Invariant functions (zero-arg, return hardcoded results)
# ============================================================

def asyncio2_future_result():
    """
    Invariant: f=Future(); f.set_result(42); f.result() == 42
    Returns 42.
    """
    f = Future()
    f.set_result(42)
    return f.result()


def asyncio2_iscoroutine():
    """
    Invariant: define async def coro(): pass; iscoroutine(coro()) == True
    Returns True.
    """
    async def coro():
        pass
    
    c = coro()
    result = iscoroutine(c)
    # Close the coroutine to avoid ResourceWarning
    c.close()
    return result


def asyncio2_isfuture():
    """
    Invariant: isfuture(Future()) == True
    Returns True.
    """
    return isfuture(Future())


__all__ = [
    'Future',
    'InvalidStateError',
    'CancelledError',
    'iscoroutine',
    'isfuture',
    'run',
    'get_event_loop',
    'Task',
    'asyncio2_future_result',
    'asyncio2_iscoroutine',
    'asyncio2_isfuture',
]