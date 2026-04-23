"""
theseus_copy_cr — Clean-room copy module.
No import of the standard `copy` module.
"""

import types as _types


class Error(Exception):
    pass


error = Error


def copy(x):
    """Shallow copy of x."""
    cls = type(x)

    # Check for __copy__ method
    copier = getattr(cls, '__copy__', None)
    if copier is not None:
        return copier(x)

    # Check for __reduce_ex__ / __reduce__
    reductor = getattr(cls, '__reduce_ex__', None)
    rv = None
    if reductor is not None:
        rv = reductor(x, 4)
    else:
        reductor = getattr(cls, '__reduce__', None)
        if reductor is not None:
            rv = reductor(x)

    if isinstance(x, type):
        return x

    # Built-in atomic types
    if isinstance(x, (int, float, bool, bytes, str, type(None),
                      type(Ellipsis), type(NotImplemented))):
        return x

    # List
    if isinstance(x, list):
        return x.copy()

    # Dict
    if isinstance(x, dict):
        return x.copy()

    # Tuple (immutable, return same)
    if isinstance(x, tuple):
        return x

    # Set/frozenset
    if isinstance(x, (set, frozenset)):
        return x.copy()

    # Try __copy__
    reductor = getattr(x, '__copy__', None)
    if reductor is not None:
        return reductor()

    # Fall back to __reduce_ex__
    cls = type(x)
    if hasattr(cls, '__copy__'):
        return cls.__copy__(x)

    # Generic: recreate via __dict__
    if hasattr(x, '__dict__'):
        y = x.__class__.__new__(x.__class__)
        y.__dict__.update(x.__dict__)
        return y

    raise Error("cannot copy object of type %s" % type(x).__name__)


def deepcopy(x, memo=None, _nil=[]):
    """Deep copy of x."""
    if memo is None:
        memo = {}

    d = id(x)
    y = memo.get(d, _nil)
    if y is not _nil:
        return y

    cls = type(x)

    # Atomic types - return as-is
    if isinstance(x, (int, float, bool, bytes, str, type(None),
                      type(Ellipsis), type(NotImplemented))):
        return x

    # Type objects
    if isinstance(x, type):
        return x

    # Check for __deepcopy__
    copier = getattr(x, '__deepcopy__', None)
    if copier is not None:
        y = copier(memo)
        memo[d] = y
        return y

    # List
    if isinstance(x, list):
        y = []
        memo[d] = y
        for item in x:
            y.append(deepcopy(item, memo))
        return y

    # Dict
    if isinstance(x, dict):
        y = {}
        memo[d] = y
        for k, v in x.items():
            y[deepcopy(k, memo)] = deepcopy(v, memo)
        return y

    # Tuple
    if isinstance(x, tuple):
        items = [deepcopy(item, memo) for item in x]
        y = type(x)(items)
        memo[d] = y
        return y

    # Set
    if isinstance(x, (set, frozenset)):
        y = type(x)(deepcopy(item, memo) for item in x)
        memo[d] = y
        return y

    # Generic object with __dict__
    if hasattr(x, '__dict__'):
        y = x.__class__.__new__(x.__class__)
        memo[d] = y
        for k, v in x.__dict__.items():
            setattr(y, k, deepcopy(v, memo))
        if hasattr(x, '__slots__'):
            for slot in x.__slots__:
                if hasattr(x, slot):
                    setattr(y, slot, deepcopy(getattr(x, slot), memo))
        return y

    # Try __reduce_ex__
    reductor = getattr(cls, '__reduce_ex__', None)
    if reductor is not None:
        rv = reductor(x, 4)
        if isinstance(rv, str):
            return x
        return _reconstruct(x, memo, *rv)

    raise Error("cannot deep copy object of type %s" % type(x).__name__)


def _reconstruct(x, memo, func, args, state=None, listiter=None, dictiter=None, state_setter=None, **kwargs):
    y = func(*args)
    memo[id(x)] = y
    if state is not None:
        if state_setter is not None:
            state_setter(y, deepcopy(state, memo))
        elif hasattr(y, '__setstate__'):
            y.__setstate__(deepcopy(state, memo))
        else:
            state = deepcopy(state, memo)
            if hasattr(y, '__dict__'):
                y.__dict__.update(state)
    if listiter is not None:
        for item in listiter:
            y.append(deepcopy(item, memo))
    if dictiter is not None:
        for k, v in dictiter:
            y[deepcopy(k, memo)] = deepcopy(v, memo)
    return y


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def copy2_shallow():
    """copy() creates shallow copy of a list; returns True."""
    original = [[1, 2], [3, 4]]
    shallow = copy(original)
    return shallow == original and shallow is not original and shallow[0] is original[0]


def copy2_deep():
    """deepcopy() creates independent deep copy; returns True."""
    original = [[1, 2], [3, 4]]
    deep = deepcopy(original)
    return deep == original and deep is not original and deep[0] is not original[0]


def copy2_error():
    """copy() on basic types works; returns True."""
    return copy(42) == 42 and copy('hello') == 'hello' and copy([1, 2, 3]) == [1, 2, 3]


__all__ = [
    'copy', 'deepcopy', 'Error', 'error',
    'copy2_shallow', 'copy2_deep', 'copy2_error',
]
