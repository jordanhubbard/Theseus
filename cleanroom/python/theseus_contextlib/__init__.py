"""
theseus_contextlib - Clean-room implementation of contextlib utilities.
"""

import functools


class _GeneratorContextManager:
    """Context manager wrapping a generator function."""

    def __init__(self, func, args, kwargs):
        self._gen = func(*args, **kwargs)
        functools.update_wrapper(self, func)

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
    """Decorator that turns a generator function into a context manager."""
    @functools.wraps(func)
    def helper(*args, **kwargs):
        return _GeneratorContextManager(func, args, kwargs)
    return helper


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


class closing:
    """Context manager that calls thing.close() on exit."""

    def __init__(self, thing):
        self.thing = thing

    def __enter__(self):
        return self.thing

    def __exit__(self, *exc_info):
        self.thing.close()
        return False


class nullcontext:
    """Context manager that does nothing, returning the enter_result."""

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *exc_info):
        return False


# --- Invariant test functions ---

def contextlib_suppress():
    """Test that suppress(ZeroDivisionError) does not raise."""
    try:
        with suppress(ZeroDivisionError):
            x = 1 / 0
        return True
    except ZeroDivisionError:
        return False


def contextlib_contextmanager():
    """Test that @contextmanager works correctly."""
    @contextmanager
    def my_ctx():
        yield "entered"

    with my_ctx() as val:
        return val


def contextlib_nullcontext():
    """Test that nullcontext passes through its enter value."""
    with nullcontext(42) as val:
        return val