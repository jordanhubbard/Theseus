"""
theseus_functools_cr5 - Clean-room implementation of functools utilities.
No import of functools allowed.
"""

# ─────────────────────────────────────────────
# total_ordering
# ─────────────────────────────────────────────

def total_ordering(cls):
    """
    Class decorator that fills in missing comparison methods.
    Requires __eq__ and one of __lt__, __le__, __gt__, __ge__.
    """
    roots = {op for op in ('__lt__', '__le__', '__gt__', '__ge__')
             if getattr(cls, op, None) is not getattr(object, op, None)}

    if not roots:
        raise ValueError(
            'must have at least one ordering operation defined: '
            '__lt__, __le__, __gt__, or __ge__'
        )

    _convert = {
        '__lt__': [
            ('__gt__', lambda self, other: type(self).__lt__(other, self)),
            ('__le__', lambda self, other: self == other or type(self).__lt__(self, other)),
            ('__ge__', lambda self, other: not type(self).__lt__(self, other)),
        ],
        '__le__': [
            ('__ge__', lambda self, other: type(self).__le__(other, self)),
            ('__lt__', lambda self, other: self != other and type(self).__le__(self, other)),
            ('__gt__', lambda self, other: not type(self).__le__(self, other)),
        ],
        '__gt__': [
            ('__lt__', lambda self, other: type(self).__gt__(other, self)),
            ('__ge__', lambda self, other: self == other or type(self).__gt__(self, other)),
            ('__le__', lambda self, other: not type(self).__gt__(self, other)),
        ],
        '__ge__': [
            ('__le__', lambda self, other: type(self).__ge__(other, self)),
            ('__gt__', lambda self, other: self != other and type(self).__ge__(self, other)),
            ('__lt__', lambda self, other: not type(self).__ge__(self, other)),
        ],
    }

    # Pick the root we have (prefer __lt__ if multiple)
    root = None
    for r in ('__lt__', '__le__', '__gt__', '__ge__'):
        if r in roots:
            root = r
            break

    for op, impl in _convert[root]:
        if getattr(cls, op, None) is getattr(object, op, None):
            def make_method(fn):
                def method(self, other):
                    result = fn(self, other)
                    if result is NotImplemented:
                        return NotImplemented
                    return result
                return method
            setattr(cls, op, make_method(impl))

    return cls


# ─────────────────────────────────────────────
# singledispatch
# ─────────────────────────────────────────────

def singledispatch(func):
    """
    Single-dispatch generic function decorator.
    Transforms a function into a generic function that dispatches
    on the type of its first argument.
    """
    registry = {}
    registry[object] = func

    def dispatch(tp):
        """Return the implementation for the given type."""
        if tp in registry:
            return registry[tp]
        for base in tp.__mro__:
            if base in registry:
                return registry[base]
        return registry[object]

    def register(tp, fn=None):
        """Register an implementation for the given type."""
        if fn is None:
            def decorator(fn):
                registry[tp] = fn
                return fn
            return decorator
        registry[tp] = fn
        return fn

    def wrapper(*args, **kwargs):
        if not args:
            raise TypeError('singledispatch requires at least one positional argument')
        tp = type(args[0])
        impl = dispatch(tp)
        return impl(*args, **kwargs)

    wrapper.register = register
    wrapper.dispatch = dispatch
    wrapper.registry = registry
    wrapper.__name__ = getattr(func, '__name__', None)
    wrapper.__doc__ = getattr(func, '__doc__', None)
    wrapper.__wrapped__ = func
    return wrapper


# ─────────────────────────────────────────────
# singledispatchmethod
# ─────────────────────────────────────────────

class singledispatchmethod:
    """
    Single-dispatch generic method descriptor.
    Supports dispatching on the type of the first non-self argument.
    """
    def __init__(self, func):
        self.dispatcher = singledispatch(func)
        self.func = func

    def register(self, tp, fn=None):
        return self.dispatcher.register(tp, fn)

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        def method(*args, **kwargs):
            if not args:
                raise TypeError('singledispatchmethod requires at least one positional argument')
            tp = type(args[0])
            impl = self.dispatcher.dispatch(tp)
            return impl(obj, *args, **kwargs)
        method.register = self.register
        return method


# ─────────────────────────────────────────────
# cached_property
# ─────────────────────────────────────────────

