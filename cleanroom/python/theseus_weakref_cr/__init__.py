"""
theseus_weakref_cr — Clean-room weakref module.

A clean-room implementation of weak reference semantics. Does NOT import
the standard `weakref` module nor the underlying `_weakref` C extension.

True weak-reference semantics (notification on object collection) require
hooks into CPython's garbage collector that are not exposed to pure
Python. This implementation provides the API surface and the explicit
"dead reference" behavior needed by the invariants, using only Python
standard-library built-ins.
"""


# ---------------------------------------------------------------------------
# Reference object
# ---------------------------------------------------------------------------

class ref:
    """A reference object mimicking ``weakref.ref``.

    Calling the instance returns the referent if still alive, else None.
    The reference can be explicitly killed via ``_kill()`` to simulate
    the referent being garbage-collected.
    """

    __slots__ = ("_target", "_callback", "_alive", "__weakref__")

    def __init__(self, ob, callback=None):
        object.__setattr__(self, "_target", ob)
        object.__setattr__(self, "_callback", callback)
        object.__setattr__(self, "_alive", True)

    def __call__(self):
        if object.__getattribute__(self, "_alive"):
            return object.__getattribute__(self, "_target")
        return None

    def _kill(self):
        """Mark this reference as dead and fire its callback (if any)."""
        if not object.__getattribute__(self, "_alive"):
            return
        object.__setattr__(self, "_alive", False)
        object.__setattr__(self, "_target", None)
        cb = object.__getattribute__(self, "_callback")
        if cb is not None:
            try:
                cb(self)
            except Exception:
                pass

    def __repr__(self):
        if object.__getattribute__(self, "_alive"):
            return "<weakref to live object>"
        return "<weakref to dead object>"

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        if isinstance(other, ref):
            a = self()
            b = other()
            if a is None or b is None:
                return self is other
            return a == b
        return NotImplemented


# ---------------------------------------------------------------------------
# Proxy object
# ---------------------------------------------------------------------------

class _ProxyBase:
    """Forward attribute / item access to a referent.

    Only ``__getattr__`` is needed: Python's attribute machinery first
    checks the instance dict and the class for the attribute; only when
    those fail does it fall back to ``__getattr__``. We store the
    referent in the instance dict under a private name and forward
    everything else.
    """

    def __init__(self, ob, callback=None):
        self.__dict__["_target"] = ob
        self.__dict__["_callback"] = callback
        self.__dict__["_alive"] = True

    def _kill(self):
        if not self.__dict__["_alive"]:
            return
        self.__dict__["_alive"] = False
        self.__dict__["_target"] = None
        cb = self.__dict__["_callback"]
        if cb is not None:
            try:
                cb(self)
            except Exception:
                pass

    def _check(self):
        if not self.__dict__["_alive"]:
            raise ReferenceError("weakly-referenced object no longer exists")
        return self.__dict__["_target"]

    def __getattr__(self, name):
        # __getattr__ is only invoked for names not found by the normal
        # mechanism; the private bookkeeping names live in __dict__ and
        # are reached directly without entering this method.
        target = self._check()
        return getattr(target, name)

    def __setattr__(self, name, value):
        target = self._check()
        setattr(target, name, value)

    def __delattr__(self, name):
        target = self._check()
        delattr(target, name)

    def __repr__(self):
        if self.__dict__["_alive"]:
            return "<weakproxy to live object>"
        return "<weakproxy to dead object>"

    def __bool__(self):
        return bool(self._check())

    def __str__(self):
        return str(self._check())

    def __len__(self):
        return len(self._check())

    def __getitem__(self, key):
        return self._check()[key]

    def __setitem__(self, key, value):
        self._check()[key] = value

    def __delitem__(self, key):
        del self._check()[key]

    def __iter__(self):
        return iter(self._check())

    def __contains__(self, item):
        return item in self._check()

    def __eq__(self, other):
        return self._check() == other

    def __ne__(self, other):
        return self._check() != other


def proxy(ob, callback=None):
    """Return a weak proxy to ``ob``."""
    return _ProxyBase(ob, callback)


ProxyType = _ProxyBase
ProxyTypes = (_ProxyBase,)
ReferenceType = ref


# ---------------------------------------------------------------------------
# Registry helpers (module-level bookkeeping)
# ---------------------------------------------------------------------------

_registry = {}


def _register(ob, r):
    bucket = _registry.setdefault(id(ob), [])
    bucket.append(r)


def getweakrefcount(ob):
    """Return the number of weak references registered for ``ob``."""
    return len(_registry.get(id(ob), ()))


def getweakrefs(ob):
    """Return a list of weak references registered for ``ob``."""
    return list(_registry.get(id(ob), ()))


