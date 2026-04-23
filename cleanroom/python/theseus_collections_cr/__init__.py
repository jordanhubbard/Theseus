"""
theseus_collections_cr — Clean-room collections module.
No import of the standard `collections` module.
"""

import _collections_abc as _abc
import operator as _operator
import heapq as _heapq
import _collections


# namedtuple factory
def namedtuple(typename, field_names, *, rename=False, defaults=None, module=None):
    """Create a new tuple subclass with named fields."""
    if isinstance(field_names, str):
        field_names = field_names.replace(',', ' ').split()
    field_names = list(map(str, field_names))

    if rename:
        seen = set()
        for index, name in enumerate(field_names):
            if (not name.isidentifier() or name.startswith('_') or name in seen):
                field_names[index] = '_%d' % index
            seen.add(name)

    for name in [typename] + field_names:
        if not name.isidentifier():
            raise ValueError('Type names and field names must be valid identifiers: %r' % name)
        if name.startswith('_') and not rename:
            raise ValueError('Field names cannot start with an underscore: %r' % name)

    seen = set()
    for name in field_names:
        if name in seen:
            raise ValueError('Encountered duplicate field name: %r' % name)
        seen.add(name)

    if defaults is not None:
        defaults = tuple(defaults)
        if len(defaults) > len(field_names):
            raise TypeError('Got more default values than field names')

    field_defaults = {}
    if defaults:
        for field, default in zip(reversed(field_names), reversed(defaults)):
            field_defaults[field] = default

    # Build a new class
    num_fields = len(field_names)

    def __new__(cls, *args, **kwargs):
        if len(args) + len(kwargs) > num_fields:
            raise TypeError('%s takes %d positional arguments but %d were given' % (
                typename, num_fields, len(args) + len(kwargs)))
        values = list(args)
        for i, name in enumerate(field_names[len(args):], len(args)):
            if name in kwargs:
                values.append(kwargs.pop(name))
            elif name in field_defaults:
                values.append(field_defaults[name])
            else:
                raise TypeError("missing required argument: '%s'" % name)
        if kwargs:
            raise TypeError('%s got unexpected keyword arguments: %r' % (typename, list(kwargs)))
        return tuple.__new__(cls, values)

    def __repr__(self):
        items = ', '.join('%s=%r' % (name, self[i]) for i, name in enumerate(field_names))
        return '%s(%s)' % (typename, items)

    def _asdict(self):
        return dict(zip(field_names, self))

    def _replace(self, /, **kwds):
        result = self._asdict()
        result.update(kwds)
        return self.__class__(**result)

    @classmethod
    def _make(cls, iterable):
        return cls(*iterable)

    ns = {
        '__new__': __new__,
        '__repr__': __repr__,
        '__doc__': '%s(%s)' % (typename, ', '.join(field_names)),
        '_fields': tuple(field_names),
        '_field_defaults': field_defaults,
        '_asdict': _asdict,
        '_replace': _replace,
        '_make': _make,
    }
    for i, name in enumerate(field_names):
        ns[name] = property(lambda self, i=i: self[i])

    cls = type(typename, (tuple,), ns)
    if module is not None:
        cls.__module__ = module
    return cls


