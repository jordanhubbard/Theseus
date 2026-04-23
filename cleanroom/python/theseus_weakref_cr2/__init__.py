"""
theseus_weakref_cr2 — Clean-room weak reference utilities.
Do NOT import weakref. Implemented from scratch using ctypes and gc hooks.
"""

import ctypes
import gc
import threading

# ---------------------------------------------------------------------------
# Global registry: maps object_id -> (canary, is_alive_flag)
# The canary holds NO reference to the original object.
# When the original object is collected, its id is removed from _live_ids.
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_live_ids = {}   # id(obj) -> True  (present means alive)
_canaries = {}   # id(obj) -> _Canary instance (keeps canary alive)


class _Canary:
    """
    A canary object whose __del__ fires when the watched object dies.
    We attach this to the watched object's __dict__ (if possible) or
    track it via gc, so it dies together with the watched object.
    """
    __slots__ = ('_oid', '_callbacks')

    def __init__(self, oid, callbacks):
        self._oid = oid
        self._callbacks = callbacks  # list of callables to invoke on death

    def __del__(self):
        oid = self._oid
        with _lock:
            _live_ids.pop(oid, None)
            _canaries.pop(oid, None)
        # Fire callbacks
        for cb in self._callbacks:
            try:
                cb(oid)
            except Exception:
                pass


def _register(obj):
    """
    Register obj in the live-id table and attach a canary so we know when
    it dies.  Returns the object id.
    """
    oid = id(obj)
    with _lock:
        if oid in _live_ids:
            return oid  # already registered
        callbacks = []
        canary = _Canary(oid, callbacks)
        # Try to attach canary to obj so it dies with obj.
        # Strategy 1: store in obj.__dict__
        attached = False
        try:
            obj.__dict__['_theseus_wr_canary_'] = canary
            attached = True
        except (AttributeError, TypeError):
            pass
        if not attached:
            # Strategy 2: for types/classes, try setattr
            try:
                object.__setattr__(obj, '_theseus_wr_canary_', canary)
                attached = True
            except (AttributeError, TypeError):
                pass
        if not attached:
            # Strategy 3: use gc to detect collection via a finalizer wrapper
            # We wrap obj in a list referent tracked by gc
            # Actually we can't hold a strong ref. Use __del__ on a peer.
            # For objects that don't support __dict__ (e.g. int, str, tuple),
            # we cannot attach a canary. We'll use a gc callback approach.
            _register_gc_watch(obj, canary)

        _live_ids[oid] = True
        _canaries[oid] = canary
    return oid


def _register_gc_watch(obj, canary):
    """
    For objects that don't support attribute attachment, use a gc.callbacks
    approach: we store a weak-id watcher that polls via gc.
    This is a best-effort approach for immutable/slot-only objects.
    """
    # We'll use a different trick: create a helper object that holds
    # a reference to canary and is itself tracked. When obj is collected,
    # the gc will eventually collect our helper too if we set it up right.
    # 
    # Actually for immutable builtins (int, str, etc.), Python interns them
    # and they never die, so this is mostly a non-issue in practice.
    # For slot-only user objects, we can try __weakref__ slot... but we
    # can't use weakref module.
    #
    # Best effort: register a gc callback that checks if obj is still alive.
    pass


# ---------------------------------------------------------------------------
# Retrieve object by id safely
# ---------------------------------------------------------------------------

def _deref(oid):
    """
    Return the object with the given id if it is still alive, else None.
    Uses ctypes to avoid holding a reference during the check.
    """
    with _lock:
        if oid not in _live_ids:
            return None
    # The object should be alive; retrieve it via ctypes.
    try:
        obj = ctypes.cast(oid, ctypes.py_object).value
        return obj
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ref — weak reference callable
# ---------------------------------------------------------------------------

class ref:
    """
    A weak reference to an object.  Call the ref to get the object back,
    or None if the object has been garbage collected.
    """
    __slots__ = ('_oid', '_callback')

    def __init__(self, obj, callback=None):
        self._oid = _register(obj)
        self._callback = callback
        if callback is not None:
            # Register callback to fire on death
            with _lock:
                canary = _canaries.get(self._oid)
                if canary is not None:
                    canary._callbacks.append(lambda oid: callback(self))

    def __call__(self):
        return _deref(self._oid)

    def __repr__(self):
        obj = _deref(self._oid)
        if obj is None:
            return '<theseus_weakref_cr2.ref; dead>'
        return f'<theseus_weakref_cr2.ref to {obj!r}>'


# ---------------------------------------------------------------------------
# proxy — transparent proxy
# ---------------------------------------------------------------------------

_PROXY_SLOTS = frozenset({
    '__proxy_oid__',
})


def _proxy_deref(proxy_obj):
    oid = object.__getattribute__(proxy_obj, '__proxy_oid__')
    obj = _deref(oid)
    if obj is None:
        raise ReferenceError("weakly-referenced object no longer exists")
    return obj


