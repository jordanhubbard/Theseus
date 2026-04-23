# theseus_operator - clean-room implementation
# Do NOT import the `operator` module


def _curry2(func):
    """Make a 2-arg function also work as curried: f(a, b) or f(a)(b)."""
    class CurriedFunc:
        def __call__(self, a, b=_MISSING):
            if b is _MISSING:
                def partial(b):
                    return func(a, b)
                return partial
            return func(a, b)
        def __repr__(self):
            return f"<theseus_operator.{func.__name__}>"
        @property
        def __name__(self):
            return func.__name__
        @property
        def __doc__(self):
            return func.__doc__
    c = CurriedFunc()
    return c


class _MISSING_TYPE:
    pass

_MISSING = _MISSING_TYPE()


def _add(a, b):
    """Return a + b."""
    return a + b

def _sub(a, b):
    """Return a - b."""
    return a - b

def _mul(a, b):
    """Return a * b."""
    return a * b

def _truediv(a, b):
    """Return a / b."""
    return a / b

def _lt(a, b):
    """Return a < b."""
    return a < b

def _le(a, b):
    """Return a <= b."""
    return a <= b

def _eq(a, b):
    """Return a == b."""
    return a == b

def _ne(a, b):
    """Return a != b."""
    return a != b

def _ge(a, b):
    """Return a >= b."""
    return a >= b

def _gt(a, b):
    """Return a > b."""
    return a > b


add = _curry2(_add)
sub = _curry2(_sub)
mul = _curry2(_mul)
truediv = _curry2(_truediv)
lt = _curry2(_lt)
le = _curry2(_le)
eq = _curry2(_eq)
ne = _curry2(_ne)
ge = _curry2(_ge)
gt = _curry2(_gt)


class itemgetter:
    """
    Return a callable object that fetches the given item(s) from its operand.
    itemgetter(key)(obj) returns obj[key].
    itemgetter(1)([10, 20, 30]) == 20
    Can be called with no arguments, returning a callable that takes a key then an obj.
    """
    def __init__(self, *keys):
        self._keys = keys
        self._has_keys = len(keys) > 0

    def __call__(self, *args):
        if not self._has_keys:
            # Called as itemgetter()(key) - treat first arg as key
            if len(args) == 0:
                raise TypeError("itemgetter expected at least 1 argument, got 0")
            if len(args) == 1:
                # Return a new itemgetter with this key
                return itemgetter(args[0])
            # args[0] is key, args[1] is obj
            return args[1][args[0]]
        else:
            # Normal usage: itemgetter(key)(obj)
            if len(args) != 1:
                raise TypeError(f"itemgetter expected 1 argument, got {len(args)}")
            obj = args[0]
            if len(self._keys) == 1:
                return obj[self._keys[0]]
            return tuple(obj[k] for k in self._keys)

    def __repr__(self):
        if not self._has_keys:
            return "theseus_operator.itemgetter()"
        keys_repr = ', '.join(repr(k) for k in self._keys)
        return f"theseus_operator.itemgetter({keys_repr})"


class attrgetter:
    """
    Return a callable object that fetches the given attribute(s) from its operand.
    attrgetter(name)(obj) returns getattr(obj, name).
    Supports dotted names: attrgetter('a.b')(obj) returns obj.a.b
    """
    def __init__(self, *attrs):
        if len(attrs) == 0:
            raise TypeError("attrgetter expected at least 1 argument, got 0")
        self._attrs = attrs

    def _get_attr(self, obj, attr):
        for part in attr.split('.'):
            obj = getattr(obj, part)
        return obj

    def __call__(self, obj):
        if len(self._attrs) == 1:
            return self._get_attr(obj, self._attrs[0])
        return tuple(self._get_attr(obj, attr) for attr in self._attrs)

    def __repr__(self):
        attrs_repr = ', '.join(repr(a) for a in self._attrs)
        return f"theseus_operator.attrgetter({attrs_repr})"


class methodcaller:
    """
    Return a callable object that calls the given method on its operand.
    methodcaller(name, *args, **kwargs)(obj) returns getattr(obj, name)(*args, **kwargs).
    """
    def __init__(self, name, *args, **kwargs):
        self._name = name
        self._args = args
        self._kwargs = kwargs

    def __call__(self, obj):
        return getattr(obj, self._name)(*self._args, **self._kwargs)

    def __repr__(self):
        args_repr = ', '.join([repr(self._name)] +
                              [repr(a) for a in self._args] +
                              [f"{k}={v!r}" for k, v in self._kwargs.items()])
        return f"theseus_operator.methodcaller({args_repr})"


def operator_add():
    return add(3, 4)

def operator_itemgetter():
    return itemgetter(1)([10, 20, 30])

def operator_lt():
    return lt(1, 2)

operator_sub = sub
operator_mul = mul
operator_truediv = truediv
operator_le = le
operator_eq = eq
operator_ne = ne
operator_ge = ge
operator_gt = gt
operator_attrgetter = attrgetter
operator_methodcaller = methodcaller


__all__ = [
    'add', 'sub', 'mul', 'truediv',
    'lt', 'le', 'eq', 'ne', 'ge', 'gt',
    'itemgetter', 'attrgetter', 'methodcaller',
    'operator_add', 'operator_sub', 'operator_mul', 'operator_truediv',
    'operator_lt', 'operator_le', 'operator_eq', 'operator_ne', 'operator_ge', 'operator_gt',
    'operator_itemgetter', 'operator_attrgetter', 'operator_methodcaller',
]