"""
theseus_operator_cr3 - Clean-room implementation of operator utilities.
Do NOT import the `operator` module.
"""

# --- Core logical/membership functions ---

def truth(obj):
    """Return True if obj is truthy, False otherwise. Equivalent to bool(obj)."""
    return bool(obj)


def not_(obj):
    """Return not obj — logical negation."""
    return not obj


def contains(a, b):
    """Return b in a (equivalent to __contains__)."""
    return b in a


# --- Arithmetic operators ---

def add(a, b):
    """Return a + b."""
    return a + b


def sub(a, b):
    """Return a - b."""
    return a - b


def mul(a, b):
    """Return a * b."""
    return a * b


def truediv(a, b):
    """Return a / b."""
    return a / b


def floordiv(a, b):
    """Return a // b."""
    return a // b


def mod(a, b):
    """Return a % b."""
    return a % b


def pow(a, b):
    """Return a ** b."""
    return a ** b


def neg(a):
    """Return -a."""
    return -a


def pos(a):
    """Return +a."""
    return +a


def abs(a):
    """Return abs(a)."""
    return __builtins__['abs'](a) if isinstance(__builtins__, dict) else __builtins__.abs(a) if hasattr(__builtins__, 'abs') else _abs(a)


def _abs(a):
    if a < 0:
        return -a
    return a


# Override abs with a clean implementation
def abs(a):
    """Return the absolute value of a."""
    if hasattr(a, '__abs__'):
        return a.__abs__()
    if a < 0:
        return -a
    return a


# --- Bitwise operators ---

def and_(a, b):
    """Return a & b."""
    return a & b


def or_(a, b):
    """Return a | b."""
    return a | b


def xor(a, b):
    """Return a ^ b."""
    return a ^ b


def lshift(a, b):
    """Return a << b."""
    return a << b


def rshift(a, b):
    """Return a >> b."""
    return a >> b


# --- Comparison operators ---

def eq(a, b):
    """Return a == b."""
    return a == b


def ne(a, b):
    """Return a != b."""
    return a != b


def lt(a, b):
    """Return a < b."""
    return a < b


def le(a, b):
    """Return a <= b."""
    return a <= b


def gt(a, b):
    """Return a > b."""
    return a > b


def ge(a, b):
    """Return a >= b."""
    return a >= b


# --- Item/attribute access ---

def getitem(a, b):
    """Return a[b]."""
    return a[b]


def setitem(a, b, c):
    """Set a[b] = c."""
    a[b] = c


def delitem(a, b):
    """Delete a[b]."""
    del a[b]


# --- Higher-order helpers ---

class attrgetter:
    """
    Return a callable object that fetches the given attribute(s) from its operand.
    After f = attrgetter('name'), the call f(r) returns r.name.
    After g = attrgetter('name', 'date'), the call g(r) returns (r.name, r.date).
    Dotted attribute paths are supported: attrgetter('a.b.c')(r) returns r.a.b.c.
    """

    def __init__(self, attr, *attrs):
        self._attrs = (attr,) + attrs

    def _resolve(self, obj, attr):
        parts = attr.split('.')
        for part in parts:
            obj = getattr(obj, part)
        return obj

    def __call__(self, obj):
        if len(self._attrs) == 1:
            return self._resolve(obj, self._attrs[0])
        return tuple(self._resolve(obj, attr) for attr in self._attrs)


class itemgetter:
    """
    Return a callable object that fetches the given item(s) from its operand.
    After f = itemgetter(2), the call f(r) returns r[2].
    After g = itemgetter(2, 5, 3), the call g(r) returns (r[2], r[5], r[3]).
    """

    def __init__(self, item, *items):
        self._items = (item,) + items

    def __call__(self, obj):
        if len(self._items) == 1:
            return obj[self._items[0]]
        return tuple(obj[item] for item in self._items)


class methodcaller:
    """
    Return a callable object that calls the given method on its operand.
    After f = methodcaller('name'), the call f(r) returns r.name().
    After g = methodcaller('name', 'date', foo=1), the call g(r) returns
    r.name('date', foo=1).
    """

    def __init__(self, name, /, *args, **kwargs):
        self._name = name
        self._args = args
        self._kwargs = kwargs

    def __call__(self, obj):
        return getattr(obj, self._name)(*self._args, **self._kwargs)


# --- Zero-arg invariant functions ---

def operator3_truth():
    """Invariant: truth([1, 2]) == True"""
    return truth([1, 2]) == True


def operator3_not_():
    """Invariant: not_('') == True (empty string is falsy)"""
    return not_('') == True


def operator3_contains():
    """Invariant: contains([1, 2, 3], 2) == True"""
    return contains([1, 2, 3], 2) == True