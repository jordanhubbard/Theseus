"""theseus_copy_cr — clean-room reimplementation of Python's copy module.

Provides shallow and deep copy operations without importing the original
`copy` module. Supports the same protocols (__copy__, __deepcopy__,
__reduce_ex__) for user-defined classes.

The public ``copy2_*`` symbols are zero-argument self-test functions that
return ``True`` when the corresponding behavior of this module works
correctly. Programmatic users should call :func:`shallow_copy` and
:func:`deep_copy` directly.
"""

__all__ = [
    "Error", "error",
    "shallow_copy", "deep_copy",
    "copy2_shallow", "copy2_deep", "copy2_error",
]


class Error(Exception):
    """Raised when an object cannot be copied."""
    pass


# Backward-compat alias (mirrors original copy.error == copy.Error).
error = Error


# ---------------------------------------------------------------------------
# Atomic-type detection
# ---------------------------------------------------------------------------

_ATOMIC_TYPES = frozenset({
    type(None),
    int,
    float,
    bool,
    complex,
    str,
    bytes,
    type,
    range,
    slice,
    type(Ellipsis),
    type(NotImplemented),
})


def _is_atomic_class(cls):
    if cls in _ATOMIC_TYPES:
        return True
    name = getattr(cls, "__name__", "")
    if name in (
        "function", "builtin_function_or_method", "method",
        "method-wrapper", "wrapper_descriptor", "method_descriptor",
        "module", "classmethod_descriptor", "getset_descriptor",
        "member_descriptor", "mappingproxy", "code", "ellipsis",
    ):
        return True
    return False


# ---------------------------------------------------------------------------
# Shallow copy
# ---------------------------------------------------------------------------

def shallow_copy(x):
    """Return a shallow copy of ``x``."""
    cls = type(x)

    if _is_atomic_class(cls):
        return x

    if cls is list:
        return list(x)
    if cls is dict:
        return dict(x)
    if cls is tuple:
        return x
    if cls is set:
        return set(x)
    if cls is frozenset:
        return x
    if cls is bytearray:
        return bytearray(x)

    if isinstance(x, list) and not _has_custom_dunder(cls):
        try:
            return cls(x)
        except Exception:
            pass
    if isinstance(x, dict) and not _has_custom_dunder(cls):
        try:
            return cls(x)
        except Exception:
            pass

    copier = getattr(cls, "__copy__", None)
    if copier is not None:
        try:
            return copier(x)
        except TypeError:
            return x.__copy__()

    rv = _safe_reduce(x)
    if rv is None:
        raise Error("un(shallow)copyable object of type %s" % cls)

    if isinstance(rv, str):
        return x

    return _reconstruct(x, None, rv)


def _has_custom_dunder(cls):
    return ("__copy__" in cls.__dict__) or ("__deepcopy__" in cls.__dict__)


# ---------------------------------------------------------------------------
# Deep copy
# ---------------------------------------------------------------------------

_NIL = object()


