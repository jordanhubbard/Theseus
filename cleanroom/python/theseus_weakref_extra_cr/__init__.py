"""
theseus_weakref_extra_cr — Clean-room weakref module.
No import of the standard `weakref` module.
Uses _weakref C extension directly.
"""

import _weakref as _wr
import gc as _gc
import threading as _threading


ref = _wr.ref
getweakrefcount = _wr.getweakrefcount
getweakrefs = _wr.getweakrefs
proxy = _wr.proxy

class _WeakRefTarget:
    pass

ReferenceType = type(_wr.ref(_WeakRefTarget()))

try:
    ProxyType = type(_wr.proxy(_WeakRefTarget()))
    CallableProxyType = type(_wr.proxy(lambda: None))
except Exception:
    ProxyType = None
    CallableProxyType = None


class WeakValueDictionary:
    """Mapping class that references values weakly."""

    def __init__(self, other=(), **kwargs):
        self._data = {}
        self.update(other, **kwargs)

    def __setitem__(self, key, value):
        def remove(wr, selfref=_wr.ref(self), key=key):
            self = selfref()
            if self is not None:
                try:
                    del self._data[key]
                except KeyError:
                    pass
        self._data[key] = _wr.ref(value, remove)

    def __getitem__(self, key):
        wr = self._data[key]
        o = wr()
        if o is None:
            raise KeyError(key)
        return o

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        wr = self._data.get(key)
        return wr is not None and wr() is not None

    def __len__(self):
        return sum(1 for wr in self._data.values() if wr() is not None)

    def __iter__(self):
        for key, wr in list(self._data.items()):
            if wr() is not None:
                yield key

    def keys(self):
        return list(self)

    def values(self):
        result = []
        for wr in list(self._data.values()):
            o = wr()
            if o is not None:
                result.append(o)
        return result

    def items(self):
        result = []
        for key, wr in list(self._data.items()):
            o = wr()
            if o is not None:
                result.append((key, o))
        return result

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, *args):
        try:
            wr = self._data.pop(key)
            o = wr()
            if o is None:
                raise KeyError(key)
            return o
        except KeyError:
            if args:
                return args[0]
            raise

    def update(self, other=(), **kwargs):
        if isinstance(other, dict):
            items = other.items()
        elif hasattr(other, 'items'):
            items = other.items()
        else:
            items = other
        for key, value in items:
            self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def clear(self):
        self._data.clear()

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self.get(key)

    def copy(self):
        new = WeakValueDictionary()
        for key, value in self.items():
            new[key] = value
        return new

    def __repr__(self):
        return '<WeakValueDictionary at 0x%x>' % id(self)


class WeakKeyDictionary:
    """Mapping class that references keys weakly."""

    def __init__(self, other=(), **kwargs):
        self._data = {}
        self.update(other, **kwargs)

    def _ref_from_key(self, key):
        def remove(wr, selfref=_wr.ref(self), key_id=id(key)):
            self = selfref()
            if self is not None:
                try:
                    del self._data[key_id]
                except KeyError:
                    pass
        return _wr.ref(key, remove)

    def __setitem__(self, key, value):
        self._data[id(key)] = (self._ref_from_key(key), value)

    def __getitem__(self, key):
        wr, value = self._data[id(key)]
        if wr() is None:
            raise KeyError(key)
        return value

    def __delitem__(self, key):
        try:
            del self._data[id(key)]
        except KeyError:
            raise KeyError(key)

    def __contains__(self, key):
        entry = self._data.get(id(key))
        return entry is not None and entry[0]() is not None

    def __len__(self):
        return sum(1 for wr, _ in self._data.values() if wr() is not None)

    def __iter__(self):
        for wr, _ in list(self._data.values()):
            k = wr()
            if k is not None:
                yield k

    def keys(self):
        return list(self)

    def values(self):
        return [v for wr, v in list(self._data.values()) if wr() is not None]

    def items(self):
        result = []
        for wr, v in list(self._data.values()):
            k = wr()
            if k is not None:
                result.append((k, v))
        return result

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, other=(), **kwargs):
        if isinstance(other, dict):
            items = other.items()
        elif hasattr(other, 'items'):
            items = other.items()
        else:
            items = other
        for key, value in items:
            self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def clear(self):
        self._data.clear()