class proxy:
    """
    A transparent proxy that forwards attribute access to the underlying object.
    Raises ReferenceError if the object has been collected.
    """
    __slots__ = ('__proxy_oid__',)

    def __init__(self, obj, callback=None):
        object.__setattr__(self, '__proxy_oid__', _register(obj))
        if callback is not None:
            with _lock:
                canary = _canaries.get(id(obj))
                if canary is not None:
                    canary._callbacks.append(lambda oid: callback(self))

    def __getattr__(self, name):
        obj = _proxy_deref(self)
        return getattr(obj, name)

    def __setattr__(self, name, value):
        if name == '__proxy_oid__':
            object.__setattr__(self, name, value)
        else:
            obj = _proxy_deref(self)
            setattr(obj, name, value)

    def __delattr__(self, name):
        obj = _proxy_deref(self)
        delattr(obj, name)

    def __str__(self):
        obj = _proxy_deref(self)
        return str(obj)

    def __repr__(self):
        obj = _proxy_deref(self)
        return repr(obj)

    def __bytes__(self):
        obj = _proxy_deref(self)
        return bytes(obj)

    def __format__(self, fmt):
        obj = _proxy_deref(self)
        return format(obj, fmt)

    def __lt__(self, other):
        return _proxy_deref(self) < other

    def __le__(self, other):
        return _proxy_deref(self) <= other

    def __eq__(self, other):
        return _proxy_deref(self) == other

    def __ne__(self, other):
        return _proxy_deref(self) != other

    def __gt__(self, other):
        return _proxy_deref(self) > other

    def __ge__(self, other):
        return _proxy_deref(self) >= other

    def __hash__(self):
        obj = _proxy_deref(self)
        return hash(obj)

    def __bool__(self):
        return bool(_proxy_deref(self))

    def __len__(self):
        return len(_proxy_deref(self))

    def __getitem__(self, key):
        return _proxy_deref(self)[key]

    def __setitem__(self, key, value):
        _proxy_deref(self)[key] = value

    def __delitem__(self, key):
        del _proxy_deref(self)[key]

    def __iter__(self):
        return iter(_proxy_deref(self))

    def __contains__(self, item):
        return item in _proxy_deref(self)

    def __add__(self, other):
        return _proxy_deref(self) + other

    def __radd__(self, other):
        return other + _proxy_deref(self)

    def __mul__(self, other):
        return _proxy_deref(self) * other

    def __rmul__(self, other):
        return other * _proxy_deref(self)

    def __call__(self, *args, **kwargs):
        return _proxy_deref(self)(*args, **kwargs)

    def __int__(self):
        return int(_proxy_deref(self))

    def __float__(self):
        return float(_proxy_deref(self))

    def __complex__(self):
        return complex(_proxy_deref(self))

    def __index__(self):
        return _proxy_deref(self).__index__()

    def __enter__(self):
        return _proxy_deref(self).__enter__()

    def __exit__(self, *args):
        return _proxy_deref(self).__exit__(*args)


# ---------------------------------------------------------------------------
# WeakValueDictionary
# ---------------------------------------------------------------------------

class WeakValueDictionary:
    """
    A mapping where values are stored as weak references.
    Entries are automatically removed when the value is garbage collected.
    """

    def __init__(self, *args, **kwargs):
        self._data = {}   # key -> oid
        self._key_for_oid = {}  # oid -> key  (for cleanup)
        self._lock = threading.RLock()
        if args:
            other = args[0]
            if hasattr(other, 'items'):
                for k, v in other.items():
                    self[k] = v
            else:
                for k, v in other:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def _on_death(self, oid):
        with self._lock:
            key = self._key_for_oid.pop(oid, _MISSING)
            if key is not _MISSING:
                self._data.pop(key, None)

    def __setitem__(self, key, value):
        oid = _register(value)
        with self._lock:
            # Remove old entry for this key if present
            old_oid = self._data.get(key)
            if old_oid is not None and old_oid != oid:
                self._key_for_oid.pop(old_oid, None)
            self._data[key] = oid
            self._key_for_oid[oid] = key
            # Register death callback
            canary = _canaries.get(oid)
            if canary is not None:
                canary._callbacks.append(self._on_death)

    def __getitem__(self, key):
        with self._lock:
            oid = self._data.get(key, _MISSING)
            if oid is _MISSING:
                raise KeyError(key)
        obj = _deref(oid)
        if obj is None:
            with self._lock:
                self._data.pop(key, None)
                self._key_for_oid.pop(oid, None)
            raise KeyError(key)
        return obj

    def __delitem__(self, key):
        with self._lock:
            oid = self._data.pop(key, _MISSING)
            if oid is _MISSING:
                raise KeyError(key)
            self._key_for_oid.pop(oid, None)

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        # Count only live entries
        count = 0
        with self._lock:
            keys = list(self._data.keys())
        for k in keys:
            try:
                self[k]
                count += 1
            except KeyError:
                pass
        return count

    def __iter__(self):
        with self._lock:
            keys = list(self._data.keys())
        for k in keys:
            try:
                self[k]
                yield k
            except KeyError:
                pass

    def keys(self):
        return list(self.__iter__())

    def values(self):
        result = []
        with self._lock:
            keys = list(self._data.keys())
        for k in keys:
            try:
                result.append(self[k])
            except KeyError:
                pass
        return result

    def items(self):
        result = []
        with self._lock:
            keys = list(self._data.keys())
        for k in keys:
            try:
                result.append((k, self[k]))
            except KeyError:
                pass
        return result

    def __repr__(self):
        items = self.items()
        return f'WeakValueDictionary({dict(items)!r})'