def deep_copy(x, memo=None, _nil=_NIL):
    """Return a deep copy of ``x``."""
    if memo is None:
        memo = {}

    key = id(x)
    cached = memo.get(key, _nil)
    if cached is not _nil:
        return cached

    cls = type(x)

    if _is_atomic_class(cls):
        return x

    if cls is list:
        y = []
        memo[key] = y
        append = y.append
        for item in x:
            append(deep_copy(item, memo))
        _keep_alive(x, memo)
        return y

    if cls is dict:
        y = {}
        memo[key] = y
        for k, v in x.items():
            y[deep_copy(k, memo)] = deep_copy(v, memo)
        _keep_alive(x, memo)
        return y

    if cls is tuple:
        if not x:
            return x
        items = [deep_copy(item, memo) for item in x]
        cached = memo.get(key, _nil)
        if cached is not _nil:
            return cached
        for orig, new in zip(x, items):
            if orig is not new:
                y = tuple(items)
                memo[key] = y
                _keep_alive(x, memo)
                return y
        return x

    if cls is set:
        y = set()
        memo[key] = y
        for item in x:
            y.add(deep_copy(item, memo))
        _keep_alive(x, memo)
        return y

    if cls is frozenset:
        items = [deep_copy(item, memo) for item in x]
        for orig, new in zip(x, items):
            if orig is not new:
                y = frozenset(items)
                memo[key] = y
                _keep_alive(x, memo)
                return y
        return x

    if cls is bytearray:
        y = bytearray(x)
        memo[key] = y
        _keep_alive(x, memo)
        return y

    copier = getattr(cls, "__deepcopy__", None)
    if copier is not None:
        try:
            y = copier(x, memo)
        except TypeError:
            y = x.__deepcopy__(memo)
        if y is not x:
            memo[key] = y
            _keep_alive(x, memo)
        return y

    rv = _safe_reduce(x)
    if rv is None:
        raise Error("un(deep)copyable object of type %s" % cls)

    if isinstance(rv, str):
        return x

    y = _reconstruct(x, memo, rv)
    if y is not x:
        memo[key] = y
        _keep_alive(x, memo)
    return y


def _keep_alive(x, memo):
    try:
        memo[id(memo)].append(x)
    except KeyError:
        memo[id(memo)] = [x]


# ---------------------------------------------------------------------------
# Reduce / reconstruct helpers
# ---------------------------------------------------------------------------

def _safe_reduce(x):
    reductor = getattr(x, "__reduce_ex__", None)
    if reductor is not None:
        try:
            return reductor(4)
        except Exception:
            pass
    reductor = getattr(x, "__reduce__", None)
    if reductor is not None:
        try:
            return reductor()
        except Exception:
            pass
    return None


def _reconstruct(x, memo, rv):
    if not isinstance(rv, tuple):
        return x

    n = len(rv)
    func = rv[0]
    args = rv[1] if n > 1 else ()
    state = rv[2] if n > 2 else None
    listiter = rv[3] if n > 3 else None
    dictiter = rv[4] if n > 4 else None
    state_setter = rv[5] if n > 5 else None

    deep = memo is not None

    if args is None:
        args = ()
    if deep and args:
        args = tuple(deep_copy(a, memo) for a in args)

    y = func(*args)

    if deep and x is not None:
        memo[id(x)] = y

    if listiter is not None:
        if deep:
            for item in listiter:
                y.append(deep_copy(item, memo))
        else:
            for item in listiter:
                y.append(item)

    if dictiter is not None:
        if deep:
            for k, v in dictiter:
                y[deep_copy(k, memo)] = deep_copy(v, memo)
        else:
            for k, v in dictiter:
                y[k] = v

    if state is not None:
        if deep:
            state = deep_copy(state, memo)
        if state_setter is not None:
            state_setter(y, state)
        else:
            _apply_state(y, state)

    return y


def _apply_state(y, state):
    setstate = getattr(y, "__setstate__", None)
    if setstate is not None:
        setstate(state)
        return

    slotstate = None
    if isinstance(state, tuple) and len(state) == 2:
        state, slotstate = state

    if state is not None:
        d = getattr(y, "__dict__", None)
        if d is not None and isinstance(state, dict):
            d.update(state)
        elif isinstance(state, dict):
            for k, v in state.items():
                setattr(y, k, v)

    if slotstate is not None:
        for k, v in slotstate.items():
            setattr(y, k, v)


# ---------------------------------------------------------------------------
# Public ``copy2_*`` self-test API (zero-argument, returns True)
# ---------------------------------------------------------------------------

