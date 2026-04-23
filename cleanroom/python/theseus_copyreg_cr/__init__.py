"""
theseus_copyreg_cr — Clean-room copyreg module.
No import of the standard `copyreg` module.
"""

dispatch_table = {}
_reconstructors = {}


def pickle(ob_type, reduce_func, constructor=None):
    """Register a reducer for ob_type."""
    if constructor is not None:
        _check_constructor(constructor)
    dispatch_table[ob_type] = reduce_func


def constructor(object):
    """Register object as a valid constructor callable."""
    _check_constructor(object)
    return object


def _check_constructor(object):
    if not callable(object):
        raise TypeError("argument must be callable")


def _reduce_ex(self, protocol):
    return _reconstructors, (type(self), object, None)


def _reconstructor(cls, base, state):
    if base is object:
        obj = object.__new__(cls)
    else:
        obj = base.__new__(cls, state)
    if base.__init__ != object.__init__:
        base.__init__(obj, state)
    return obj


_reconstructors[_reconstructor.__name__] = _reconstructor


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def copyreg2_dispatch_table():
    """dispatch_table is a dict; returns True."""
    return isinstance(dispatch_table, dict)


def copyreg2_pickle():
    """pickle() registers a custom reducer; returns True."""
    class MyClass:
        pass

    def my_reduce(obj):
        return (MyClass, ())

    pickle(MyClass, my_reduce)
    return MyClass in dispatch_table


def copyreg2_constructor():
    """constructor() registers a callable; returns True."""
    def my_constructor(state):
        return object()

    result = constructor(my_constructor)
    return callable(result)


__all__ = [
    'dispatch_table', 'pickle', 'constructor',
    '_reconstructor', '_reduce_ex',
    'copyreg2_dispatch_table', 'copyreg2_pickle', 'copyreg2_constructor',
]