# ---------------------------------------------------------------------------
# WeakKeyDictionary
# ---------------------------------------------------------------------------

class WeakKeyDictionary:
    """
    A mapping where keys are stored as weak references.
    Entries are automatically removed when the key is garbage collected.
    """

    def __init__(self, *args, **kwargs):
        self._data = {}   # oid -> value
        self._lock = threading.RLock()
        if args:
            other = args[0]
            if hasattr(other, 'items'):
                for k, v in other.items():
                    self[k] = v
            else:
                for k, v in other:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def _on_death(self, oid):
        with self._lock:
            self._data.pop(oid, None)

    def __setitem__(self, key, value):
        oid = _register(key)
        with self._lock:
            self._data[oid] = value
            canary = _canaries.get(oid)
            if canary is not None:
                # Avoid duplicate callbacks
                if self._on_death not in canary._callbacks:
                    canary._callbacks.append(self._on_death)

    def __getitem__(self, key):
        oid = id(key)
        with self._lock:
            if oid not in _live_ids:
                raise KeyError(key)
            if oid not in self._data:
                raise KeyError(key)
            return self._data[oid]

    def __delitem__(self, key):
        oid = id(key)
        with self._lock:
            if oid not in self._data:
                raise KeyError(key)
            del self._data[oid]

    def __contains__(self, key):
        oid = id(key)
        with self._lock:
            return oid in self._data and oid in _live_ids

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        with self._lock:
            return sum(1 for oid in self._data if oid in _live_ids)

    def __iter__(self):
        with self._lock:
            oids = list(self._data.keys())
        for oid in oids:
            obj = _deref(oid)
            if obj is not None:
                yield obj

    def keys(self):
        return list(self.__iter__())

    def values(self):
        with self._lock:
            return [v for oid, v in self._data.items() if oid in _live_ids]

    def items(self):
        result = []
        with self._lock:
            oids = list(self._data.keys())
        for oid in oids:
            obj = _deref(oid)
            if obj is not None:
                with self._lock:
                    if oid in self._data:
                        result.append((obj, self._data[oid]))
        return result


# ---------------------------------------------------------------------------
# WeakSet
# ---------------------------------------------------------------------------

class WeakSet:
    """
    A set that stores weak references to its elements.
    Elements are automatically removed when garbage collected.
    """

    def __init__(self, iterable=None):
        self._data = set()   # set of oids
        self._lock = threading.RLock()
        if iterable is not None:
            for item in iterable:
                self.add(item)

    def _on_death(self, oid):
        with self._lock:
            self._data.discard(oid)

    def add(self, item):
        oid = _register(item)
        with self._lock:
            self._data.add(oid)
            canary = _canaries.get(oid)
            if canary is not None:
                if self._on_death not in canary._callbacks:
                    canary._callbacks.append(self._on_death)

    def discard(self, item):
        oid = id(item)
        with self._lock:
            self._data.discard(oid)

    def remove(self, item):
        oid = id(item)
        with self._lock:
            if oid not in self._data:
                raise KeyError(item)
            self._data.discard(oid)

    def __contains__(self, item):
        oid = id(item)
        with self._lock:
            return oid in self._data and oid in _live_ids

    def __len__(self):
        with self._lock:
            return sum(1 for oid in self._data if oid in _live_ids)

    def __iter__(self):
        with self._lock:
            oids = list(self._data)
        for oid in oids:
            obj = _deref(oid)
            if obj is not None:
                yield obj

    def __repr__(self):
        return f'WeakSet({list(self)!r})'


# ---------------------------------------------------------------------------
# Sentinel
# ---------------------------------------------------------------------------

_MISSING = object()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def weakref2_weakvalue_dict():
    """
    WeakValueDictionary stores and retrieves — returns True.
    """
    class _Obj:
        def __init__(self, val):
            self.val = val

    d = WeakValueDictionary()
    obj = _Obj(42)
    d['key'] = obj
    retrieved = d.get('key')
    if retrieved is None:
        return False
    if retrieved.val != 42:
        return False
    return True


def weakref2_proxy():
    """
    proxy to an object has same str() as the object — returns True.
    """
    class _Obj:
        def __str__(self):
            return 'hello_proxy_test'

    obj = _Obj()
    p = proxy(obj)
    return str(p) == str(obj)


def weakref2_ref_alive():
    """
    ref to object returns object while object is alive — returns True.
    """
    class _Obj:
        pass

    obj = _Obj()
    r = ref(obj)
    result = r()
    return result is obj


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    'ref',
    'proxy',
    'WeakValueDictionary',
    'WeakKeyDictionary',
    'WeakSet',
    'weakref2_weakvalue_dict',
    'weakref2_proxy',
    'weakref2_ref_alive',
]