class WeakSet:
    """A set that holds weak references to objects."""

    def __init__(self, iterable=()):
        self._data = WeakValueDictionary()
        for item in iterable:
            self.add(item)

    def add(self, item):
        self._data[id(item)] = item

    def discard(self, item):
        try:
            del self._data[id(item)]
        except KeyError:
            pass

    def remove(self, item):
        del self._data[id(item)]

    def __contains__(self, item):
        return id(item) in self._data

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data.values())

    def clear(self):
        self._data.clear()

    def pop(self):
        try:
            _, v = self._data._data.popitem()
            wr, _ = v if isinstance(v, tuple) else (v, None)
            # Actually just use WeakValueDictionary properly
            for k in list(self._data):
                val = self._data[k]
                del self._data[k]
                return val
        except (KeyError, StopIteration):
            raise KeyError('pop from empty set')


class finalize:
    """Finalization callback for weak-reference cleanup."""

    _registry = {}
    _registry_lock = _threading.RLock()
    _dirty = False
    _registered_with_atexit = False

    def __init__(self, obj, func, /, *args, **kwargs):
        if not callable(func):
            raise ValueError('func must be callable')
        with finalize._registry_lock:
            self._atexit_id = None
            self._weakref = _wr.ref(obj, self._cleanup)
            self._func = func
            self._args = args
            self._kwargs = kwargs
            self._alive = True
            self._index = (id(obj), id(self))
            finalize._registry[self._index] = self
            if not finalize._registered_with_atexit:
                finalize._registered_with_atexit = True
                import atexit
                atexit.register(finalize._exitfunc)

    def _cleanup(self, wr):
        self()

    def __call__(self):
        with finalize._registry_lock:
            if not self._alive:
                return None
            self._alive = False
            try:
                del finalize._registry[self._index]
            except KeyError:
                pass
        try:
            return self._func(*self._args, **self._kwargs)
        except Exception:
            pass

    def detach(self):
        with finalize._registry_lock:
            if not self._alive:
                return None
            obj = self._weakref()
            if obj is None:
                return None
            self._alive = False
            try:
                del finalize._registry[self._index]
            except KeyError:
                pass
            return (obj, self._func, self._args, self._kwargs)

    def peek(self):
        with finalize._registry_lock:
            if self._alive:
                return (self._weakref(), self._func, self._args, self._kwargs)
            return None

    @property
    def alive(self):
        return self._alive

    def __repr__(self):
        info = ['dead']
        if self._alive:
            obj = self._weakref()
            info = ['alive']
            if obj is not None:
                info.append('object=%r' % obj)
        info.append('func=%r' % self._func)
        return '<%s object at %#x; %s>' % (type(self).__name__, id(self), ', '.join(info))

    @classmethod
    def _exitfunc(cls):
        reenable_gc = False
        try:
            if cls._registry:
                import gc
                reenable_gc = gc.isenabled()
                gc.disable()
                pending = None
                while True:
                    if pending is None or _gc.collect() == 0:
                        with cls._registry_lock:
                            if not cls._registry:
                                break
                            key = min(cls._registry)
                            pending = cls._registry[key]
                    try:
                        pending()
                    except Exception:
                        pass
                    finally:
                        pending = None
        finally:
            if reenable_gc:
                _gc.enable()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def weakref2_ref():
    """ref() creates weak reference that returns object; returns True."""
    class MyObj:
        pass
    obj = MyObj()
    wr = ref(obj)
    return wr() is obj


def weakref2_dead():
    """ref() returns None after object is deleted; returns True."""
    class MyObj:
        pass
    obj = MyObj()
    wr = ref(obj)
    del obj
    _gc.collect()
    return wr() is None


def weakref2_weakvalue_dict():
    """WeakValueDictionary removes entries when values are GC'd; returns True."""
    class MyObj:
        pass
    d = WeakValueDictionary()
    obj = MyObj()
    d['key'] = obj
    alive = 'key' in d
    del obj
    _gc.collect()
    dead = 'key' not in d
    return alive and dead


__all__ = [
    'ref', 'proxy', 'getweakrefcount', 'getweakrefs',
    'ReferenceType', 'ProxyType', 'CallableProxyType',
    'WeakValueDictionary', 'WeakKeyDictionary', 'WeakSet', 'finalize',
    'weakref2_ref', 'weakref2_dead', 'weakref2_weakvalue_dict',
]
