# Clean-room implementation of functools utilities
# No import of functools or any third-party library

_MISSING = object()


def reduce(function, iterable, initializer=_MISSING):
    """
    Left-fold: reduce(fn, iterable[, initializer])
    reduce(lambda a, b: a + b, [1, 2, 3, 4]) == 10
    """
    it = iter(iterable)
    if initializer is _MISSING:
        try:
            accumulator = next(it)
        except StopIteration:
            raise TypeError("reduce() of empty iterable with no initial value")
    else:
        accumulator = initializer
    for element in it:
        accumulator = function(accumulator, element)
    return accumulator


class partial:
    """
    Return a new callable with pre-filled positional and keyword arguments.
    partial(int, base=2)('101') == 5
    """
    __slots__ = ('func', 'args', 'keywords')

    def __new__(cls, func, *args, **kwargs):
        if not callable(func):
            raise TypeError("the first argument must be callable")
        obj = super().__new__(cls)
        # If func is itself a partial, flatten it
        if isinstance(func, partial):
            new_args = func.args + args
            new_kwargs = {**func.keywords, **kwargs}
            obj.func = func.func
            obj.args = new_args
            obj.keywords = new_kwargs
        else:
            obj.func = func
            obj.args = args
            obj.keywords = kwargs
        return obj

    def __call__(self, *args, **kwargs):
        merged_kwargs = {**self.keywords, **kwargs}
        return self.func(*self.args, *args, **merged_kwargs)

    def __repr__(self):
        args_repr = ', '.join(repr(a) for a in self.args)
        kwargs_repr = ', '.join('{0}={1!r}'.format(k, v) for k, v in self.keywords.items())
        all_args = ', '.join(x for x in [args_repr, kwargs_repr] if x)
        return 'partial({0!r}, {1})'.format(self.func, all_args)


class lru_cache:
    """
    Memoize with LRU eviction.
    Can be used as a decorator: @lru_cache(maxsize=128) or @lru_cache
    """
    def __init__(self, maxsize=128, typed=False):
        self._maxsize = maxsize
        self._typed = typed
        self._func = None
        self._cache = {}       # key -> value
        self._order = []       # list of keys in access order (oldest first)

    def __call__(self, *args, **kwargs):
        # If used as @lru_cache (no parentheses), first call receives the function
        if self._func is None and len(args) == 1 and callable(args[0]) and not kwargs:
            self._func = args[0]
            return self
        # Otherwise, call the wrapped function with memoization
        key = self._make_key(args, kwargs)
        if key in self._cache:
            # Move to end (most recently used)
            self._order.remove(key)
            self._order.append(key)
            return self._cache[key]
        result = self._func(*args, **kwargs)
        self._cache[key] = result
        self._order.append(key)
        if self._maxsize is not None and len(self._cache) > self._maxsize:
            # Evict least recently used
            oldest = self._order.pop(0)
            del self._cache[oldest]
        return result

    def _make_key(self, args, kwargs):
        key = args
        if kwargs:
            key += (object(),)  # separator
            for item in sorted(kwargs.items()):
                key += item
        if self._typed:
            key += tuple(type(a) for a in args)
            if kwargs:
                key += tuple(type(v) for v in kwargs.values())
        return key

    def cache_info(self):
        return (len(self._cache),)

    def cache_clear(self):
        self._cache.clear()
        self._order.clear()

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return partial(self, obj)

    def __repr__(self):
        return 'lru_cache({0!r})'.format(self._func)


# --- Invariant test functions ---

def reduce_sum():
    """reduce(lambda a, b: a + b, [1, 2, 3, 4]) == 10"""
    return reduce(lambda a, b: a + b, [1, 2, 3, 4])


def partial_base2():
    """partial(int, base=2)('101') == 5"""
    int_base2 = partial(int, base=2)
    return int_base2('101')


def reduce_product():
    """reduce(lambda a, b: a * b, [1, 2, 3, 4, 5]) == 120"""
    return reduce(lambda a, b: a * b, [1, 2, 3, 4, 5])


# Aliases with functools_ prefix for compatibility
functools_reduce_sum = reduce_sum
functools_partial_base2 = partial_base2
functools_reduce_product = reduce_product