class deque:
    """Double-ended queue."""

    def __init__(self, iterable=(), maxlen=None):
        self._data = list(iterable)
        self._maxlen = maxlen
        if maxlen is not None:
            while len(self._data) > maxlen:
                self._data.pop(0)

    @property
    def maxlen(self):
        return self._maxlen

    def append(self, x):
        self._data.append(x)
        if self._maxlen is not None and len(self._data) > self._maxlen:
            self._data.pop(0)

    def appendleft(self, x):
        self._data.insert(0, x)
        if self._maxlen is not None and len(self._data) > self._maxlen:
            self._data.pop()

    def extend(self, iterable):
        for x in iterable:
            self.append(x)

    def extendleft(self, iterable):
        for x in iterable:
            self.appendleft(x)

    def pop(self):
        if not self._data:
            raise IndexError('pop from an empty deque')
        return self._data.pop()

    def popleft(self):
        if not self._data:
            raise IndexError('pop from an empty deque')
        return self._data.pop(0)

    def rotate(self, n=1):
        if self._data:
            n = n % len(self._data)
            if n:
                self._data = self._data[-n:] + self._data[:-n]

    def clear(self):
        self._data = []

    def copy(self):
        return deque(self._data, self._maxlen)

    def count(self, x):
        return self._data.count(x)

    def index(self, x, start=None, stop=None):
        data = self._data[start:stop]
        return data.index(x) + (start or 0)

    def insert(self, i, x):
        self._data.insert(i, x)
        if self._maxlen is not None and len(self._data) > self._maxlen:
            self._data.pop()

    def remove(self, x):
        self._data.remove(x)

    def reverse(self):
        self._data.reverse()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __reversed__(self):
        return reversed(self._data)

    def __contains__(self, x):
        return x in self._data

    def __getitem__(self, i):
        if i < 0:
            i += len(self._data)
        return self._data[i]

    def __setitem__(self, i, x):
        if i < 0:
            i += len(self._data)
        self._data[i] = x

    def __delitem__(self, i):
        del self._data[i]

    def __repr__(self):
        if self._maxlen is None:
            return 'deque(%r)' % (list(self._data),)
        return 'deque(%r, maxlen=%d)' % (list(self._data), self._maxlen)

    def __eq__(self, other):
        if isinstance(other, deque):
            return list(self._data) == list(other._data)
        return NotImplemented

    def __add__(self, other):
        if not isinstance(other, deque):
            return NotImplemented
        return deque(list(self) + list(other))

    def __mul__(self, other):
        return deque(list(self) * other, self._maxlen)

    def __imul__(self, other):
        self._data *= other
        return self

    def __iadd__(self, other):
        self.extend(other)
        return self


class Counter(dict):
    """Dict subclass for counting hashable items."""

    def __init__(self, iterable=None, /, **kwds):
        super().__init__()
        self.update(iterable, **kwds)

    def update(self, iterable=None, /, **kwds):
        if iterable is not None:
            if isinstance(iterable, dict):
                for k, v in iterable.items():
                    self[k] = self.get(k, 0) + v
            else:
                for k in iterable:
                    self[k] = self.get(k, 0) + 1
        for k, v in kwds.items():
            self[k] = self.get(k, 0) + v

    def subtract(self, iterable=None, /, **kwds):
        if iterable is not None:
            if isinstance(iterable, dict):
                for k, v in iterable.items():
                    self[k] = self.get(k, 0) - v
            else:
                for k in iterable:
                    self[k] = self.get(k, 0) - 1
        for k, v in kwds.items():
            self[k] = self.get(k, 0) - v

    def most_common(self, n=None):
        if n is None:
            return sorted(self.items(), key=lambda x: -x[1])
        return sorted(self.items(), key=lambda x: -x[1])[:n]

    def elements(self):
        for k, v in self.items():
            for _ in range(max(int(v), 0)):
                yield k

    def total(self):
        return sum(self.values())

    def __missing__(self, key):
        return 0

    def __repr__(self):
        if not self:
            return '%s()' % self.__class__.__name__
        items = ', '.join('%r: %r' % item for item in self.most_common())
        return '%s({%s})' % (self.__class__.__name__, items)

    def __add__(self, other):
        result = Counter()
        for k, v in self.items():
            new_v = v + other[k]
            if new_v > 0:
                result[k] = new_v
        for k, v in other.items():
            if k not in self and v > 0:
                result[k] = v
        return result

    def __sub__(self, other):
        result = Counter()
        for k, v in self.items():
            new_v = v - other[k]
            if new_v > 0:
                result[k] = new_v
        return result

    def __or__(self, other):
        result = Counter()
        for k in set(self) | set(other):
            new_v = max(self[k], other[k])
            if new_v > 0:
                result[k] = new_v
        return result

    def __and__(self, other):
        result = Counter()
        for k in set(self) & set(other):
            new_v = min(self[k], other[k])
            if new_v > 0:
                result[k] = new_v
        return result

    def __iadd__(self, other):
        for k, v in other.items():
            self[k] = self.get(k, 0) + v
        return +self

    def __isub__(self, other):
        for k, v in other.items():
            self[k] = self.get(k, 0) - v
        return +self

    def __pos__(self):
        result = Counter()
        for k, v in self.items():
            if v > 0:
                result[k] = v
        return result

    def __neg__(self):
        result = Counter()
        for k, v in self.items():
            if v < 0:
                result[k] = -v
        return result

    def copy(self):
        return Counter(self)

    @classmethod
    def fromkeys(cls, iterable, v=None):
        return super().fromkeys(iterable, v)


