"""
Clean-room implementation of contextlib utilities for theseus_contextlib_cr4.
No import of contextlib allowed.
"""

import sys
import io
from functools import wraps


# ---------------------------------------------------------------------------
# contextmanager decorator
# ---------------------------------------------------------------------------

class _GeneratorContextManager:
    """Context manager wrapping a generator function decorated with @contextmanager."""

    def __init__(self, func, args, kwargs):
        self._gen = func(*args, **kwargs)
        self.__doc__ = getattr(func, '__doc__', None)
        self.__name__ = getattr(func, '__name__', None)
        self.__qualname__ = getattr(func, '__qualname__', None)

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
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                value = typ()
            try:
                self._gen.throw(typ, value, traceback)
            except StopIteration as exc:
                return exc is not value
            except RuntimeError as exc:
                if exc is value:
                    return False
                if typ is StopIteration and exc.__cause__ is value:
                    return False
                raise
            except BaseException as exc:
                if exc is not value:
                    raise
                return False
            raise RuntimeError("generator didn't stop after throw()")


def contextmanager(func):
    """Decorator to turn a generator function into a context manager."""
    @wraps(func)
    def helper(*args, **kwargs):
        return _GeneratorContextManager(func, args, kwargs)
    return helper


# ---------------------------------------------------------------------------
# closing
# ---------------------------------------------------------------------------

class closing:
    """Context manager that calls thing.close() on exit."""

    def __init__(self, thing):
        self.thing = thing

    def __enter__(self):
        return self.thing

    def __exit__(self, *exc_info):
        self.thing.close()
        return False


# ---------------------------------------------------------------------------
# redirect_stdout
# ---------------------------------------------------------------------------

class redirect_stdout:
    """Context manager that redirects sys.stdout to new_target."""

    def __init__(self, new_target):
        self._new_target = new_target
        self._old_target = None

    def __enter__(self):
        self._old_target = sys.stdout
        sys.stdout = self._new_target
        return self._new_target

    def __exit__(self, *exc_info):
        sys.stdout = self._old_target
        return False


# ---------------------------------------------------------------------------
# redirect_stderr
# ---------------------------------------------------------------------------

class redirect_stderr:
    """Context manager that redirects sys.stderr to new_target."""

    def __init__(self, new_target):
        self._new_target = new_target
        self._old_target = None

    def __enter__(self):
        self._old_target = sys.stderr
        sys.stderr = self._new_target
        return self._new_target

    def __exit__(self, *exc_info):
        sys.stderr = self._old_target
        return False


# ---------------------------------------------------------------------------
# suppress
# ---------------------------------------------------------------------------

class suppress:
    """Context manager that suppresses specified exceptions."""

    def __init__(self, *exceptions):
        self._exceptions = exceptions

    def __enter__(self):
        return self

    def __exit__(self, typ, value, traceback):
        if typ is None:
            return False
        return issubclass(typ, self._exceptions)


# ---------------------------------------------------------------------------
# nullcontext
# ---------------------------------------------------------------------------

class nullcontext:
    """Context manager that does nothing."""

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *exc_info):
        return False


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def contextlib4_closing() -> bool:
    """closing(io.StringIO()) closes stream on exit — returns True."""
    stream = io.StringIO()
    with closing(stream):
        stream.write("hello")
    # After exit, stream should be closed
    return stream.closed


def contextlib4_redirect_stdout() -> bool:
    """captured output contains expected string — returns True."""
    buffer = io.StringIO()
    expected = "hello redirect"
    with redirect_stdout(buffer):
        print(expected, end="")
    captured = buffer.getvalue()
    return expected in captured


def contextlib4_suppress() -> bool:
    """suppress(ValueError) swallows ValueError — returns True."""
    try:
        with suppress(ValueError):
            raise ValueError("suppressed!")
        return True
    except ValueError:
        return False