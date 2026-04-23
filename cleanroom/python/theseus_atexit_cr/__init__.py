# Clean-room implementation of atexit functionality
# No import of the original atexit module

_registry = []  # List of (fn, args, kwargs) tuples in registration order


def register(fn, *args, **kwargs):
    """Register fn to be called at interpreter exit with given args and kwargs."""
    _registry.append((fn, args, kwargs))
    return fn


def unregister(fn):
    """Remove all instances of fn from the exit handler list."""
    global _registry
    _registry = [(f, a, k) for f, a, k in _registry if f is not fn]


def _run_exitfuncs():
    """Call all registered handlers in LIFO order."""
    # Iterate in reverse order (LIFO)
    exc_info = None
    for fn, args, kwargs in reversed(_registry):
        try:
            fn(*args, **kwargs)
        except SystemExit:
            exc_info = sys.exc_info()
        except Exception:
            import sys as _sys
            exc_info = _sys.exc_info()
    if exc_info is not None:
        raise exc_info[1]


# Test helper functions as described in the spec

def atexit_register_called():
    """Register a handler, run exit funcs, return True if handler was called."""
    called = [False]

    def handler():
        called[0] = True

    # Save current registry state
    saved = list(_registry)
    _registry.clear()

    register(handler)
    _run_exitfuncs()

    result = called[0]

    # Restore registry
    _registry.clear()
    _registry.extend(saved)

    return result


def atexit_unregister():
    """Register then unregister a handler; return False if not called after _run_exitfuncs."""
    called = [False]

    def handler():
        called[0] = True

    # Save current registry state
    saved = list(_registry)
    _registry.clear()

    register(handler)
    unregister(handler)
    _run_exitfuncs()

    result = called[0]

    # Restore registry
    _registry.clear()
    _registry.extend(saved)

    return result


def atexit_lifo_order():
    """Register two handlers, run exit funcs, return order they were called."""
    order = []

    def handler1():
        order.append(1)

    def handler2():
        order.append(2)

    # Save current registry state
    saved = list(_registry)
    _registry.clear()

    register(handler1)
    register(handler2)
    _run_exitfuncs()

    result = list(order)

    # Restore registry
    _registry.clear()
    _registry.extend(saved)

    return result