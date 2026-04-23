"""
theseus_functools_cr2 - Clean-room implementation of extended functools utilities.
No import of functools or any third-party library.
"""

import threading


# ---------------------------------------------------------------------------
# cached_property
# ---------------------------------------------------------------------------

class cached_property:
    """
    A descriptor that computes the property value once and caches it on the
    instance's __dict__ under the same attribute name.
    """

    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__
        self.lock = threading.RLock()

    def __set_name__(self, owner, name):
        self.attrname = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        name = self.attrname
        if name is None:
            # Fallback: use the function name
            name = self.func.__name__
        with self.lock:
            # Check again inside the lock
            if name not in instance.__dict__:
                instance.__dict__[name] = self.func(instance)
        return instance.__dict__[name]


# ---------------------------------------------------------------------------
# total_ordering
# ---------------------------------------------------------------------------

def total_ordering(cls):
    """
    Class decorator that fills in missing comparison methods.
    The class must define __eq__ and one of __lt__, __le__, __gt__, __ge__.
    """
    roots = {
        '__lt__': [
            ('__gt__', lambda self, other: NotImplemented if (r := self.__lt__(other)) is NotImplemented else not r and self != other),
            ('__le__', lambda self, other: NotImplemented if (r := self.__lt__(other)) is NotImplemented else r or self == other),
            ('__ge__', lambda self, other: NotImplemented if (r := self.__lt__(other)) is NotImplemented else not r),
        ],
        '__le__': [
            ('__ge__', lambda self, other: NotImplemented if (r := self.__le__(other)) is NotImplemented else not r or self == other),
            ('__lt__', lambda self, other: NotImplemented if (r := self.__le__(other)) is NotImplemented else r and self != other),
            ('__gt__', lambda self, other: NotImplemented if (r := self.__le__(other)) is NotImplemented else not r),
        ],
        '__gt__': [
            ('__lt__', lambda self, other: NotImplemented if (r := self.__gt__(other)) is NotImplemented else not r and self != other),
            ('__ge__', lambda self, other: NotImplemented if (r := self.__gt__(other)) is NotImplemented else r or self == other),
            ('__le__', lambda self, other: NotImplemented if (r := self.__gt__(other)) is NotImplemented else not r),
        ],
        '__ge__': [
            ('__le__', lambda self, other: NotImplemented if (r := self.__ge__(other)) is NotImplemented else not r or self == other),
            ('__gt__', lambda self, other: NotImplemented if (r := self.__ge__(other)) is NotImplemented else r and self != other),
            ('__lt__', lambda self, other: NotImplemented if (r := self.__ge__(other)) is NotImplemented else not r),
        ],
    }

    # Find which root method is defined
    defined = set(cls.__dict__)

    # Determine which root we have
    root = None
    for candidate in ('__lt__', '__le__', '__gt__', '__ge__'):
        if candidate in defined:
            root = candidate
            break

    if root is None:
        raise ValueError(
            "total_ordering requires at least one of: "
            "__lt__, __le__, __gt__, __ge__"
        )

    if '__eq__' not in defined:
        raise ValueError("total_ordering requires __eq__ to be defined")

    # Add missing methods
    for method_name, method_impl in roots[root]:
        if method_name not in defined:
            setattr(cls, method_name, method_impl)

    return cls


# ---------------------------------------------------------------------------
# singledispatch
# ---------------------------------------------------------------------------

class singledispatch:
    """
    A decorator that transforms a function into a single-dispatch generic
    function. Implementations for specific types can be registered with the
    .register() method.
    """

    def __init__(self, func):
        self._func = func
        self._registry = {}
        # Copy function metadata
        self.__doc__ = func.__doc__
        self.__name__ = getattr(func, '__name__', None)
        self.__qualname__ = getattr(func, '__qualname__', None)
        self.__module__ = getattr(func, '__module__', None)
        self.__wrapped__ = func

    def register(self, type_or_func=None, func=None):
        """
        Register an implementation for a given type.

        Can be used as:
            @my_func.register(int)
            def _(arg):
                ...

        Or:
            my_func.register(int, impl_func)
        """
        if type_or_func is None:
            raise TypeError("register() requires at least one argument")

        # Called as .register(SomeType, func)
        if func is not None:
            self._registry[type_or_func] = func
            return func

        # Called as .register(SomeType) — returns decorator
        if isinstance(type_or_func, type):
            def decorator(f):
                self._registry[type_or_func] = f
                return f
            return decorator

        # Called as .register(func) with annotations — not supported in minimal impl
        # but handle gracefully
        raise TypeError(
            "register() first argument must be a type, got {!r}".format(type_or_func)
        )

    def dispatch(self, tp):
        """Return the implementation for the given type."""
        # Check exact match first
        if tp in self._registry:
            return self._registry[tp]
        # Walk MRO
        for base in tp.__mro__:
            if base in self._registry:
                return self._registry[base]
        return self._func

    def __call__(self, arg, *args, **kwargs):
        impl = self.dispatch(type(arg))
        return impl(arg, *args, **kwargs)

    @property
    def registry(self):
        return dict(self._registry)


# ---------------------------------------------------------------------------
# Verification / demo functions
# ---------------------------------------------------------------------------

def functools2_cached_property():
    """
    Demonstrates cached_property: the property function is called only once.
    Returns True if the cached value is reused correctly.
    """
    call_count = []

    class MyClass:
        @cached_property
        def value(self):
            call_count.append(1)
            return 42

    obj = MyClass()
    # Access twice
    v1 = obj.value
    v2 = obj.value

    return v1 == 42 and v2 == 42 and len(call_count) == 1


def functools2_total_ordering():
    """
    Demonstrates total_ordering: a class with __eq__ and __lt__ gets
    __le__, __gt__, __ge__ filled in automatically.
    Returns True if all comparisons work correctly.
    """

    @total_ordering
    class Number:
        def __init__(self, val):
            self.val = val

        def __eq__(self, other):
            if not isinstance(other, Number):
                return NotImplemented
            return self.val == other.val

        def __lt__(self, other):
            if not isinstance(other, Number):
                return NotImplemented
            return self.val < other.val

    a = Number(1)
    b = Number(2)
    c = Number(1)

    checks = [
        a < b,        # True
        not (b < a),  # True
        a <= c,       # True
        a <= b,       # True
        not (b <= a), # True
        b > a,        # True
        not (a > b),  # True
        b >= a,       # True
        a >= c,       # True
        not (a >= b), # True
        a == c,       # True
        not (a == b), # True
    ]

    return all(checks)


def functools2_singledispatch():
    """
    Demonstrates singledispatch: dispatches to int handler for int argument.
    Returns "int" when called with an integer.
    """

    @singledispatch
    def process(arg):
        return "default"

    @process.register(int)
    def _(arg):
        return "int"

    @process.register(str)
    def _(arg):
        return "str"

    return process(42)


__all__ = [
    'cached_property',
    'total_ordering',
    'singledispatch',
    'functools2_cached_property',
    'functools2_total_ordering',
    'functools2_singledispatch',
]