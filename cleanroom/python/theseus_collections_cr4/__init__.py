"""
theseus_collections_cr4 — Clean-room implementation of extended collections utilities.
Do NOT import collections or any third-party library.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Counter
# ─────────────────────────────────────────────────────────────────────────────

class Counter(dict):
    """
    A dict subclass for counting hashable objects.
    Elements are stored as dictionary keys and their counts as values.
    """

    def __init__(self, iterable_or_mapping=None, **kwargs):
        super().__init__()
        if iterable_or_mapping is not None:
            self.update(iterable_or_mapping)
        if kwargs:
            self.update(kwargs)

    def update(self, iterable_or_mapping=None, **kwargs):
        """Add counts from iterable or mapping."""
        if iterable_or_mapping is not None:
            if hasattr(iterable_or_mapping, 'items'):
                # It's a mapping
                for key, count in iterable_or_mapping.items():
                    self[key] = self.get(key, 0) + count
            else:
                # It's an iterable
                for item in iterable_or_mapping:
                    self[item] = self.get(item, 0) + 1
        for key, count in kwargs.items():
            self[key] = self.get(key, 0) + count

    def most_common(self, n=None):
        """
        Return a list of the n most common elements and their counts,
        from most common to least. If n is None, return all elements.
        Result is sorted by count descending; ties are in arbitrary order.
        """
        items = list(self.items())
        # Sort by count descending (stable sort)
        items.sort(key=lambda x: x[1], reverse=True)
        if n is None:
            return items
        return items[:n]

    def __missing__(self, key):
        return 0

    def __add__(self, other):
        """Add counts, keeping only positive results."""
        result = Counter()
        all_keys = set(self.keys()) | set(other.keys())
        for key in all_keys:
            val = self.get(key, 0) + other.get(key, 0)
            if val > 0:
                result[key] = val
        return result

    def __sub__(self, other):
        """Subtract counts, keeping only positive results."""
        result = Counter()
        for key in self.keys():
            val = self.get(key, 0) - other.get(key, 0)
            if val > 0:
                result[key] = val
        return result

    def __or__(self, other):
        """Union: max(c[x], d[x])"""
        result = Counter()
        all_keys = set(self.keys()) | set(other.keys())
        for key in all_keys:
            val = max(self.get(key, 0), other.get(key, 0))
            if val > 0:
                result[key] = val
        return result

    def __and__(self, other):
        """Intersection: min(c[x], d[x])"""
        result = Counter()
        for key in self.keys():
            val = min(self.get(key, 0), other.get(key, 0))
            if val > 0:
                result[key] = val
        return result

    def elements(self):
        """Return an iterator over elements repeating each as many times as its count."""
        for key, count in self.items():
            for _ in range(max(0, count)):
                yield key

    def subtract(self, iterable_or_mapping=None, **kwargs):
        """Subtract counts. Unlike update(), counts can go below zero."""
        if iterable_or_mapping is not None:
            if hasattr(iterable_or_mapping, 'items'):
                for key, count in iterable_or_mapping.items():
                    self[key] = self.get(key, 0) - count
            else:
                for item in iterable_or_mapping:
                    self[item] = self.get(item, 0) - 1
        for key, count in kwargs.items():
            self[key] = self.get(key, 0) - count

    def copy(self):
        return Counter(self)

    def __repr__(self):
        if not self:
            return 'Counter()'
        items = ', '.join(f'{k!r}: {v!r}' for k, v in self.items())
        return f'Counter({{{items}}})'


# ─────────────────────────────────────────────────────────────────────────────
# OrderedDict
# ─────────────────────────────────────────────────────────────────────────────

class OrderedDict(dict):
    """
    A dict subclass that remembers insertion order.
    (In Python 3.7+ regular dicts are ordered, but we implement explicitly.)
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._order = []  # list of keys in insertion order
        if args:
            if len(args) > 1:
                raise TypeError(f'OrderedDict expected at most 1 argument, got {len(args)}')
            other = args[0]
            if hasattr(other, 'items'):
                for k, v in other.items():
                    self[k] = v
            else:
                for k, v in other:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def __setitem__(self, key, value):
        if key not in self:
            self._order.append(key)
        super().__setitem__(key, value)

    def __delitem__(self, key):
        super().__delitem__(key)
        self._order.remove(key)

    def __iter__(self):
        return iter(self._order)

    def __reversed__(self):
        return reversed(self._order)

    def keys(self):
        return _KeysView(self._order)

    def values(self):
        return _ValuesView(self._order, self)

    def items(self):
        return _ItemsView(self._order, self)

    def move_to_end(self, key, last=True):
        """Move an existing key to either end."""
        if key not in self:
            raise KeyError(key)
        self._order.remove(key)
        if last:
            self._order.append(key)
        else:
            self._order.insert(0, key)

    def popitem(self, last=True):
        """Remove and return a (key, value) pair. last=True means LIFO."""
        if not self._order:
            raise KeyError('dictionary is empty')
        key = self._order[-1] if last else self._order[0]
        value = self[key]
        del self[key]
        return key, value

    def copy(self):
        return OrderedDict(self)

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for (k1, v1), (k2, v2) in zip(self.items(), other.items()):
                if k1 != k2 or v1 != v2:
                    return False
            return True
        return dict.__eq__(self, other)

    def __repr__(self):
        if not self:
            return 'OrderedDict()'
        items = ', '.join(f'({k!r}, {v!r})' for k, v in self.items())
        return f'OrderedDict([{items}])'

    def update(self, *args, **kwargs):
        if args:
            other = args[0]
            if hasattr(other, 'items'):
                for k, v in other.items():
                    self[k] = v
            else:
                for k, v in other:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def clear(self):
        super().clear()
        self._order.clear()

    def pop(self, key, *args):
        if key not in self:
            if args:
                return args[0]
            raise KeyError(key)
        value = self[key]
        del self[key]
        return value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