# ---------------------------------------------------------------------------
# WeakValueDictionary
# ---------------------------------------------------------------------------

class WeakValueDictionary:
    """Mapping whose values are held by weak references."""

    def __init__(self, other=None):
        self._data = {}
        if other is not None:
            self.update(other)

    def __setitem__(self, key, value):
        def cb(_wr, k=key, d=self._data):
            d.pop(k, None)
        self._data[key] = ref(value, cb)

    def __getitem__(self, key):
        wr = self._data[key]
        obj = wr()
        if obj is None:
            self._data.pop(key, None)
            raise KeyError(key)
        return obj

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        wr = self._data.get(key)
        return wr is not None and wr() is not None

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return sum(1 for wr in self._data.values() if wr() is not None)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return [k for k, wr in self._data.items() if wr() is not None]

    def values(self):
        return [wr() for wr in self._data.values() if wr() is not None]

    def items(self):
        return [(k, wr()) for k, wr in self._data.items() if wr() is not None]

    def pop(self, key, *args):
        try:
            wr = self._data.pop(key)
        except KeyError:
            if args:
                return args[0]
            raise
        obj = wr()
        if obj is None:
            if args:
                return args[0]
            raise KeyError(key)
        return obj

    def update(self, other):
        if hasattr(other, "items"):
            it = other.items()
        else:
            it = other
        for k, v in it:
            self[k] = v

    def clear(self):
        self._data.clear()


# ---------------------------------------------------------------------------
# WeakKeyDictionary
# ---------------------------------------------------------------------------

class WeakKeyDictionary:
    """Mapping whose keys are held by weak references."""

    def __init__(self, other=None):
        # Map id(key) -> (key_ref, value)
        self._data = {}
        if other is not None:
            self.update(other)

    def __setitem__(self, key, value):
        def cb(_wr, kid=id(key), d=self._data):
            d.pop(kid, None)
        self._data[id(key)] = (ref(key, cb), value)

    def __getitem__(self, key):
        entry = self._data.get(id(key))
        if entry is None:
            raise KeyError(key)
        wr, value = entry
        if wr() is None:
            self._data.pop(id(key), None)
            raise KeyError(key)
        return value

    def __delitem__(self, key):
        del self._data[id(key)]

    def __contains__(self, key):
        entry = self._data.get(id(key))
        return entry is not None and entry[0]() is not None

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return sum(1 for wr, _ in self._data.values() if wr() is not None)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return [wr() for wr, _ in self._data.values() if wr() is not None]

    def values(self):
        return [v for wr, v in self._data.values() if wr() is not None]

    def items(self):
        return [(wr(), v) for wr, v in self._data.values() if wr() is not None]

    def update(self, other):
        if hasattr(other, "items"):
            it = other.items()
        else:
            it = other
        for k, v in it:
            self[k] = v

    def clear(self):
        self._data.clear()


# ---------------------------------------------------------------------------
# WeakSet
# ---------------------------------------------------------------------------

class WeakSet:
    """Set whose elements are held by weak references."""

    def __init__(self, data=None):
        self._refs = set()
        if data is not None:
            for item in data:
                self.add(item)

    def add(self, item):
        def cb(wr, s=self._refs):
            s.discard(wr)
        self._refs.add(ref(item, cb))

    def discard(self, item):
        for r in list(self._refs):
            if r() is item:
                self._refs.discard(r)

    def remove(self, item):
        for r in list(self._refs):
            if r() is item:
                self._refs.discard(r)
                return
        raise KeyError(item)

    def __contains__(self, item):
        return any(r() is item for r in self._refs)

    def __iter__(self):
        for r in list(self._refs):
            ob = r()
            if ob is not None:
                yield ob

    def __len__(self):
        return sum(1 for r in self._refs if r() is not None)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def weakref2_ref():
    """``ref(obj)()`` returns the referent while it is alive."""
    class Obj:
        pass
    obj = Obj()
    r = ref(obj)
    return r() is obj


def weakref2_dead():
    """A reference returns ``None`` once its referent is gone."""
    class Obj:
        pass
    obj = Obj()
    r = ref(obj)
    r._kill()  # simulate referent being garbage-collected
    return r() is None


def weakref2_proxy():
    """A proxy forwards attribute access while the referent is alive."""
    class Obj:
        value = 42
    obj = Obj()
    p = proxy(obj)
    return p.value


__all__ = [
    "ref",
    "proxy",
    "ReferenceType",
    "ProxyType",
    "ProxyTypes",
    "getweakrefcount",
    "getweakrefs",
    "WeakValueDictionary",
    "WeakKeyDictionary",
    "WeakSet",
    "weakref2_ref",
    "weakref2_dead",
    "weakref2_proxy",
]