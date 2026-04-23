"""
theseus_selectors_cr — Clean-room selectors module.
No import of the standard `selectors` module.
Uses the `select` C extension directly for I/O multiplexing.
"""

import select as _select
import os as _os
from collections import namedtuple as _namedtuple

EVENT_READ = 1
EVENT_WRITE = 4

SelectorKey = _namedtuple('SelectorKey', ['fileobj', 'fd', 'events', 'data'])


def _fileobj_lookup(fileobj):
    try:
        return fileobj.fileno()
    except (AttributeError, ValueError):
        return fileobj


class BaseSelector:
    """Abstract base class for I/O selectors."""

    def register(self, fileobj, events, data=None):
        raise NotImplementedError

    def unregister(self, fileobj):
        raise NotImplementedError

    def modify(self, fileobj, events, data=None):
        self.unregister(fileobj)
        return self.register(fileobj, events, data)

    def select(self, timeout=None):
        raise NotImplementedError

    def close(self):
        pass

    def get_key(self, fileobj):
        raise NotImplementedError

    def get_map(self):
        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class _SelectorMapping:
    """Read-only mapping of file objects to selector keys."""

    def __init__(self, selector):
        self._selector = selector

    def __len__(self):
        return len(self._selector._fd_to_key)

    def __getitem__(self, fileobj):
        fd = _fileobj_lookup(fileobj)
        try:
            return self._selector._fd_to_key[fd]
        except KeyError:
            raise KeyError(f"{fileobj!r} is not registered")

    def __iter__(self):
        return iter(self._selector._fd_to_key.values())


class SelectSelector(BaseSelector):
    """Select-based selector."""

    def __init__(self):
        self._fd_to_key = {}
        self._readers = set()
        self._writers = set()

    def register(self, fileobj, events, data=None):
        fd = _fileobj_lookup(fileobj)
        if fd in self._fd_to_key:
            raise KeyError(f"{fileobj!r} is already registered")
        key = SelectorKey(fileobj=fileobj, fd=fd, events=events, data=data)
        self._fd_to_key[fd] = key
        if events & EVENT_READ:
            self._readers.add(fd)
        if events & EVENT_WRITE:
            self._writers.add(fd)
        return key

    def unregister(self, fileobj):
        fd = _fileobj_lookup(fileobj)
        try:
            key = self._fd_to_key.pop(fd)
        except KeyError:
            raise KeyError(f"{fileobj!r} is not registered")
        self._readers.discard(fd)
        self._writers.discard(fd)
        return key

    def select(self, timeout=None):
        if timeout is not None:
            if timeout <= 0:
                timeout = 0
        r, w, _ = _select.select(list(self._readers), list(self._writers), [], timeout)
        ready = []
        r = set(r)
        w = set(w)
        for fd, key in self._fd_to_key.items():
            events = 0
            if fd in r:
                events |= EVENT_READ
            if fd in w:
                events |= EVENT_WRITE
            if events:
                ready.append((key, events & key.events))
        return ready

    def get_key(self, fileobj):
        fd = _fileobj_lookup(fileobj)
        try:
            return self._fd_to_key[fd]
        except KeyError:
            raise KeyError(f"{fileobj!r} is not registered")

    def get_map(self):
        return _SelectorMapping(self)

    def close(self):
        self._fd_to_key.clear()
        self._readers.clear()
        self._writers.clear()


if hasattr(_select, 'poll'):
    class PollSelector(BaseSelector):
        """Poll-based selector."""

        def __init__(self):
            self._fd_to_key = {}
            self._poll = _select.poll()

        def register(self, fileobj, events, data=None):
            fd = _fileobj_lookup(fileobj)
            if fd in self._fd_to_key:
                raise KeyError(f"{fileobj!r} is already registered")
            key = SelectorKey(fileobj=fileobj, fd=fd, events=events, data=data)
            self._fd_to_key[fd] = key
            poll_events = 0
            if events & EVENT_READ:
                poll_events |= _select.POLLIN
            if events & EVENT_WRITE:
                poll_events |= _select.POLLOUT
            self._poll.register(fd, poll_events)
            return key

        def unregister(self, fileobj):
            fd = _fileobj_lookup(fileobj)
            try:
                key = self._fd_to_key.pop(fd)
            except KeyError:
                raise KeyError(f"{fileobj!r} is not registered")
            self._poll.unregister(fd)
            return key

        def select(self, timeout=None):
            if timeout is None:
                timeout_ms = None
            elif timeout <= 0:
                timeout_ms = 0
            else:
                timeout_ms = int(timeout * 1000)
            ready = []
            fd_event_list = self._poll.poll(timeout_ms)
            for fd, event in fd_event_list:
                events = 0
                if event & (_select.POLLIN | _select.POLLPRI | _select.POLLHUP):
                    events |= EVENT_READ
                if event & _select.POLLOUT:
                    events |= EVENT_WRITE
                key = self._fd_to_key.get(fd)
                if key:
                    ready.append((key, events & key.events))
            return ready

        def get_key(self, fileobj):
            fd = _fileobj_lookup(fileobj)
            try:
                return self._fd_to_key[fd]
            except KeyError:
                raise KeyError(f"{fileobj!r} is not registered")

        def get_map(self):
            return _SelectorMapping(self)

        def close(self):
            self._fd_to_key.clear()


