"""
Clean-room implementation of functools utilities.
No import of functools or any third-party library.
"""


def reduce(function, iterable, initializer=None):
    """
    Apply function cumulatively to items of iterable, from left to right,
    so as to reduce the iterable to a single value.
    
    reduce(f, [a, b, c]) == f(f(a, b), c)
    reduce(f, [a, b, c], init) == f(f(f(init, a), b), c)
    """
    it = iter(iterable)
    
    if initializer is None:
        try:
            accumulator = next(it)
        except StopIteration:
            raise TypeError("reduce() of empty iterable with no initial value")
    else:
        accumulator = initializer
    
    for item in it:
        accumulator = function(accumulator, item)
    
    return accumulator


class partial:
    """
    Return a new callable that behaves like func called with the positional
    arguments args and keyword arguments kwargs. Additional arguments supplied
    at call time are appended to args, and additional keyword arguments
    override or extend kwargs.
    """
    
    def __init__(self, func, *args, **kwargs):
        if not callable(func):
            raise TypeError("the first argument must be callable")
        self.func = func
        self.args = args
        self.keywords = kwargs
    
    def __call__(self, *call_args, **call_kwargs):
        new_args = self.args + call_args
        new_kwargs = {**self.keywords, **call_kwargs}
        return self.func(*new_args, **new_kwargs)
    
    def __repr__(self):
        args_repr = ", ".join(repr(a) for a in self.args)
        kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in self.keywords.items())
        all_args = ", ".join(filter(None, [args_repr, kwargs_repr]))
        return f"partial({self.func!r}, {all_args})"


def wraps(wrapped):
    """
    Decorator factory that updates the wrapper function to look like the
    wrapped function.
    """
    def decorator(wrapper):
        wrapper.__wrapped__ = wrapped
        wrapper.__name__ = getattr(wrapped, '__name__', None)
        wrapper.__qualname__ = getattr(wrapped, '__qualname__', None)
        wrapper.__doc__ = getattr(wrapped, '__doc__', None)
        wrapper.__dict__.update(getattr(wrapped, '__dict__', {}))
        wrapper.__module__ = getattr(wrapped, '__module__', None)
        wrapper.__annotations__ = getattr(wrapped, '__annotations__', {})
        return wrapper
    return decorator


class lru_cache:
    """
    Least-recently-used cache decorator.
    
    If maxsize is set to None, the LRU feature is disabled and the cache
    can grow without bound.
    """
    
    def __init__(self, maxsize=128, typed=False):
        self.maxsize = maxsize
        self.typed = typed
        self._cache = {}
        self._order = []  # tracks access order for LRU eviction
        self._hits = 0
        self._misses = 0
        self._func = None
    
    def __call__(self, func_or_arg=None):
        # Handle both @lru_cache and @lru_cache() usage
        if callable(func_or_arg):
            # Used as @lru_cache without parentheses
            self._func = func_or_arg
            
            @wraps(func_or_arg)
            def wrapper(*args, **kwargs):
                return self._call_cached(*args, **kwargs)
            
            wrapper.cache_info = self.cache_info
            wrapper.cache_clear = self.cache_clear
            return wrapper
        else:
            # Used as @lru_cache() or @lru_cache(maxsize=N)
            # func_or_arg is actually the function being decorated
            # This path shouldn't normally be hit since __init__ handles maxsize
            raise TypeError("Invalid usage of lru_cache")
    
    def _make_key(self, args, kwargs, typed):
        key = args
        if kwargs:
            key += (object(),)  # sentinel
            for item in sorted(kwargs.items()):
                key += item
        if typed:
            key += tuple(type(v) for v in args)
            if kwargs:
                key += tuple(type(v) for v in kwargs.values())
        return key
    
    def _call_cached(self, *args, **kwargs):
        key = self._make_key(args, kwargs, self.typed)
        
        if key in self._cache:
            self._hits += 1
            # Move to end (most recently used)
            if key in self._order:
                self._order.remove(key)
                self._order.append(key)
            return self._cache[key]
        
        self._misses += 1
        result = self._func(*args, **kwargs)
        
        if self.maxsize is None:
            self._cache[key] = result
        elif self.maxsize > 0:
            if len(self._cache) >= self.maxsize:
                # Evict least recently used
                lru_key = self._order.pop(0)
                del self._cache[lru_key]
            self._cache[key] = result
            self._order.append(key)
        
        return result
    
    def cache_info(self):
        return (self._hits, self._misses, self.maxsize, len(self._cache))
    
    def cache_clear(self):
        self._cache.clear()
        self._order.clear()
        self._hits = 0
        self._misses = 0


def _lru_cache_decorator(maxsize=128, typed=False):
    """
    Proper lru_cache implementation that works as both
    @lru_cache and @lru_cache(maxsize=N)
    """
    def decorator(func):
        cache = {}
        order = []
        hits = [0]
        misses = [0]
        
        def make_key(args, kwargs):
            key = args
            if kwargs:
                key += (object,)
                for item in sorted(kwargs.items()):
                    key += item
            if typed:
                key += tuple(type(v) for v in args)
            return key
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = make_key(args, kwargs)
            
            if key in cache:
                hits[0] += 1
                if key in order:
                    order.remove(key)
                    order.append(key)
                return cache[key]
            
            misses[0] += 1
            result = func(*args, **kwargs)
            
            if maxsize is None:
                cache[key] = result
            elif maxsize > 0:
                if len(cache) >= maxsize:
                    lru_key = order.pop(0)
                    del cache[lru_key]
                cache[key] = result
                order.append(key)
            
            return result
        
        def cache_info():
            return (hits[0], misses[0], maxsize, len(cache))
        
        def cache_clear():
            cache.clear()
            order.clear()
            hits[0] = 0
            misses[0] = 0
        
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper
    
    return decorator


# Override lru_cache with a proper function-based implementation
def lru_cache(maxsize=128, typed=False):
    """
    Decorator to wrap a function with a memoizing callable that saves up to
    maxsize results based on a Least Recently Used (LRU) algorithm.
    """
    if callable(maxsize):
        # Used as @lru_cache without parentheses
        func = maxsize
        return _lru_cache_decorator(128, False)(func)
    else:
        return _lru_cache_decorator(maxsize, typed)


# ── Invariant test functions ──────────────────────────────────────────────────

def functools4_reduce():
    """reduce(lambda a, b: a+b, [1,2,3,4]) == 10"""
    return reduce(lambda a, b: a + b, [1, 2, 3, 4])


def functools4_partial_kwargs():
    """partial(int, base=16)('ff') == 255"""
    hex_int = partial(int, base=16)
    return hex_int('ff')


def functools4_partial_basic():
    """partial(pow, 2)(10) == 1024 (2**10)"""
    pow2 = partial(pow, 2)
    return pow2(10)


__all__ = [
    'reduce',
    'partial',
    'wraps',
    'lru_cache',
    'functools4_reduce',
    'functools4_partial_kwargs',
    'functools4_partial_basic',
]