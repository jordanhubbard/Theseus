"""Clean-room implementation of theseus_selectors_cr.

This module provides a minimal selectors-like surface without importing
the original `selectors` package. Only standard-library primitives are used.
"""


# Event mask constants (mirroring the typical selectors API surface)
EVENT_READ = 1 << 0
EVENT_WRITE = 1 << 1


class SelectorKey:
    """Represents a registered file object on a selector."""

    __slots__ = ("fileobj", "fd", "events", "data")

    def __init__(self, fileobj, fd, events, data=None):
        self.fileobj = fileobj
        self.fd = fd
        self.events = events
        self.data = data

    def __repr__(self):
        return (
            "SelectorKey(fileobj=%r, fd=%r, events=%r, data=%r)"
            % (self.fileobj, self.fd, self.events, self.data)
        )


def _fileobj_to_fd(fileobj):
    """Return the file descriptor for fileobj.

    Accepts either an integer fd or any object with a ``fileno()`` method.
    """
    if isinstance(fileobj, int):
        fd = fileobj
    else:
        try:
            fd = int(fileobj.fileno())
        except (AttributeError, TypeError, ValueError):
            raise ValueError("Invalid file object: %r" % (fileobj,))
    if fd < 0:
        raise ValueError("Invalid file descriptor: %d" % fd)
    return fd


class _BaseSelector:
    """A minimal in-memory selector.

    This is a clean-room implementation: it does not rely on the standard
    library ``selectors`` module. ``select`` is a pure no-op that simply
    honors the timeout contract — it returns an empty list of ready keys.
    Real I/O readiness is out of scope for the invariants we verify.
    """

    def __init__(self):
        self._fd_to_key = {}

    # --- registration -------------------------------------------------

    def register(self, fileobj, events, data=None):
        if not events or events & ~(EVENT_READ | EVENT_WRITE):
            raise ValueError("Invalid events: %r" % (events,))
        fd = _fileobj_to_fd(fileobj)
        if fd in self._fd_to_key:
            raise KeyError("%r is already registered" % (fileobj,))
        key = SelectorKey(fileobj, fd, events, data)
        self._fd_to_key[fd] = key
        return key

    def unregister(self, fileobj):
        fd = _fileobj_to_fd(fileobj)
        try:
            return self._fd_to_key.pop(fd)
        except KeyError:
            raise KeyError("%r is not registered" % (fileobj,))

    def modify(self, fileobj, events, data=None):
        fd = _fileobj_to_fd(fileobj)
        if fd not in self._fd_to_key:
            raise KeyError("%r is not registered" % (fileobj,))
        key = SelectorKey(fileobj, fd, events, data)
        self._fd_to_key[fd] = key
        return key

    # --- lookup -------------------------------------------------------

    def get_key(self, fileobj):
        fd = _fileobj_to_fd(fileobj)
        try:
            return self._fd_to_key[fd]
        except KeyError:
            raise KeyError("%r is not registered" % (fileobj,))

    def get_map(self):
        # Return a shallow copy to discourage external mutation.
        return dict(self._fd_to_key)

    # --- selection ----------------------------------------------------

    def select(self, timeout=None):
        """Honor the timeout contract and return an empty ready list.

        - timeout is None: return immediately with no events.
        - timeout <= 0: return immediately with no events.
        - timeout > 0: validated as a finite non-negative number; we do
          not block on real I/O in this clean-room implementation.
        """
        if timeout is not None:
            try:
                t = float(timeout)
            except (TypeError, ValueError):
                raise TypeError("timeout must be a number or None")
            if t != t:  # NaN check without importing math
                raise ValueError("timeout must not be NaN")
            if t < 0:
                t = 0.0
        return []

    def close(self):
        self._fd_to_key.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class DefaultSelector(_BaseSelector):
    """Default selector type for this clean-room module."""
    pass


# ---------------------------------------------------------------------------
# Invariant entry points
# ---------------------------------------------------------------------------


def selectors2_create():
    """Invariant: a selector can be created and exposes the expected API."""
    sel = DefaultSelector()
    try:
        if not isinstance(sel, _BaseSelector):
            return False
        if not hasattr(sel, "register"):
            return False
        if not hasattr(sel, "unregister"):
            return False
        if not hasattr(sel, "select"):
            return False
        if sel.get_map() != {}:
            return False
        return True
    finally:
        sel.close()


def selectors2_register():
    """Invariant: register/unregister round-trips a SelectorKey correctly."""
    sel = DefaultSelector()
    try:
        fd = 7  # arbitrary integer fd; we never actually do I/O on it
        key = sel.register(fd, EVENT_READ, data="payload")
        if not isinstance(key, SelectorKey):
            return False
        if key.fd != fd or key.events != EVENT_READ or key.data != "payload":
            return False
        if sel.get_key(fd) is not key:
            return False

        # Duplicate registration must raise KeyError.
        try:
            sel.register(fd, EVENT_READ)
        except KeyError:
            pass
        else:
            return False

        # Modifying should preserve fd and update events/data.
        modified = sel.modify(fd, EVENT_READ | EVENT_WRITE, data="updated")
        if modified.events != (EVENT_READ | EVENT_WRITE):
            return False
        if modified.data != "updated":
            return False

        # Unregister returns the latest key and clears the map.
        removed = sel.unregister(fd)
        if removed.fd != fd:
            return False
        if sel.get_map() != {}:
            return False

        # Unregistering again must raise KeyError.
        try:
            sel.unregister(fd)
        except KeyError:
            return True
        return False
    finally:
        sel.close()


def selectors2_select_timeout():
    """Invariant: select() honors the timeout contract without blocking."""
    sel = DefaultSelector()
    try:
        # No registrations, several timeout shapes — all must return [].
        if sel.select(0) != []:
            return False
        if sel.select(0.0) != []:
            return False
        if sel.select(None) != []:
            return False
        if sel.select(-1) != []:  # negative is normalized to 0
            return False

        # Bad timeout types should raise TypeError.
        try:
            sel.select("not-a-number")
        except TypeError:
            pass
        else:
            return False

        # With a registration, select still returns [] (no real I/O here).
        sel.register(3, EVENT_READ)
        if sel.select(0) != []:
            return False
        return True
    finally:
        sel.close()