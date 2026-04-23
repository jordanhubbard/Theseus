"""
theseus_weakref - Clean-room weak reference simulation.
No import of weakref or gc.
"""


class WeakRef:
    """Simulated weak reference. Holds a strong ref internally."""

    def __init__(self, obj, callback=None):
        self._obj = obj
        self._callback = callback
        self._dead = False

    def __call__(self):
        if self._dead:
            return None
        return self._obj

    def __repr__(self):
        if self._dead:
            return f'<WeakRef dead>'
        return f'<WeakRef to {type(self._obj).__name__}>'

    def _kill(self):
        self._dead = True
        obj = self._obj
        self._obj = None
        if self._callback is not None:
            self._callback(self)


class Finalizer:
    """Register a callback to be called when the finalizer fires."""

    def __init__(self, obj, func, *args, **kwargs):
        self._obj = obj
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._alive = True

    def __call__(self):
        if self._alive:
            self._alive = False
            return self._func(*self._args, **self._kwargs)

    def cancel(self):
        self._alive = False

    @property
    def alive(self):
        return self._alive


def ref(obj, callback=None):
    return WeakRef(obj, callback)


def finalize(obj, func, *args, **kwargs):
    return Finalizer(obj, func, *args, **kwargs)


def weakref_alive():
    class _Obj:
        pass
    o = _Obj()
    r = ref(o)
    return r() is not None


def weakref_callable():
    class _Box:
        def __init__(self, v):
            self.value = v
    o = _Box(42)
    r = ref(o)
    return r().value


def weakref_finalize_called():
    called = []

    class _Obj:
        pass

    o = _Obj()
    fin = finalize(o, called.append, True)
    fin()
    return bool(called)