if hasattr(_select, 'kqueue'):
    class KqueueSelector(BaseSelector):
        """kqueue-based selector (macOS/BSD)."""

        def __init__(self):
            self._fd_to_key = {}
            self._kqueue = _select.kqueue()

        def fileno(self):
            return self._kqueue.fileno()

        def register(self, fileobj, events, data=None):
            fd = _fileobj_lookup(fileobj)
            if fd in self._fd_to_key:
                raise KeyError(f"{fileobj!r} is already registered")
            key = SelectorKey(fileobj=fileobj, fd=fd, events=events, data=data)
            self._fd_to_key[fd] = key
            if events & EVENT_READ:
                kev = _select.kevent(fd, filter=_select.KQ_FILTER_READ, flags=_select.KQ_EV_ADD)
                self._kqueue.control([kev], 0, 0)
            if events & EVENT_WRITE:
                kev = _select.kevent(fd, filter=_select.KQ_FILTER_WRITE, flags=_select.KQ_EV_ADD)
                self._kqueue.control([kev], 0, 0)
            return key

        def unregister(self, fileobj):
            fd = _fileobj_lookup(fileobj)
            try:
                key = self._fd_to_key.pop(fd)
            except KeyError:
                raise KeyError(f"{fileobj!r} is not registered")
            if key.events & EVENT_READ:
                kev = _select.kevent(fd, filter=_select.KQ_FILTER_READ, flags=_select.KQ_EV_DELETE)
                try:
                    self._kqueue.control([kev], 0, 0)
                except OSError:
                    pass
            if key.events & EVENT_WRITE:
                kev = _select.kevent(fd, filter=_select.KQ_FILTER_WRITE, flags=_select.KQ_EV_DELETE)
                try:
                    self._kqueue.control([kev], 0, 0)
                except OSError:
                    pass
            return key

        def select(self, timeout=None):
            if timeout is None:
                timeout = None
            elif timeout <= 0:
                timeout = 0
            max_ev = max(len(self._fd_to_key), 1)
            ready = []
            kev_list = self._kqueue.control(None, max_ev, timeout)
            for kev in kev_list:
                fd = kev.ident
                key = self._fd_to_key.get(fd)
                if key is None:
                    continue
                events = 0
                if kev.filter == _select.KQ_FILTER_READ:
                    events |= EVENT_READ
                if kev.filter == _select.KQ_FILTER_WRITE:
                    events |= EVENT_WRITE
                if events:
                    ready.append((key, events & key.events))
            return ready

        def get_key(self, fileobj):
            fd = _fileobj_lookup(fileobj)
            try:
                return self._fd_to_key[fd]
            except KeyError:
                raise KeyError(f"{fileobj!r} is not registered")

        def get_map(self):
            return _SelectorMapping(self)

        def close(self):
            self._fd_to_key.clear()
            self._kqueue.close()


def DefaultSelector():
    """Return the most efficient selector for the current platform."""
    if hasattr(_select, 'kqueue'):
        return KqueueSelector()
    if hasattr(_select, 'epoll'):
        return EpollSelector()
    if hasattr(_select, 'poll'):
        return PollSelector()
    return SelectSelector()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def selectors2_create():
    """DefaultSelector() can be created and closed; returns True."""
    sel = DefaultSelector()
    sel.close()
    return True


def selectors2_register():
    """register/unregister a pipe read end works; returns True."""
    r, w = _os.pipe()
    try:
        sel = DefaultSelector()
        key = sel.register(r, EVENT_READ)
        found = sel.get_key(r)
        sel.unregister(r)
        sel.close()
        return key.fd == r and found.fd == r
    finally:
        _os.close(r)
        _os.close(w)


def selectors2_select_timeout():
    """select() with timeout=0 returns quickly on empty set; returns True."""
    sel = DefaultSelector()
    ready = sel.select(timeout=0)
    sel.close()
    return isinstance(ready, list)


__all__ = [
    'EVENT_READ', 'EVENT_WRITE', 'SelectorKey',
    'BaseSelector', 'SelectSelector',
    'DefaultSelector',
    'selectors2_create', 'selectors2_register', 'selectors2_select_timeout',
]
