"""
theseus_functools_cr3 - Clean-room implementation of functools utilities.
No import of functools or any third-party library.
"""

def cache(func):
    """Unbounded memoization cache decorator."""
    _cache = {}
    
    def wrapper(*args, **kwargs):
        # Create a hashable key from args and kwargs
        key = (args, tuple(sorted(kwargs.items())))
        if key not in _cache:
            _cache[key] = func(*args, **kwargs)
        return _cache[key]
    
    # Copy metadata
    wrapper.__name__ = getattr(func, '__name__', None)
    wrapper.__doc__ = getattr(func, '__doc__', None)
    wrapper.__dict__.update(getattr(func, '__dict__', {}))
    wrapper.__module__ = getattr(func, '__module__', None)
    wrapper.__qualname__ = getattr(func, '__qualname__', None)
    wrapper.__annotations__ = getattr(func, '__annotations__', {})
    wrapper.__wrapped__ = func
    wrapper._cache = _cache
    
    return wrapper


def wraps(wrapped):
    """Decorator factory to copy function metadata from wrapped to wrapper."""
    def decorator(wrapper):
        wrapper.__name__ = getattr(wrapped, '__name__', None)
        wrapper.__doc__ = getattr(wrapped, '__doc__', None)
        wrapper.__dict__.update(getattr(wrapped, '__dict__', {}))
        wrapper.__module__ = getattr(wrapped, '__module__', None)
        wrapper.__qualname__ = getattr(wrapped, '__qualname__', None)
        wrapper.__annotations__ = getattr(wrapped, '__annotations__', {})
        wrapper.__wrapped__ = wrapped
        return wrapper
    return decorator


def cmp_to_key(mycmp):
    """Convert an old-style comparison function to a key function."""
    class K:
        __slots__ = ('obj',)
        
        def __init__(self, obj):
            self.obj = obj
        
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
        
        def __hash__(self):
            raise TypeError('hash not implemented')
    
    K.__name__ = 'K'
    K.__qualname__ = 'cmp_to_key.<locals>.K'
    return K


def functools3_cache():
    """Test that cache works correctly."""
    call_count = [0]
    
    @cache
    def f(x):
        call_count[0] += 1
        return x * 2
    
    result1 = f(3)
    result2 = f(3)  # Should use cache
    
    return result1 == 6 and result2 == 6 and call_count[0] == 1


def functools3_wraps():
    """Test that wraps copies metadata correctly."""
    def original():
        """Original docstring."""
        pass
    original.__name__ = 'original'
    
    @wraps(original)
    def wrapper():
        pass
    
    return wrapper.__name__ == original.__name__


def functools3_cmp_to_key():
    """Test that cmp_to_key works for sorting."""
    result = sorted([3, 1, 2], key=cmp_to_key(lambda a, b: a - b))
    return result