class defaultdict(dict):
    """Dict subclass that calls a default_factory for missing keys."""

    def __init__(self, default_factory=None, *args, **kwargs):
        if default_factory is not None and not callable(default_factory):
            raise TypeError('first argument must be callable or None')
        super().__init__(*args, **kwargs)
        self.default_factory = default_factory

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __repr__(self):
        return 'defaultdict(%s, %s)' % (self.default_factory, dict.__repr__(self))

    def copy(self):
        return type(self)(self.default_factory, self)

    def __reduce__(self):
        args = (self.default_factory,) if self.default_factory else ()
        return type(self), args, None, None, iter(self.items())


class OrderedDict(dict):
    """Dict that remembers insertion order."""

    def __init__(self, other=(), **kwargs):
        super().__init__()
        self.update(other, **kwargs)

    def move_to_end(self, key, last=True):
        value = self.pop(key)
        if last:
            self[key] = value
        else:
            items = list(self.items())
            self.clear()
            self[key] = value
            for k, v in items:
                self[k] = v

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = next(reversed(self))
        else:
            key = next(iter(self))
        value = self.pop(key)
        return key, value

    def copy(self):
        return type(self)(self)

    def __repr__(self):
        if not self:
            return '%s()' % type(self).__name__
        return '%s(%r)' % (type(self).__name__, list(self.items()))

    def __or__(self, other):
        if not isinstance(other, dict):
            return NotImplemented
        new = self.copy()
        new.update(other)
        return new

    def __ior__(self, other):
        self.update(other)
        return self


class ChainMap:
    """Group multiple mappings together."""

    def __init__(self, *maps):
        self.maps = list(maps) or [{}]

    def __missing__(self, key):
        raise KeyError(key)

    def __getitem__(self, key):
        for mapping in self.maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        return self.__missing__(key)

    def __setitem__(self, key, value):
        self.maps[0][key] = value

    def __delitem__(self, key):
        try:
            del self.maps[0][key]
        except KeyError:
            raise KeyError('Key not found in the first mapping: %r' % key)

    def __len__(self):
        return len(set().union(*self.maps))

    def __iter__(self):
        return iter(set().union(*self.maps))

    def __contains__(self, key):
        return any(key in m for m in self.maps)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(map(repr, self.maps)))

    def get(self, key, default=None):
        return self[key] if key in self else default

    def keys(self):
        return set().union(*self.maps)

    def values(self):
        return [self[k] for k in self]

    def items(self):
        return [(k, self[k]) for k in self]

    def new_child(self, m=None, **kwargs):
        if m is None:
            m = {}
        m.update(kwargs)
        return self.__class__(m, *self.maps)

    @property
    def parents(self):
        return self.__class__(*self.maps[1:])

    def update(self, other=(), **kwargs):
        if isinstance(other, dict):
            other = other.items()
        for k, v in other:
            self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def pop(self, key, *args):
        try:
            return self.maps[0].pop(key)
        except KeyError:
            if args:
                return args[0]
            raise KeyError('Key not found in the first mapping: %r' % key)

    def clear(self):
        self.maps[0].clear()

    def copy(self):
        return self.__class__(*self.maps)


class UserDict:
    """A user-accessible dict wrapper."""

    def __init__(self, dict=None, /, **kwargs):
        self.data = {}
        if dict is not None:
            self.update(dict)
        if kwargs:
            self.update(kwargs)

    def __len__(self): return len(self.data)
    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        if hasattr(self.__class__, '__missing__'):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)
    def __setitem__(self, key, item): self.data[key] = item
    def __delitem__(self, key): del self.data[key]
    def __iter__(self): return iter(self.data)
    def __contains__(self, key): return key in self.data
    def __repr__(self): return repr(self.data)
    def __or__(self, other):
        if isinstance(other, UserDict):
            return self.__class__(self.data | other.data)
        return self.__class__(self.data | other)
    def __ior__(self, other):
        if isinstance(other, UserDict):
            self.data |= other.data
        else:
            self.data |= other
        return self
    def get(self, key, default=None): return self.data.get(key, default)
    def keys(self): return self.data.keys()
    def items(self): return self.data.items()
    def values(self): return self.data.values()
    def pop(self, key, *args): return self.data.pop(key, *args)
    def popitem(self): return self.data.popitem()
    def clear(self): self.data.clear()
    def copy(self):
        if self.__class__ is UserDict:
            return UserDict(self.data.copy())
        import copy
        data = self.data
        try:
            self.data = {}
            c = copy.copy(self)
        finally:
            self.data = data
        c.update(self)
        return c
    def update(self, dict=None, /, **kwargs):
        if dict is not None:
            if isinstance(dict, UserDict):
                self.data.update(dict.data)
            elif isinstance(dict, type({})):
                self.data.update(dict)
            else:
                for k, v in dict.items() if hasattr(dict, 'items') else dict:
                    self.data[k] = v
        self.data.update(kwargs)
    def setdefault(self, key, failobj=None):
        if key not in self:
            self[key] = failobj
        return self[key]
    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d