def copy2_shallow():
    """Self-test the shallow-copy behavior. Returns ``True`` on success."""
    # Primitive — returned as-is.
    if shallow_copy(42) != 42:
        return False
    if shallow_copy("abc") != "abc":
        return False
    if shallow_copy(None) is not None:
        return False

    # List — new container, shared inner refs.
    inner = [1, 2, 3]
    a = [inner, "x", 7]
    b = shallow_copy(a)
    if a is b:
        return False
    if a != b:
        return False
    if b[0] is not inner:
        return False

    # Dict — new container, shared values.
    payload = {"k": [10]}
    da = {"a": 1, "b": payload}
    db = shallow_copy(da)
    if da is db:
        return False
    if da != db:
        return False
    if db["b"] is not payload:
        return False

    # Tuple — immutable, identity preserved.
    t = (1, 2, 3)
    if shallow_copy(t) is not t:
        return False

    # Set — new container.
    s = {1, 2, 3}
    s2 = shallow_copy(s)
    if s is s2 or s != s2:
        return False

    # bytearray — new container.
    ba = bytearray(b"hello")
    bb = shallow_copy(ba)
    if ba is bb or ba != bb:
        return False

    # __copy__ protocol.
    class WithCopy:
        def __init__(self, v):
            self.v = v
            self.copied = False

        def __copy__(self):
            n = WithCopy(self.v)
            n.copied = True
            return n

    wc = WithCopy(5)
    wc2 = shallow_copy(wc)
    if not wc2.copied or wc2.v != 5 or wc2 is wc:
        return False

    return True


def copy2_deep():
    """Self-test the deep-copy behavior. Returns ``True`` on success."""
    # Primitive — returned as-is.
    if deep_copy(42) != 42:
        return False
    if deep_copy("abc") != "abc":
        return False

    # Nested list — independent inner copy.
    inner = [1, 2, 3]
    a = [inner, "x", 7]
    b = deep_copy(a)
    if a is b or a != b:
        return False
    if b[0] is inner:
        return False
    if b[0] != inner:
        return False

    # Mutating the deep copy must not affect the original.
    b[0].append(99)
    if 99 in inner:
        return False

    # Nested dict — independent inner copy.
    payload = {"k": [10]}
    da = {"a": 1, "b": payload}
    db = deep_copy(da)
    if db["b"] is payload:
        return False
    if db["b"] != payload:
        return False

    # Cycle handling.
    cyc = []
    cyc.append(cyc)
    cyc2 = deep_copy(cyc)
    if cyc2 is cyc:
        return False
    if cyc2[0] is not cyc2:
        return False

    # Shared-reference handling: two refs to the same list become one
    # shared list in the copy as well.
    shared = [0]
    pair = [shared, shared]
    pair_copy = deep_copy(pair)
    if pair_copy[0] is not pair_copy[1]:
        return False
    if pair_copy[0] is shared:
        return False

    # __deepcopy__ protocol.
    class WithDeep:
        def __init__(self, v):
            self.v = v
            self.deeped = False

        def __deepcopy__(self, memo):
            n = WithDeep(deep_copy(self.v, memo))
            n.deeped = True
            return n

    wd = WithDeep([1, 2])
    wd2 = deep_copy(wd)
    if not wd2.deeped or wd2.v == [] or wd2 is wd:
        return False
    if wd2.v is wd.v:
        return False

    return True


def copy2_error():
    """Self-test the :class:`Error` type. Returns ``True`` on success."""
    # Error must be an Exception subclass.
    if not isinstance(Error, type):
        return False
    if not issubclass(Error, Exception):
        return False

    # error alias must point to the same class.
    if error is not Error:
        return False

    # It must be raisable and catchable.
    try:
        raise Error("boom")
    except Error as e:
        if str(e) != "boom":
            return False
    except Exception:
        return False
    else:
        return False

    # An object with no copy support must raise Error from shallow_copy.
    class Unc:
        __slots__ = ()

        def __reduce_ex__(self, protocol):
            raise TypeError("cannot reduce")

        def __reduce__(self):
            raise TypeError("cannot reduce")

    u = Unc()
    raised = False
    try:
        shallow_copy(u)
    except Error:
        raised = True
    except Exception:
        return False
    if not raised:
        return False

    # Same object must raise Error from deep_copy.
    raised = False
    try:
        deep_copy(u)
    except Error:
        raised = True
    except Exception:
        return False
    if not raised:
        return False

    return True