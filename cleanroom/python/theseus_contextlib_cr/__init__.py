"""
theseus_contextlib_cr — Clean-room contextlib module.
No import of the standard `contextlib` module.
"""

import functools as _functools


class _GeneratorContextManager:
    """Context manager wrapping a generator function."""

    def __init__(self, func, args, kwargs):
        self._gen = func(*args, **kwargs)
        self._func = func

    def __enter__(self):
        try:
            return next(self._gen)
        except StopIteration:
            raise RuntimeError("generator didn't yield") from None

    def __exit__(self, typ, value, traceback):
        if typ is None:
            try:
                next(self._gen)
            except StopIteration:
                return False
            raise RuntimeError("generator didn't stop")
        else:
            try:
                self._gen.throw(typ, value, traceback)
            except StopIteration as exc:
                return exc is not value
            except RuntimeError as exc:
                if exc is value:
                    return False
                if isinstance(value, (StopIteration, RuntimeError)):
                    if exc.__cause__ is value:
                        return False
                raise
            except BaseException as exc:
                if exc is not value:
                    raise
                return False
            raise RuntimeError("generator didn't stop after throw()")


def contextmanager(func):
    """Decorator to make a generator-based context manager."""
    @_functools.wraps(func)
    def helper(*args, **kwargs):
        return _GeneratorContextManager(func, args, kwargs)
    return helper


class closing:
    """Context manager that calls close() on exit."""

    def __init__(self, thing):
        self.thing = thing

    def __enter__(self):
        return self.thing

    def __exit__(self, *exc_info):
        self.thing.close()
        return False


class suppress:
    """Context manager to suppress specified exceptions."""

    def __init__(self, *exceptions):
        self._exceptions = exceptions

    def __enter__(self):
        pass

    def __exit__(self, exctype, excinst, exctb):
        return exctype is not None and issubclass(exctype, self._exceptions)


class nullcontext:
    """Context manager that does nothing."""

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *exc_info):
        return False


class AbstractContextManager:
    """Abstract base for context managers."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None


class ExitStack:
    """Context manager for managing dynamic callbacks on exit."""

    def __init__(self):
        self._exit_callbacks = []

    def enter_context(self, cm):
        result = cm.__enter__()
        self._exit_callbacks.append(cm.__exit__)
        return result

    def callback(self, callback, /, *args, **kwargs):
        def _exit(exc_type, exc, tb):
            callback(*args, **kwargs)
        self._exit_callbacks.append(_exit)

    def push(self, exit_fn):
        self._exit_callbacks.append(exit_fn)
        return exit_fn

    def pop_all(self):
        new_stack = ExitStack()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = []
        return new_stack

    def close(self):
        self.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        suppressed_exc = False
        pending_raise = False
        frame_exc = exc_details[1]

        def _fix_exception_context(new_exc, old_exc):
            while 1:
                exc_context = new_exc.__context__
                if exc_context is None or exc_context is old_exc:
                    return
                new_exc = exc_context

        for cb in reversed(self._exit_callbacks):
            try:
                if cb(*exc_details):
                    suppressed_exc = True
                    pending_raise = False
                    exc_details = (None, None, None)
            except Exception as exc:
                new_exc_details = type(exc), exc, exc.__traceback__
                pending_raise = True
                exc_details = new_exc_details

        if pending_raise:
            raise exc_details[1]
        return suppressed_exc and not pending_raise


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def contextlib2_contextmanager():
    """contextmanager-decorated generator works as context manager; returns True."""
    results = []

    @contextmanager
    def managed():
        results.append('enter')
        yield 42
        results.append('exit')

    with managed() as val:
        results.append(val)

    return results == ['enter', 42, 'exit']


def contextlib2_suppress():
    """suppress(ValueError) swallows ValueError without reraise; returns True."""
    caught = False
    with suppress(ValueError):
        raise ValueError("ignored")
        caught = True  # unreachable
    return not caught


def contextlib2_closing():
    """closing() calls .close() on exit; returns True."""
    class Resource:
        def __init__(self):
            self.closed = False
        def close(self):
            self.closed = True

    r = Resource()
    with closing(r):
        pass
    return r.closed


__all__ = [
    'contextmanager', 'closing', 'suppress', 'nullcontext',
    'AbstractContextManager', 'ExitStack',
    'contextlib2_contextmanager', 'contextlib2_suppress', 'contextlib2_closing',
]
