import sys


class suppress:
    """Context manager that suppresses specified exceptions."""
    
    def __init__(self, *exceptions):
        self._exceptions = exceptions
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False
        return issubclass(exc_type, self._exceptions)


class redirect_stdout:
    """Context manager that redirects sys.stdout to new_target."""
    
    def __init__(self, new_target):
        self._new_target = new_target
        self._old_target = None
    
    def __enter__(self):
        self._old_target = sys.stdout
        sys.stdout = self._new_target
        return self._new_target
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._old_target
        return False


class redirect_stderr:
    """Context manager that redirects sys.stderr to new_target."""
    
    def __init__(self, new_target):
        self._new_target = new_target
        self._old_target = None
    
    def __enter__(self):
        self._old_target = sys.stderr
        sys.stderr = self._new_target
        return self._new_target
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr = self._old_target
        return False


class ExitStack:
    """Context manager for dynamically assembling context managers and callbacks."""
    
    def __init__(self):
        self._exit_callbacks = []
    
    def _push_cm_exit(self, cm, cm_exit):
        """Helper to push a context manager's __exit__ method."""
        def _exit_wrapper(exc_type, exc, tb):
            return cm_exit(exc_type, exc, tb)
        self._exit_callbacks.append(_exit_wrapper)
    
    def enter_context(self, cm):
        """Enter a context manager and register its __exit__ for cleanup."""
        result = cm.__enter__()
        self._push_cm_exit(cm, cm.__exit__)
        return result
    
    def callback(self, func, *args, **kwargs):
        """Register a callback to be called on exit."""
        def _callback_wrapper(exc_type, exc, tb):
            func(*args, **kwargs)
            return False
        self._exit_callbacks.append(_callback_wrapper)
        return func
    
    def push(self, exit_func):
        """Register an exit callback directly."""
        self._exit_callbacks.append(exit_func)
        return exit_func
    
    def pop_all(self):
        """Transfer all callbacks to a new ExitStack."""
        new_stack = ExitStack()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = []
        return new_stack
    
    def close(self):
        """Immediately unwind the context stack."""
        self.__exit__(None, None, None)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Run callbacks in LIFO order
        suppressed = False
        pending_raise = False
        
        # We need to handle exceptions carefully
        # Process callbacks in reverse order
        callbacks = list(reversed(self._exit_callbacks))
        self._exit_callbacks = []
        
        current_exc = (exc_type, exc_val, exc_tb)
        
        for cb in callbacks:
            try:
                if cb(*current_exc):
                    # This callback suppressed the exception
                    suppressed = True
                    current_exc = (None, None, None)
            except Exception:
                # New exception raised by callback
                import sys as _sys
                new_exc_info = _sys.exc_info()
                current_exc = new_exc_info
                suppressed = False
        
        # If we started with an exception and it's now suppressed
        if exc_type is not None and current_exc == (None, None, None):
            return True
        
        # If a new exception was raised during cleanup, re-raise it
        if current_exc[0] is not None and current_exc[0] is not exc_type:
            raise current_exc[1].with_traceback(current_exc[2])
        
        return suppressed


def contextlib2_suppress_works():
    """suppress(ValueError) catches ValueError, returns True."""
    try:
        with suppress(ValueError):
            raise ValueError("test")
        return True
    except ValueError:
        return False


def contextlib2_suppress_reraises():
    """suppress(TypeError) does NOT suppress ValueError."""
    try:
        with suppress(TypeError):
            raise ValueError("test")
        return False
    except ValueError:
        return True


def contextlib2_exitstack():
    """ExitStack runs cleanup callbacks in LIFO order."""
    order = []
    with ExitStack() as stack:
        stack.callback(order.append, 1)
        stack.callback(order.append, 2)
    return order