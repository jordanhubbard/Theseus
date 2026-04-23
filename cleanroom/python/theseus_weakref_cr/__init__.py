"""
theseus_weakref_cr — Clean-room weakref module.
No import of the standard `weakref` module.

Uses Python's built-in _weakref C extension.
"""

import _weakref


def ref(ob, callback=None):
    """Return a weak reference to ob."""
    if callback is None:
        return _weakref.ref(ob)
    return _weakref.ref(ob, callback)


def proxy(ob, callback=None):
    """Return a weak proxy to ob."""
    if callback is None:
        return _weakref.proxy(ob)
    return _weakref.proxy(ob, callback)


def getweakrefcount(ob):
    """Return the number of weak references to ob."""
    return _weakref.getweakrefcount(ob)


def getweakrefs(ob):
    """Return list of all weak references to ob."""
    return _weakref.getweakrefs(ob)


class WeakValueDictionary:
    """Dictionary mapping keys to weakly-referenced values."""

    def __init__(self, other=None):
        self._data = {}
        if other:
            self.update(other)

    def _cleanup(self, key_ref):
        key = key_ref()
        if key is not None:
            self._data.pop(key, None)

    def __setitem__(self, key, value):
        def callback(wr, k=key):
            self._data.pop(k, None)
        self._data[key] = _weakref.ref(value, callback)

    def __getitem__(self, key):
        wr = self._data[key]
        obj = wr()
        if obj is None:
            del self._data[key]
            raise KeyError(key)
        return obj

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        wr = self._data.get(key)
        if wr is None:
            return False
        return wr() is not None

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        return sum(1 for wr in self._data.values() if wr() is not None)

    def keys(self):
        return [k for k, wr in self._data.items() if wr() is not None]

    def values(self):
        return [wr() for wr in self._data.values() if wr() is not None]

    def items(self):
        return [(k, wr()) for k, wr in self._data.items() if wr() is not None]

    def update(self, other):
        for k, v in (other.items() if hasattr(other, 'items') else other):
            self[k] = v


class WeakKeyDictionary:
    """Dictionary with weak-referenced keys."""

    def __init__(self, other=None):
        self._data = {}
        if other:
            self.update(other)

    def __setitem__(self, key, value):
        def callback(wr, k=id(key)):
            self._data.pop(k, None)
        self._data[id(key)] = (_weakref.ref(key, callback), value)

    def __getitem__(self, key):
        entry = self._data.get(id(key))
        if entry is None:
            raise KeyError(key)
        wr, value = entry
        if wr() is None:
            del self._data[id(key)]
            raise KeyError(key)
        return value

    def __contains__(self, key):
        entry = self._data.get(id(key))
        return entry is not None and entry[0]() is not None

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, other):
        for k, v in (other.items() if hasattr(other, 'items') else other):
            self[k] = v


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def weakref2_ref():
    """weakref.ref(obj)() returns the object while alive; returns True."""
    class Obj:
        pass
    obj = Obj()
    r = ref(obj)
    return r() is obj


def weakref2_dead():
    """weakref returns None after object is deleted; returns True."""
    class Obj:
        pass
    obj = Obj()
    r = ref(obj)
    del obj
    return r() is None


def weakref2_proxy():
    """weakproxy allows attribute access while object alive; returns 42."""
    class Obj:
        value = 42
    obj = Obj()
    p = proxy(obj)
    return p.value


__all__ = [
    'ref', 'proxy', 'getweakrefcount', 'getweakrefs',
    'WeakValueDictionary', 'WeakKeyDictionary',
    'weakref2_ref', 'weakref2_dead', 'weakref2_proxy',
]