class cached_property:
    """
    Descriptor that computes the property value once and caches it
    in the instance's __dict__.
    """
    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__

    def __set_name__(self, owner, name):
        self.attrname = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        name = self.attrname
        if name is None:
            name = self.func.__name__
        if name not in instance.__dict__:
            instance.__dict__[name] = self.func(instance)
        return instance.__dict__[name]


# ─────────────────────────────────────────────
# reduce
# ─────────────────────────────────────────────

_sentinel = object()


def reduce(function, iterable, initializer=_sentinel):
    """
    Apply function of two arguments cumulatively to the items of iterable,
    so as to reduce the iterable to a single value.
    """
    it = iter(iterable)
    if initializer is _sentinel:
        try:
            value = next(it)
        except StopIteration:
            raise TypeError('reduce() of empty iterable with no initial value')
    else:
        value = initializer
    for element in it:
        value = function(value, element)
    return value


# ─────────────────────────────────────────────
# partial
# ─────────────────────────────────────────────

class partial:
    """
    New function with partial application of the given arguments and keywords.
    """
    __slots__ = ('func', 'args', 'keywords', '__dict__', '__weakref__')

    def __new__(cls, func, *args, **keywords):
        if not callable(func):
            raise TypeError('the first argument must be callable')
        if isinstance(func, partial):
            # Flatten nested partials
            args = func.args + args
            keywords = {**func.keywords, **keywords}
            func = func.func
        obj = super().__new__(cls)
        obj.func = func
        obj.args = args
        obj.keywords = keywords
        return obj

    def __call__(self, *args, **keywords):
        merged_keywords = {**self.keywords, **keywords}
        return self.func(*self.args, *args, **merged_keywords)

    def __repr__(self):
        args_str = ', '.join(repr(a) for a in self.args)
        kwargs_str = ', '.join('{0}={1!r}'.format(k, v) for k, v in self.keywords.items())
        parts = [repr(self.func)]
        if args_str:
            parts.append(args_str)
        if kwargs_str:
            parts.append(kwargs_str)
        return 'partial({0})'.format(', '.join(parts))

    @property
    def __doc__(self):
        return getattr(self.func, '__doc__', None)


# ─────────────────────────────────────────────
# wraps
# ─────────────────────────────────────────────

WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__qualname__', '__annotations__',
                       '__doc__')
WRAPPER_UPDATES = ('__dict__',)


def update_wrapper(wrapper, wrapped,
                   assigned=WRAPPER_ASSIGNMENTS,
                   updated=WRAPPER_UPDATES):
    """Update a wrapper function to look like the wrapped function."""
    for attr in assigned:
        try:
            value = getattr(wrapped, attr)
        except AttributeError:
            pass
        else:
            setattr(wrapper, attr, value)
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    wrapper.__wrapped__ = wrapped
    return wrapper


def wraps(wrapped, assigned=WRAPPER_ASSIGNMENTS, updated=WRAPPER_UPDATES):
    """Decorator factory to apply update_wrapper() to a wrapper function."""
    def decorator(wrapper):
        return update_wrapper(wrapper, wrapped, assigned=assigned, updated=updated)
    return decorator


# ─────────────────────────────────────────────
# Invariant test functions
# ─────────────────────────────────────────────

def functools5_total_ordering():
    """Test that total_ordering fills in __gt__ from __eq__ + __lt__."""
    @total_ordering
    class MyNum:
        def __init__(self, val):
            self.val = val
        def __eq__(self, other):
            return self.val == other.val
        def __lt__(self, other):
            return self.val < other.val

    a = MyNum(1)
    b = MyNum(2)
    result = b > a  # should be True
    return result is True


def functools5_singledispatch():
    """Test that singledispatch dispatches correctly for str type."""
    @singledispatch
    def process(arg):
        return 'default'

    @process.register(str)
    def _(arg):
        return 'string'

    return process('hello') == 'string'


def functools5_cached_property():
    """Test that cached_property computes once and caches."""
    call_count = [0]

    class MyClass:
        @cached_property
        def value(self):
            call_count[0] += 1
            return 42

    obj = MyClass()
    v1 = obj.value
    v2 = obj.value
    return v1 == 42 and v2 == 42 and call_count[0] == 1


__all__ = [
    'total_ordering',
    'singledispatch',
    'singledispatchmethod',
    'cached_property',
    'reduce',
    'partial',
    'wraps',
    'update_wrapper',
    'WRAPPER_ASSIGNMENTS',
    'WRAPPER_UPDATES',
    'functools5_total_ordering',
    'functools5_singledispatch',
    'functools5_cached_property',
]