class UserList(list):
    """A user-accessible list wrapper."""

    def __init__(self, initlist=None):
        self.data = []
        if initlist is not None:
            if type(initlist) == type(self.data):
                self.data[:] = initlist
            elif isinstance(initlist, UserList):
                self.data[:] = initlist.data[:]
            else:
                self.data = list(initlist)

    def __repr__(self): return repr(self.data)
    def __lt__(self, other): return self.data < self.__cast(other)
    def __le__(self, other): return self.data <= self.__cast(other)
    def __eq__(self, other): return self.data == self.__cast(other)
    def __gt__(self, other): return self.data > self.__cast(other)
    def __ge__(self, other): return self.data >= self.__cast(other)
    def __cast(self, other): return other.data if isinstance(other, UserList) else other
    def __contains__(self, item): return item in self.data
    def __len__(self): return len(self.data)
    def __getitem__(self, i): return self.data[i]
    def __setitem__(self, i, item): self.data[i] = item
    def __delitem__(self, i): del self.data[i]
    def __add__(self, other):
        if isinstance(other, UserList):
            return self.__class__(self.data + other.data)
        return self.__class__(self.data + list(other))
    def __radd__(self, other):
        if isinstance(other, UserList):
            return self.__class__(other.data + self.data)
        return self.__class__(list(other) + self.data)
    def __iadd__(self, other):
        if isinstance(other, UserList):
            self.data += other.data
        else:
            self.data += list(other)
        return self
    def __mul__(self, n): return self.__class__(self.data * n)
    def __imul__(self, n): self.data *= n; return self
    def __copy__(self): return self.__class__(self)
    def append(self, item): self.data.append(item)
    def insert(self, i, item): self.data.insert(i, item)
    def pop(self, i=-1): return self.data.pop(i)
    def remove(self, item): self.data.remove(item)
    def clear(self): self.data.clear()
    def copy(self): return self.__class__(self)
    def count(self, item): return self.data.count(item)
    def index(self, item, *args): return self.data.index(item, *args)
    def reverse(self): self.data.reverse()
    def sort(self, /, *args, **kwds): self.data.sort(*args, **kwds)
    def extend(self, other):
        if isinstance(other, UserList):
            self.data.extend(other.data)
        else:
            self.data.extend(other)
    def __iter__(self): return iter(self.data)


class UserString(str):
    """A user-accessible string wrapper."""

    def __init__(self, seq=''):
        if isinstance(seq, str):
            self.data = seq
        elif isinstance(seq, UserString):
            self.data = seq.data[:]
        else:
            self.data = str(seq)

    def __str__(self): return self.data
    def __repr__(self): return repr(self.data)
    def __len__(self): return len(self.data)
    def __contains__(self, char): return char in self.data
    def __bytes__(self): return self.data.encode()
    def __add__(self, other):
        if isinstance(other, UserString):
            return self.__class__(self.data + other.data)
        return self.__class__(self.data + other)
    def __radd__(self, other): return self.__class__(other + self.data)
    def __mul__(self, n): return self.__class__(self.data * n)
    def __rmul__(self, n): return self.__class__(self.data * n)
    def __mod__(self, args): return self.__class__(self.data % args)
    def __rmod__(self, template): return self.__class__(template % self.data)
    def __getitem__(self, i): return self.__class__(self.data[i])


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def collections2_counter():
    """Counter counts elements in an iterable; returns True."""
    c = Counter('aabbbcccc')
    return c['a'] == 2 and c['b'] == 3 and c['c'] == 4


def collections2_defaultdict():
    """defaultdict returns default for missing keys; returns True."""
    d = defaultdict(int)
    d['x'] += 1
    d['x'] += 1
    return d['x'] == 2 and d['y'] == 0


def collections2_deque():
    """deque supports appendleft and appendright; returns True."""
    dq = deque([1, 2, 3])
    dq.appendleft(0)
    dq.append(4)
    return list(dq) == [0, 1, 2, 3, 4]


__all__ = [
    'namedtuple', 'deque', 'Counter', 'defaultdict', 'OrderedDict',
    'ChainMap', 'UserDict', 'UserList', 'UserString',
    'collections2_counter', 'collections2_defaultdict', 'collections2_deque',
]
