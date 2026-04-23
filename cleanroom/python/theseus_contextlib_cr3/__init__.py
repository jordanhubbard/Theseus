"""
Clean-room implementation of extended contextlib functionality.
No import of contextlib or any third-party libraries.
"""

import abc
import sys


class AbstractContextManager(abc.ABC):
    """Abstract base class for context managers."""

    @abc.abstractmethod
    def __enter__(self):
        return self

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        return None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractContextManager:
            if (hasattr(C, '__enter__') and hasattr(C, '__exit__')):
                return True
        return NotImplemented


class nullcontext(AbstractContextManager):
    """A context manager that does nothing and returns enter_result on __enter__."""

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, exc_type, exc_value, traceback):
        return None


class suppress(AbstractContextManager):
    """Context manager that suppresses specified exceptions."""

    def __init__(self, *exceptions):
        self._exceptions = exceptions

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and issubclass(exc_type, self._exceptions):
            return True
        return False


class ExitStack(AbstractContextManager):
    """
    Context manager that maintains a stack of cleanup callbacks.
    Callbacks are called in LIFO order on exit.
    """

    def __init__(self):
        self._exit_callbacks = []

    def enter_context(self, cm):
        """Enter a context manager and push its __exit__ onto the stack."""
        result = cm.__enter__()
        self._exit_callbacks.append(cm.__exit__)
        return result

    def callback(self, func, *args, **kwargs):
        """Register an arbitrary callback to be called on exit."""
        def _exit_wrapper(exc_type, exc_val, exc_tb):
            func(*args, **kwargs)
            return False
        self._exit_callbacks.append(_exit_wrapper)

    def push(self, exit_func):
        """Push an exit callback directly."""
        self._exit_callbacks.append(exit_func)
        return exit_func

    def pop_all(self):
        """Transfer all callbacks to a new ExitStack and return it."""
        new_stack = ExitStack()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = []
        return new_stack

    def close(self):
        """Immediately unwind the context stack."""
        self.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Call callbacks in LIFO order
        suppressed = False
        pending_raise = False

        # We need to handle exceptions carefully
        # If an exception is active, we pass it to each callback
        # If a callback returns True, the exception is suppressed
        # If a callback raises, that becomes the new exception

        current_exc = (exc_type, exc_value, traceback)

        while self._exit_callbacks:
            cb = self._exit_callbacks.pop()
            try:
                if cb(*current_exc):
                    # Exception was suppressed
                    suppressed = True
                    current_exc = (None, None, None)
                    pending_raise = False
            except Exception:
                # New exception from callback
                new_exc_info = sys.exc_info()
                current_exc = new_exc_info
                pending_raise = True
                suppressed = False

        if pending_raise:
            # Re-raise the exception from the callback
            exc = current_exc[1]
            if exc is not None:
                raise exc
            return False

        # If original exception was suppressed, return True
        if exc_type is not None and current_exc[0] is None:
            return True

        return False


# ─── Test functions ───────────────────────────────────────────────────────────

def contextlib3_exitstack():
    """Test that ExitStack can enter/exit a simple context manager."""
    results = []

    class SimpleCtx:
        def __enter__(self):
            results.append('enter')
            return self

        def __exit__(self, *args):
            results.append('exit')
            return False

    with ExitStack() as stack:
        stack.enter_context(SimpleCtx())

    return results == ['enter', 'exit']


def contextlib3_nullcontext():
    """Test that nullcontext returns the enter_result."""
    with nullcontext(42) as val:
        return val


def contextlib3_suppress():
    """Test that suppress swallows specified exceptions."""
    try:
        with suppress(ValueError):
            raise ValueError("test")
        return True
    except ValueError:
        return False