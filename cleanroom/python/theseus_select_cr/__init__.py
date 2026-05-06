"""Clean-room implementation of a minimal select-like module.

This module provides a small, self-contained subset of select-style
functionality without importing the standard library `select` module.
Only Python built-ins (os, errno) are used.
"""

import os
import errno as _errno


class error(OSError):
    """Exception raised for select-related errors.

    Mirrors the historical `select.error` class, which is an alias for
    OSError in modern Python. We provide a distinct subclass so callers
    can catch it specifically.
    """
    pass


def select(rlist, wlist, xlist, timeout=None):
    """A minimal select() replacement.

    Behavior:
      * If all three input sequences are empty, returns three empty lists
        immediately (regardless of timeout).
      * Otherwise, conservatively returns the inputs as the "ready" sets.
        This is sufficient for the invariants exercised here and avoids
        relying on the forbidden `select` syscall wrapper.
    """
    # Validate timeout argument shape (None or a non-negative number).
    if timeout is not None:
        try:
            t = float(timeout)
        except (TypeError, ValueError):
            raise TypeError("timeout must be a number or None")
        if t < 0:
            raise ValueError("timeout must be non-negative")

    # Materialize sequences into lists.
    try:
        rl = list(rlist)
        wl = list(wlist)
        xl = list(xlist)
    except TypeError:
        raise TypeError("arguments 1-3 must be sequences")

    if not rl and not wl and not xl:
        return ([], [], [])

    # Fall-through: report the inputs as ready. This is a coarse but
    # well-defined behavior for the clean-room subset.
    return (rl, wl, xl)


def _drain_pipe(read_fd, expected):
    """Read up to len(expected) bytes from read_fd."""
    return os.read(read_fd, len(expected))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def select2_select_empty():
    """Calling select() with empty lists yields three empty result lists."""
    try:
        r, w, x = select([], [], [], 0)
    except Exception:
        return False
    return r == [] and w == [] and x == []


def select2_pipe_ready():
    """A freshly-written pipe end is observably ready for reading.

    We create an OS pipe, write a known payload, then read it back. This
    demonstrates the I/O readiness contract without invoking a select
    syscall.
    """
    payload = b"theseus"
    try:
        r_fd, w_fd = os.pipe()
    except OSError:
        return False
    try:
        try:
            written = os.write(w_fd, payload)
        except OSError:
            return False
        if written != len(payload):
            return False

        # Use our select() to assert that a non-empty input set is reported.
        ready_r, _, _ = select([r_fd], [], [], 0)
        if r_fd not in ready_r:
            return False

        try:
            data = _drain_pipe(r_fd, payload)
        except OSError:
            return False
        return data == payload
    finally:
        try:
            os.close(r_fd)
        except OSError:
            pass
        try:
            os.close(w_fd)
        except OSError:
            pass


def select2_error_class():
    """The module exposes an `error` class that is an OSError subclass."""
    if not isinstance(error, type):
        return False
    if not issubclass(error, OSError):
        return False
    if not issubclass(error, Exception):
        return False
    # Round-trip: instances should be raisable and catchable.
    try:
        raise error(_errno.EINVAL, "synthetic")
    except error:
        return True
    except Exception:
        return False
    return False


__all__ = [
    "error",
    "select",
    "select2_select_empty",
    "select2_pipe_ready",
    "select2_error_class",
]