class _KeysView:
    def __init__(self, order):
        self._order = order

    def __iter__(self):
        return iter(self._order)

    def __len__(self):
        return len(self._order)

    def __contains__(self, item):
        return item in self._order

    def __repr__(self):
        return f'odict_keys({list(self._order)!r})'


class _ValuesView:
    def __init__(self, order, mapping):
        self._order = order
        self._mapping = mapping

    def __iter__(self):
        for k in self._order:
            yield self._mapping[k]

    def __len__(self):
        return len(self._order)

    def __repr__(self):
        return f'odict_values({[self._mapping[k] for k in self._order]!r})'


class _ItemsView:
    def __init__(self, order, mapping):
        self._order = order
        self._mapping = mapping

    def __iter__(self):
        for k in self._order:
            yield k, self._mapping[k]

    def __len__(self):
        return len(self._order)

    def __repr__(self):
        return f'odict_items({[(k, self._mapping[k]) for k in self._order]!r})'


# ─────────────────────────────────────────────────────────────────────────────
# defaultdict
# ─────────────────────────────────────────────────────────────────────────────

class defaultdict(dict):
    """
    A dict subclass that calls a factory function to supply missing values.
    """

    def __init__(self, default_factory=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if default_factory is not None and not callable(default_factory):
            raise TypeError('first argument must be callable or None')
        self.default_factory = default_factory

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = self.default_factory()
        return self[key]

    def copy(self):
        return defaultdict(self.default_factory, self)

    def __repr__(self):
        return f'defaultdict({self.default_factory!r}, {dict.__repr__(self)})'

    def __reduce__(self):
        return (self.__class__, (self.default_factory,), None, None, iter(self.items()))


# ─────────────────────────────────────────────────────────────────────────────
# deque
# ─────────────────────────────────────────────────────────────────────────────

class deque:
    """
    A double-ended queue with optional maxlen.
    """

    def __init__(self, iterable=None, maxlen=None):
        if maxlen is not None and maxlen < 0:
            raise ValueError('maxlen must be non-negative')
        self._maxlen = maxlen
        self._data = []
        if iterable is not None:
            for item in iterable:
                self.append(item)

    @property
    def maxlen(self):
        return self._maxlen

    def append(self, item):
        """Add item to the right side."""
        self._data.append(item)
        if self._maxlen is not None and len(self._data) > self._maxlen:
            self._data.pop(0)

    def appendleft(self, item):
        """Add item to the left side."""
        self._data.insert(0, item)
        if self._maxlen is not None and len(self._data) > self._maxlen:
            self._data.pop()

    def pop(self):
        """Remove and return the rightmost item."""
        if not self._data:
            raise IndexError('pop from an empty deque')
        return self._data.pop()

    def popleft(self):
        """Remove and return the leftmost item."""
        if not self._data:
            raise IndexError('pop from an empty deque')
        return self._data.pop(0)

    def extend(self, iterable):
        """Extend the right side by appending elements from the iterable."""
        for item in iterable:
            self.append(item)

    def extendleft(self, iterable):
        """Extend the left side by appending elements from the iterable (reversed)."""
        for item in iterable:
            self.appendleft(item)

    def rotate(self, n=1):
        """Rotate the deque n steps to the right (negative n rotates left)."""
        if not self._data:
            return
        length = len(self._data)
        n = n % length
        if n:
            self._data = self._data[-n:] + self._data[:-n]

    def clear(self):
        """Remove all elements."""
        self._data.clear()

    def count(self, value):
        """Count the number of occurrences of value."""
        return self._data.count(value)

    def remove(self, value):
        """Remove the first occurrence of value."""
        self._data.remove(value)

    def reverse(self):
        """Reverse the deque in place."""
        self._data.reverse()

    def copy(self):
        return deque(self._data, self._maxlen)

    def index(self, value, start=0, stop=None):
        if stop is None:
            stop = len(self._data)
        for i in range(start, min(stop, len(self._data))):
            if self._data[i] == value:
                return i
        raise ValueError(f'{value!r} is not in deque')

    def insert(self, i, value):
        if self._maxlen is not None and len(self._data) >= self._maxlen:
            raise IndexError('deque already at its maximum size')
        self._data.insert(i, value)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

    def __delitem__(self, index):
        del self._data[index]

    def __iter__(self):
        return iter(self._data)

    def __reversed__(self):
        return reversed(self._data)

    def __contains__(self, item):
        return item in self._data

    def __add__(self, other):
        if not isinstance(other, deque):
            raise TypeError(f'can only concatenate deque (not "{type(other).__name__}") to deque')
        return deque(list(self._data) + list(other._data))

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __mul__(self, n):
        return deque(self._data * n)

    def __imul__(self, n):
        self._data *= n
        if self._maxlen is not None:
            self._data = self._data[-self._maxlen:]
        return self

    def __eq__(self, other):
        if isinstance(other, deque):
            return self._data == other._data
        return NotImplemented

    def __repr__(self):
        if self._maxlen is None:
            return f'deque({self._data!r})'
        return f'deque({self._data!r}, maxlen={self._maxlen})'

    def __bool__(self):
        return bool(self._data)


# ─────────────────────────────────────────────────────────────────────────────
# namedtuple
# ─────────────────────────────────────────────────────────────────────────────

def namedtuple(typename, field_names, *, rename=False, defaults=None, module=None):
    """
    Returns a new subclass of tuple with named fields.
    """
    # Parse field_names
    if isinstance(field_names, str):
        # Can be comma or space separated
        field_names = field_names.replace(',', ' ').split()
    else:
        field_names = list(field_names)

    # Rename invalid fields if requested
    seen = set()
    for i, name in enumerate(field_names):
        need_rename = False
        if not isinstance(name, str):
            need_rename = True
        elif not name.isidentifier():
            need_rename = True
        elif _is_keyword(name):
            need_rename = True
        elif name.startswith('_'):
            need_rename = True
        elif name in seen:
            need_rename = True

        if need_rename:
            if rename:
                field_names[i] = f'_{i}'
            else:
                raise ValueError(f'Type names and field names must be valid identifiers: {name!r}')
        seen.add(field_names[i])

    field_names = tuple(field_names)
    n_fields = len(field_names)

    # Handle defaults
    if defaults is not None:
        defaults = tuple(defaults)
        if len(defaults) > n_fields:
            raise TypeError('Got more default values than field names')
    else:
        defaults = ()

    # Build __new__ with defaults
    n_defaults = len(defaults)
    n_required = n_fields - n_defaults

    class _NamedTupleMeta(tuple):
        __slots__ = ()
        _fields = field_names
        _field_defaults = dict(zip(field_names[n_required:], defaults))

        def __new__(cls, *args, **kwargs):
            # Fill in defaults
            args = list(args)
            # Apply kwargs
            for i, fname in enumerate(field_names):
                if i < len(args):
                    if fname in kwargs:
                        raise TypeError(f'__new__() got multiple values for argument {fname!r}')
                else:
                    if fname in kwargs:
                        args.append(kwargs.pop(fname))
                    elif i >= n_required:
                        args.append(defaults[i - n_required])
                    else:
                        raise TypeError(f'__new__() missing required argument: {fname!r}')
            if kwargs:
                raise TypeError(f'__new__() got unexpected keyword arguments: {list(kwargs.keys())}')
            if len(args) != n_fields:
                raise TypeError(f'__new__() takes {n_fields} positional arguments but {len(args)} were given')
            return tuple.__new__(cls, args)

        def _asdict(self):
            return {f: self[i] for i, f in enumerate(field_names)}

        def _replace(self, **kwargs):
            current = self._asdict()
            for k, v in kwargs.items():
                if k not in current:
                    raise ValueError(f'Got unexpected field names: {k!r}')
                current[k] = v
            return type(self)(**current)

        @classmethod
        def _make(cls, iterable):
            return cls(*iterable)

        def __repr__(self):
            fields = ', '.join(f'{f}={self[i]!r}' for i, f in enumerate(field_names))
            return f'{typename}({fields})'

        def __getnewargs__(self):
            return tuple(self)

        def __getnewargs_ex__(self):
            return tuple(self), {}

    # Add property accessors for each field
    for idx, fname in enumerate(field_names):
        def make_prop(i):
            return property(lambda self: tuple.__getitem__(self, i))
        setattr(_NamedTupleMeta, fname, make_prop(idx))

    _NamedTupleMeta.__name__ = typename
    _NamedTupleMeta.__qualname__ = typename
    if module is not None:
        _NamedTupleMeta.__module__ = module

    return _NamedTupleMeta


def _is_keyword(name):
    """Check if name is a Python keyword."""
    _keywords = {
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
        'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
        'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
        'while', 'with', 'yield'
    }
    return name in _keywords


# ─────────────────────────────────────────────────────────────────────────────
# ChainMap
# ─────────────────────────────────────────────────────────────────────────────

class ChainMap:
    """
    A ChainMap groups multiple dicts (or other mappings) together to create
    a single, updateable view.
    """

    def __init__(self, *maps):
        self.maps = list(maps) if maps else [{}]

    def __getitem__(self, key):
        for mapping in self.maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        return any(key in m for m in self.maps)

    def __len__(self):
        return len(set().union(*self.maps))

    def __iter__(self):
        seen = set()
        for mapping in self.maps:
            for key in mapping:
                if key not in seen:
                    seen.add(key)
                    yield key

    def __setitem__(self, key, value):
        self.maps[0][key] = value

    def __delitem__(self, key):
        try:
            del self.maps[0][key]
        except KeyError:
            raise KeyError(f'Key not found in the first mapping: {key!r}')

    def __bool__(self):
        return any(self.maps)

    def keys(self):
        return list(self)

    def values(self):
        return [self[k] for k in self]

    def items(self):
        return [(k, self[k]) for k in self]

    def new_child(self, m=None, **kwargs):
        """New ChainMap with a new map followed by all previous maps."""
        if m is None:
            m = {}
        m.update(kwargs)
        return ChainMap(m, *self.maps)

    @property
    def parents(self):
        """New ChainMap from maps[1:]."""
        return ChainMap(*self.maps[1:])

    def update(self, other=None, **kwargs):
        if other is not None:
            if hasattr(other, 'items'):
                for k, v in other.items():
                    self[k] = v
            else:
                for k, v in other:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def copy(self):
        return ChainMap(self.maps[0].copy(), *self.maps[1:])

    def __repr__(self):
        return f'ChainMap({", ".join(repr(m) for m in self.maps)})'

    def __eq__(self, other):
        if isinstance(other, ChainMap):
            return dict(self.items()) == dict(other.items())
        return NotImplemented

    def pop(self, key, *args):
        try:
            return self.maps[0].pop(key)
        except KeyError:
            if args:
                return args[0]
            raise KeyError(f'Key not found in the first mapping: {key!r}')

    def popitem(self):
        try:
            return self.maps[0].popitem()
        except KeyError:
            raise KeyError('No keys found in the first mapping')

    def clear(self):
        self.maps[0].clear()

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def fromkeys(self, iterable, value=None):
        return ChainMap(dict.fromkeys(iterable, value))


# ─────────────────────────────────────────────────────────────────────────────
# Invariant functions
# ─────────────────────────────────────────────────────────────────────────────

def collections4_most_common() -> bool:
    """
    Counter('aabbc').most_common(1)[0][0] is 'a' or 'b'.
    Returns True if the invariant holds.
    """
    c = Counter('aabbc')
    result = c.most_common(1)
    # The most common element should be 'a' or 'b' (both appear twice)
    top_element = result[0][0]
    return top_element in ('a', 'b')


def collections4_counter_update() -> int:
    """
    c = Counter({'a': 2}); c.update({'a': 1}); return c['a']  # should be 3
    """
    c = Counter({'a': 2})
    c.update({'a': 1})
    return c['a']


def collections4_counter_sub() -> int:
    """
    (Counter(a=3, b=1) - Counter(a=1))['a']  # should be 2
    """
    result = Counter(a=3, b=1) - Counter(a=1)
    return result['a']


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    'Counter',
    'OrderedDict',
    'defaultdict',
    'deque',
    'namedtuple',
    'ChainMap',
    'collections4_most_common',
    'collections4_counter_update',
    'collections4_counter_sub',
]