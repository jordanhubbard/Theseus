"""
theseus_operator_cr — Clean-room operator module.
No import of the standard `operator` module.
"""


# Comparison operators
def lt(a, b): return a < b
def le(a, b): return a <= b
def eq(a, b): return a == b
def ne(a, b): return a != b
def ge(a, b): return a >= b
def gt(a, b): return a > b

# Logical operators
def not_(a): return not a
def truth(a): return bool(a)
def is_(a, b): return a is b
def is_not(a, b): return a is not b

# Arithmetic operators
def abs(a): return __builtins__['abs'](a) if isinstance(__builtins__, dict) else __import__('builtins').abs(a)
def add(a, b): return a + b
def floordiv(a, b): return a // b
def index(a): return a.__index__()
def inv(a): return ~a
invert = inv
def lshift(a, b): return a << b
def mod(a, b): return a % b
def mul(a, b): return a * b
def matmul(a, b): return a @ b
def neg(a): return -a
def pos(a): return +a
def pow(a, b): return a ** b
def rshift(a, b): return a >> b
def sub(a, b): return a - b
def truediv(a, b): return a / b

# Bitwise operators
def and_(a, b): return a & b
def or_(a, b): return a | b
def xor(a, b): return a ^ b

# Sequence operators
def concat(a, b): return a + b
def contains(a, b): return b in a
def delitem(a, b): del a[b]
def getitem(a, b): return a[b]
def setitem(a, b, c): a[b] = c
def length_hint(obj, default=0):
    try:
        return len(obj)
    except TypeError:
        try:
            return obj.__length_hint__()
        except AttributeError:
            return default

# Augmented assignment operators
def iadd(a, b): a += b; return a
def iand(a, b): a &= b; return a
def iconcat(a, b): a += b; return a
def ifloordiv(a, b): a //= b; return a
def ilshift(a, b): a <<= b; return a
def imod(a, b): a %= b; return a
def imul(a, b): a *= b; return a
def imatmul(a, b): a @= b; return a
def ior(a, b): a |= b; return a
def ipow(a, b): a **= b; return a
def irshift(a, b): a >>= b; return a
def isub(a, b): a -= b; return a
def itruediv(a, b): a /= b; return a
def ixor(a, b): a ^= b; return a


class itemgetter:
    """Return a callable that fetches item(s) from its operand."""

    def __init__(self, *items):
        self._items = items

    def __call__(self, obj):
        if len(self._items) == 1:
            return obj[self._items[0]]
        return tuple(obj[i] for i in self._items)

    def __repr__(self):
        items = ', '.join(repr(i) for i in self._items)
        return f'operator.itemgetter({items})'


class attrgetter:
    """Return a callable that fetches attr(s) from its operand."""

    def __init__(self, *attrs):
        self._attrs = attrs

    def __call__(self, obj):
        def _get(obj, attr):
            for name in attr.split('.'):
                obj = getattr(obj, name)
            return obj
        if len(self._attrs) == 1:
            return _get(obj, self._attrs[0])
        return tuple(_get(obj, a) for a in self._attrs)

    def __repr__(self):
        attrs = ', '.join(repr(a) for a in self._attrs)
        return f'operator.attrgetter({attrs})'


class methodcaller:
    """Return a callable that calls method with given args."""

    def __init__(self, name, /, *args, **kwargs):
        self._name = name
        self._args = args
        self._kwargs = kwargs

    def __call__(self, obj):
        return getattr(obj, self._name)(*self._args, **self._kwargs)

    def __repr__(self):
        args = [repr(self._name)]
        args.extend(repr(a) for a in self._args)
        args.extend(f'{k}={v!r}' for k, v in self._kwargs.items())
        return f'operator.methodcaller({", ".join(args)})'


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def operator2_add():
    """add(3, 4) == 7; returns 7."""
    return add(3, 4)


def operator2_itemgetter():
    """itemgetter(1)(['a','b','c']) == 'b'; returns 'b'."""
    return itemgetter(1)(['a', 'b', 'c'])


def operator2_attrgetter():
    """attrgetter('__class__.__name__') of list returns 'list'; returns 'list'."""
    return attrgetter('__class__.__name__')([])


__all__ = [
    'lt', 'le', 'eq', 'ne', 'ge', 'gt',
    'not_', 'truth', 'is_', 'is_not',
    'abs', 'add', 'floordiv', 'index', 'inv', 'invert', 'lshift', 'mod',
    'mul', 'matmul', 'neg', 'pos', 'pow', 'rshift', 'sub', 'truediv',
    'and_', 'or_', 'xor',
    'concat', 'contains', 'delitem', 'getitem', 'setitem', 'length_hint',
    'iadd', 'iand', 'iconcat', 'ifloordiv', 'ilshift', 'imod', 'imul',
    'imatmul', 'ior', 'ipow', 'irshift', 'isub', 'itruediv', 'ixor',
    'itemgetter', 'attrgetter', 'methodcaller',
    'operator2_add', 'operator2_itemgetter', 'operator2_attrgetter',
]
