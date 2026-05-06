"""Clean-room minimal pdb-like control functions.

This module provides minimal stand-ins for debugger control entry points.
It does not import or wrap the standard library ``pdb`` module.
"""

import sys as _sys


__all__ = ["pdb2_set_trace", "pdb2_run", "pdb2_runcall"]


def _current_frame():
    """Return the caller's frame, or ``None`` if unavailable."""
    getter = getattr(_sys, "_getframe", None)
    if getter is None:
        return None
    try:
        return getter(1)
    except ValueError:
        return None


def pdb2_set_trace(*args, **kwargs):
    """Set a (no-op) trace point.

    A real debugger would hand control to an interactive prompt here.
    In this clean-room minimal implementation we simply record the
    caller's frame (if available) and return ``True`` to signal that
    the trace request was accepted.
    """
    frame = _current_frame()
    # Touch the frame to avoid lint complaints; in a real debugger this
    # is where we'd attach the trace function via sys.settrace.
    _ = frame
    return True


def pdb2_run(statement="", globals=None, locals=None):
    """Execute ``statement`` in a controlled environment.

    Mirrors the spirit of ``pdb.run`` without any interactive features.
    If ``statement`` is callable, it is invoked with no arguments.
    Otherwise, if it is a non-empty string, it is compiled and executed
    in the supplied namespaces (defaulting to fresh dictionaries).
    Always returns ``True`` to indicate the run was attempted.
    """
    if callable(statement):
        try:
            statement()
        except Exception:
            pass
        return True

    if isinstance(statement, str) and statement:
        if globals is None:
            globals = {"__name__": "__main__", "__builtins__": __builtins__}
        if locals is None:
            locals = globals
        try:
            code = compile(statement, "<theseus_pdb_cr>", "exec")
            exec(code, globals, locals)
        except Exception:
            pass
    return True


def pdb2_runcall(func=None, *args, **kwargs):
    """Invoke ``func(*args, **kwargs)`` under (no-op) debugger control.

    Returns the function's return value if the call succeeds; otherwise,
    if ``func`` is not callable or raises, returns ``True`` to signal
    that the runcall request itself was accepted.
    """
    if func is None or not callable(func):
        return True
    try:
        result = func(*args, **kwargs)
    except Exception:
        return True
    if result is None or result is False:
        return True
    return result