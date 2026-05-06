"""Clean-room implementation of contextlib (theseus_contextlib_cr).

Provides:
  - contextmanager: decorator to create context managers from generators
  - closing: context manager that calls .close() on exit
  - suppress: context manager to suppress specified exceptions
  - nullcontext: context manager that does nothing
"""

import sys as _sys
from functools import wraps as _wraps


class AbstractContextManager:
    """Abstract base class for context managers."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None


class _GeneratorContextManager(AbstractContextManager):
    """Helper class that turns a generator into a context manager."""

    def __init__(self, func, args, kwds):
        self.gen = func(*args, **kwds)
        self.func = func
        self.args = args
        self.kwds = kwds
        # Preserve the docstring so wrapping behaves nicely.
        doc = getattr(func, "__doc__", None)
        if doc is None:
            doc = type(self).__doc__
        self.__doc__ = doc

    def _recreate_cm(self):
        # Allow re-entry by recreating the underlying generator.
        return self.__class__(self.func, self.args, self.kwds)

    def __enter__(self):
        try:
            return next(self.gen)
        except StopIteration:
            raise RuntimeError("generator didn't yield") from None

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            try:
                next(self.gen)
            except StopIteration:
                return False
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if exc_value is None:
                # Need to force instantiation so we can reliably
                # tell if we get the same exception back.
                exc_value = exc_type()
            try:
                self.gen.throw(exc_type, exc_value, traceback)
            except StopIteration as exc:
                # Suppress StopIteration unless it's the same exception
                # that was passed in.
                return exc is not exc_value
            except RuntimeError as exc:
                # Don't re-raise the passed in exception. (issue27122)
                if exc is exc_value:
                    return False
                # Likely a StopIteration -> RuntimeError conversion
                # introduced by PEP 479; check the cause.
                if (
                    isinstance(exc_value, StopIteration)
                    and exc.__cause__ is exc_value
                ):
                    return False
                raise
            except BaseException as exc:
                # Only re-raise if it's *not* the exception that was
                # passed to throw(); in that case re-raising will
                # produce a "double exception" traceback so we just
                # return False to indicate the exception isn't handled.
                if exc is not exc_value:
                    raise
                return False
            raise RuntimeError("generator didn't stop after throw()")


def contextmanager(func):
    """Decorator to create a context manager from a generator function.

    The generator must yield exactly once. The code before the yield is
    treated as __enter__, and the code after the yield as __exit__.
    """

    @_wraps(func)
    def helper(*args, **kwds):
        return _GeneratorContextManager(func, args, kwds)

    return helper


class closing(AbstractContextManager):
    """Context manager that automatically calls .close() on the wrapped
    object when the with block exits.

    Example:
        with closing(open('file')) as f:
            ...
    """

    def __init__(self, thing):
        self.thing = thing

    def __enter__(self):
        return self.thing

    def __exit__(self, exc_type, exc_value, traceback):
        self.thing.close()
        return None


class suppress(AbstractContextManager):
    """Context manager that suppresses any of the specified exceptions
    if they occur in the body of a with statement.

    Example:
        with suppress(FileNotFoundError):
            os.remove('somefile.tmp')
    """

    def __init__(self, *exceptions):
        self._exceptions = exceptions

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            return False
        # issubclass returns True for the exact match too.
        return issubclass(exc_type, self._exceptions)


class nullcontext(AbstractContextManager):
    """Context manager that does nothing.

    Optionally returns the supplied enter_result from __enter__.
    """

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, exc_type, exc_value, traceback):
        return None


# Helpers used by the invariant probes (mirroring the names contextlib2
# style probes look for).
def contextlib2_contextmanager():
    """Verify that contextmanager works correctly."""
    entered = []
    exited = []

    @contextmanager
    def cm():
        entered.append(True)
        try:
            yield 42
        finally:
            exited.append(True)

    with cm() as value:
        if value != 42:
            return False
    if not entered or not exited:
        return False

    # Check exception propagation.
    @contextmanager
    def cm2():
        try:
            yield
        except ValueError:
            # Suppress ValueError.
            pass

    try:
        with cm2():
            raise ValueError("ignored")
    except ValueError:
        return False

    # Check that other exceptions propagate.
    @contextmanager
    def cm3():
        yield

    try:
        with cm3():
            raise RuntimeError("propagate")
    except RuntimeError:
        return True
    return False


def contextlib2_suppress():
    """Verify that suppress works correctly."""
    # Should suppress matching exception.
    with suppress(ValueError):
        raise ValueError("boom")

    # Should suppress subclass.
    class MyError(ValueError):
        pass

    with suppress(ValueError):
        raise MyError("boom")

    # Should propagate non-matching exception.
    try:
        with suppress(ValueError):
            raise TypeError("boom")
    except TypeError:
        pass
    else:
        return False

    # No exception should be a no-op.
    with suppress(ValueError):
        pass

    return True


def contextlib2_closing():
    """Verify that closing works correctly."""

    class Resource:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    r = Resource()
    with closing(r) as obj:
        if obj is not r:
            return False
        if r.closed:
            return False
    if not r.closed:
        return False

    # closing should call .close even if an exception occurs.
    r2 = Resource()
    try:
        with closing(r2):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    if not r2.closed:
        return False

    return True


__all__ = [
    "AbstractContextManager",
    "contextmanager",
    "closing",
    "suppress",
    "nullcontext",
    "contextlib2_contextmanager",
    "contextlib2_suppress",
    "contextlib2_closing",
]