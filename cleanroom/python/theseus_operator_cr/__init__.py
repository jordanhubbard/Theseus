"""Clean-room implementation of a subset of the operator module."""


# Arithmetic operators
def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


def truediv(a, b):
    return a / b


def floordiv(a, b):
    return a // b


def mod(a, b):
    return a % b


def pow(a, b):
    return a ** b


def neg(a):
    return -a


def pos(a):
    return +a


def abs(a):
    if a < 0:
        return -a
    return a


# Bitwise operators
def and_(a, b):
    return a & b


def or_(a, b):
    return a | b


def xor(a, b):
    return a ^ b


def invert(a):
    return ~a


def lshift(a, b):
    return a << b


def rshift(a, b):
    return a >> b


# Comparison operators
def lt(a, b):
    return a < b


def le(a, b):
    return a <= b


def eq(a, b):
    return a == b


def ne(a, b):
    return a != b


def gt(a, b):
    return a > b


def ge(a, b):
    return a >= b


# Logical operators
def not_(a):
    return not a


def truth(a):
    return True if a else False


def is_(a, b):
    return a is b


def is_not(a, b):
    return a is not b


# Sequence operators
def concat(a, b):
    return a + b


def contains(a, b):
    return b in a


def countOf(a, b):
    count = 0
    for item in a:
        if item == b:
            count += 1
    return count


def indexOf(a, b):
    i = 0
    for item in a:
        if item == b:
            return i
        i += 1
    raise ValueError("sequence.index(x): x not in sequence")


def getitem(a, b):
    return a[b]


def setitem(a, b, c):
    a[b] = c


def delitem(a, b):
    del a[b]


# In-place operators
def iadd(a, b):
    a += b
    return a


def isub(a, b):
    a -= b
    return a


def imul(a, b):
    a *= b
    return a


def itruediv(a, b):
    a /= b
    return a


def ifloordiv(a, b):
    a //= b
    return a


def imod(a, b):
    a %= b
    return a


def ipow(a, b):
    a **= b
    return a


def iand(a, b):
    a &= b
    return a


def ior(a, b):
    a |= b
    return a


def ixor(a, b):
    a ^= b
    return a


def ilshift(a, b):
    a <<= b
    return a


def irshift(a, b):
    a >>= b
    return a


def iconcat(a, b):
    a += b
    return a


# itemgetter, attrgetter, methodcaller
class itemgetter:
    """Return a callable that fetches the given item(s) from its operand."""

    __slots__ = ("_items", "_single")

    def __init__(self, item, *items):
        if not items:
            self._items = (item,)
            self._single = True
        else:
            self._items = (item,) + items
            self._single = False

    def __call__(self, obj):
        if self._single:
            return obj[self._items[0]]
        return tuple(obj[i] for i in self._items)

    def __repr__(self):
        return "%s(%s)" % (
            type(self).__name__,
            ", ".join(repr(i) for i in self._items),
        )


class attrgetter:
    """Return a callable that fetches the given attribute(s) from its operand.

    Dotted attribute names are supported: attrgetter('a.b') is equivalent to
    lambda x: x.a.b.
    """

    __slots__ = ("_attrs", "_single")

    def __init__(self, attr, *attrs):
        if not isinstance(attr, str):
            raise TypeError("attribute name must be a string")
        for a in attrs:
            if not isinstance(a, str):
                raise TypeError("attribute name must be a string")
        all_attrs = (attr,) + attrs
        self._attrs = tuple(a.split(".") for a in all_attrs)
        self._single = len(all_attrs) == 1

    def _resolve(self, obj, parts):
        for p in parts:
            obj = getattr(obj, p)
        return obj

    def __call__(self, obj):
        if self._single:
            return self._resolve(obj, self._attrs[0])
        return tuple(self._resolve(obj, parts) for parts in self._attrs)

    def __repr__(self):
        return "%s(%s)" % (
            type(self).__name__,
            ", ".join(repr(".".join(parts)) for parts in self._attrs),
        )


class methodcaller:
    """Return a callable that calls the given method on its operand."""

    __slots__ = ("_name", "_args", "_kwargs")

    def __init__(self, name, *args, **kwargs):
        if not isinstance(name, str):
            raise TypeError("method name must be a string")
        self._name = name
        self._args = args
        self._kwargs = kwargs

    def __call__(self, obj):
        return getattr(obj, self._name)(*self._args, **self._kwargs)

    def __repr__(self):
        parts = [repr(self._name)]
        parts.extend(repr(a) for a in self._args)
        parts.extend("%s=%r" % (k, v) for k, v in self._kwargs.items())
        return "%s(%s)" % (type(self).__name__, ", ".join(parts))


# Aliases matching the stdlib module naming
__add__ = add
__sub__ = sub
__mul__ = mul
__truediv__ = truediv
__floordiv__ = floordiv
__mod__ = mod
__pow__ = pow
__neg__ = neg
__pos__ = pos
__abs__ = abs
__and__ = and_
__or__ = or_
__xor__ = xor
__invert__ = invert
__lshift__ = lshift
__rshift__ = rshift
__lt__ = lt
__le__ = le
__eq__ = eq
__ne__ = ne
__gt__ = gt
__ge__ = ge
__not__ = not_
__contains__ = contains
__getitem__ = getitem
__setitem__ = setitem
__delitem__ = delitem


# Invariant smoke-test helpers
def operator2_add():
    return add(3, 4)


def operator2_itemgetter():
    return itemgetter(1)(["a", "b", "c"])


def operator2_attrgetter():
    return attrgetter("__class__.__name__")([])