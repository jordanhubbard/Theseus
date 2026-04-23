"""
theseus_collections_cr5 - Clean-room extended collections utilities.
Do NOT import collections or any third-party library.
"""

# ─────────────────────────────────────────────
# ChainMap
# ─────────────────────────────────────────────

class ChainMap:
    """
    A view of multiple dicts as a single mapping.
    Lookup traverses maps in order; the first map that has the key wins.
    Writes/deletes always go to the first map.
    """

    def __init__(self, *maps):
        self.maps = list(maps) if maps else [{}]

    # ── read ──────────────────────────────────

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

    def keys(self):
        return list(self)

    def values(self):
        return [self[k] for k in self]

    def items(self):
        return [(k, self[k]) for k in self]

    # ── write (always to first map) ───────────

    def __setitem__(self, key, value):
        self.maps[0][key] = value

    def __delitem__(self, key):
        try:
            del self.maps[0][key]
        except KeyError:
            raise KeyError(f'Key not found in first map: {key!r}')

    # ── structural helpers ────────────────────

    def new_child(self, m=None):
        if m is None:
            m = {}
        return ChainMap(m, *self.maps)

    @property
    def parents(self):
        return ChainMap(*self.maps[1:])

    def __repr__(self):
        return f'{self.__class__.__name__}({", ".join(map(repr, self.maps))})'

    def copy(self):
        return self.__class__(*self.maps)

    __copy__ = copy

    def __eq__(self, other):
        if isinstance(other, ChainMap):
            return dict(self.items()) == dict(other.items())
        if isinstance(other, dict):
            return dict(self.items()) == other
        return NotImplemented


# ─────────────────────────────────────────────
# UserDict
# ─────────────────────────────────────────────

class UserDict:
    """
    A dict-like class that stores data in self.data.
    Subclass this instead of dict for easier customisation.
    """

    def __init__(self, initialdata=None, **kwargs):
        self.data = {}
        if initialdata is not None:
            if isinstance(initialdata, UserDict):
                self.data.update(initialdata.data)
            else:
                self.data.update(initialdata)
        if kwargs:
            self.data.update(kwargs)

    # ── core mapping interface ────────────────

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        # support subclass __missing__
        if hasattr(self.__class__, '__missing__'):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __repr__(self):
        return repr(self.data)

    def __eq__(self, other):
        if isinstance(other, UserDict):
            return self.data == other.data
        return self.data == other

    # ── dict-compatible helpers ───────────────

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def pop(self, key, *args):
        return self.data.pop(key, *args)

    def popitem(self):
        return self.data.popitem()

    def clear(self):
        self.data.clear()

    def update(self, other=None, **kwargs):
        if other is not None:
            if isinstance(other, UserDict):
                self.data.update(other.data)
            else:
                self.data.update(other)
        self.data.update(kwargs)

    def setdefault(self, key, default=None):
        return self.data.setdefault(key, default)

    def copy(self):
        return self.__class__(self.data.copy())

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d


# ─────────────────────────────────────────────
# UserList
# ─────────────────────────────────────────────

class UserList:
    """
    A list-like class that stores data in self.data.
    """

    def __init__(self, initlist=None):
        self.data = []
        if initlist is not None:
            if isinstance(initlist, UserList):
                self.data[:] = initlist.data[:]
            elif isinstance(initlist, list):
                self.data[:] = initlist[:]
            else:
                self.data = list(initlist)

    def __repr__(self):
        return repr(self.data)

    def __eq__(self, other):
        if isinstance(other, UserList):
            return self.data == other.data
        return self.data == other

    def __lt__(self, other):
        return self.data < (other.data if isinstance(other, UserList) else other)

    def __le__(self, other):
        return self.data <= (other.data if isinstance(other, UserList) else other)

    def __gt__(self, other):
        return self.data > (other.data if isinstance(other, UserList) else other)

    def __ge__(self, other):
        return self.data >= (other.data if isinstance(other, UserList) else other)

    def __contains__(self, item):
        return item in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, i, item):
        self.data[i] = item

    def __delitem__(self, i):
        del self.data[i]

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

    def __mul__(self, n):
        return self.__class__(self.data * n)

    __rmul__ = __mul__

    def __imul__(self, n):
        self.data *= n
        return self

    def __iter__(self):
        return iter(self.data)

    def append(self, item):
        self.data.append(item)

    def insert(self, i, item):
        self.data.insert(i, item)

    def pop(self, i=-1):
        return self.data.pop(i)

    def remove(self, item):
        self.data.remove(item)

    def clear(self):
        self.data.clear()

    def copy(self):
        return self.__class__(self.data[:])

    def count(self, item):
        return self.data.count(item)

    def index(self, item, *args):
        return self.data.index(item, *args)

    def reverse(self):
        self.data.reverse()

    def sort(self, /, *args, **kwargs):
        self.data.sort(*args, **kwargs)

    def extend(self, other):
        if isinstance(other, UserList):
            self.data.extend(other.data)
        else:
            self.data.extend(other)


# ─────────────────────────────────────────────
# UserString
# ─────────────────────────────────────────────

class UserString:
    """
    A string-like class that stores data in self.data.
    """

    def __init__(self, seq=''):
        if isinstance(seq, str):
            self.data = seq
        elif isinstance(seq, UserString):
            self.data = seq.data[:]
        else:
            self.data = str(seq)

    def __str__(self):
        return self.data

    def __repr__(self):
        return repr(self.data)

    def __hash__(self):
        return hash(self.data)

    def __eq__(self, other):
        if isinstance(other, UserString):
            return self.data == other.data
        return self.data == other

    def __lt__(self, other):
        return self.data < (other.data if isinstance(other, UserString) else other)

    def __le__(self, other):
        return self.data <= (other.data if isinstance(other, UserString) else other)

    def __gt__(self, other):
        return self.data > (other.data if isinstance(other, UserString) else other)

    def __ge__(self, other):
        return self.data >= (other.data if isinstance(other, UserString) else other)

    def __contains__(self, char):
        return char in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.__class__(self.data[index])

    def __add__(self, other):
        if isinstance(other, UserString):
            return self.__class__(self.data + other.data)
        return self.__class__(self.data + other)

    def __radd__(self, other):
        if isinstance(other, UserString):
            return self.__class__(other.data + self.data)
        return self.__class__(other + self.data)

    def __mul__(self, n):
        return self.__class__(self.data * n)

    __rmul__ = __mul__

    def __iter__(self):
        return iter(self.data)

    def __mod__(self, args):
        return self.__class__(self.data % args)

    # Delegate common str methods
    def upper(self): return self.__class__(self.data.upper())
    def lower(self): return self.__class__(self.data.lower())
    def strip(self, chars=None): return self.__class__(self.data.strip(chars))
    def lstrip(self, chars=None): return self.__class__(self.data.lstrip(chars))
    def rstrip(self, chars=None): return self.__class__(self.data.rstrip(chars))
    def split(self, sep=None, maxsplit=-1): return self.data.split(sep, maxsplit)
    def rsplit(self, sep=None, maxsplit=-1): return self.data.rsplit(sep, maxsplit)
    def join(self, seq): return self.__class__(self.data.join(seq))
    def replace(self, old, new, maxsplit=-1): return self.__class__(self.data.replace(old, new, maxsplit))
    def find(self, sub, *args): return self.data.find(sub, *args)
    def rfind(self, sub, *args): return self.data.rfind(sub, *args)
    def index(self, sub, *args): return self.data.index(sub, *args)
    def rindex(self, sub, *args): return self.data.rindex(sub, *args)
    def count(self, sub, *args): return self.data.count(sub, *args)
    def startswith(self, prefix, *args): return self.data.startswith(prefix, *args)
    def endswith(self, suffix, *args): return self.data.endswith(suffix, *args)
    def encode(self, encoding='utf-8', errors='strict'): return self.data.encode(encoding, errors)
    def capitalize(self): return self.__class__(self.data.capitalize())
    def title(self): return self.__class__(self.data.title())
    def swapcase(self): return self.__class__(self.data.swapcase())
    def center(self, width, *args): return self.__class__(self.data.center(width, *args))
    def ljust(self, width, *args): return self.__class__(self.data.ljust(width, *args))
    def rjust(self, width, *args): return self.__class__(self.data.rjust(width, *args))
    def zfill(self, width): return self.__class__(self.data.zfill(width))
    def expandtabs(self, tabsize=8): return self.__class__(self.data.expandtabs(tabsize))
    def isalpha(self): return self.data.isalpha()
    def isalnum(self): return self.data.isalnum()
    def isdecimal(self): return self.data.isdecimal()
    def isdigit(self): return self.data.isdigit()
    def isnumeric(self): return self.data.isnumeric()
    def isspace(self): return self.data.isspace()
    def istitle(self): return self.data.istitle()
    def isupper(self): return self.data.isupper()
    def islower(self): return self.data.islower()
    def splitlines(self, keepends=False): return self.data.splitlines(keepends)
    def partition(self, sep): return self.data.partition(sep)
    def rpartition(self, sep): return self.data.rpartition(sep)
    def format(self, *args, **kwargs): return self.__class__(self.data.format(*args, **kwargs))
    def format_map(self, mapping): return self.__class__(self.data.format_map(mapping))
    def maketrans(self, *args): return self.data.maketrans(*args)
    def translate(self, table): return self.__class__(self.data.translate(table))


# ─────────────────────────────────────────────
# Counter
# ─────────────────────────────────────────────

class Counter(dict):
    """
    A dict subclass for counting hashable objects.
    Elements are stored as dict keys and counts as dict values.
    """

    def __init__(self, iterable=None, /, **kwargs):
        super().__init__()
        self.update(iterable, **kwargs)

    def __missing__(self, key):
        return 0

    def most_common(self, n=None):
        pairs = sorted(self.items(), key=lambda x: x[1], reverse=True)
        return pairs if n is None else pairs[:n]

    def elements(self):
        for elem, count in self.items():
            if count > 0:
                for _ in range(count):
                    yield elem

    def subtract(self, iterable=None, /, **kwargs):
        if iterable is not None:
            if isinstance(iterable, dict):
                for key, val in iterable.items():
                    self[key] = self[key] - val
            else:
                for key in iterable:
                    self[key] = self[key] - 1
        for key, val in kwargs.items():
            self[key] = self[key] - val

    def update(self, iterable=None, /, **kwargs):
        if iterable is not None:
            if isinstance(iterable, dict):
                for key, val in iterable.items():
                    self[key] = self[key] + val
            elif isinstance(iterable, Counter):
                for key, val in iterable.items():
                    self[key] = self[key] + val
            else:
                for key in iterable:
                    self[key] = self[key] + 1
        for key, val in kwargs.items():
            self[key] = self[key] + val

    def copy(self):
        return Counter(self)

    def __add__(self, other):
        result = Counter()
        for key in set(list(self.keys()) + list(other.keys())):
            val = self[key] + other[key]
            if val > 0:
                result[key] = val
        return result

    def __sub__(self, other):
        result = Counter()
        for key in self:
            val = self[key] - other[key]
            if val > 0:
                result[key] = val
        return result

    def __or__(self, other):
        result = Counter()
        for key in set(list(self.keys()) + list(other.keys())):
            result[key] = max(self[key], other[key])
        return result

    def __and__(self, other):
        result = Counter()
        for key in self:
            val = min(self[key], other[key])
            if val > 0:
                result[key] = val
        return result

    def __repr__(self):
        if not self:
            return f'{self.__class__.__name__}()'
        items = ', '.join(f'{k!r}: {v!r}' for k, v in self.most_common())
        return f'{self.__class__.__name__}({{{items}}})'


# ─────────────────────────────────────────────
# OrderedDict
# ─────────────────────────────────────────────

class OrderedDict(dict):
    """
    A dict subclass that remembers insertion order.
    (In Python 3.7+ regular dicts are ordered, but this provides
    the extra move_to_end / popitem(last=) API.)
    """

    def __init__(self, other=None, /, **kwargs):
        super().__init__()
        self._order = []
        if other is not None:
            if isinstance(other, dict):
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
        return list(self._order)

    def values(self):
        return [self[k] for k in self._order]

    def items(self):
        return [(k, self[k]) for k in self._order]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        key = self._order[-1] if last else self._order[0]
        value = self[key]
        del self[key]
        return key, value

    def move_to_end(self, key, last=True):
        if key not in self:
            raise KeyError(key)
        self._order.remove(key)
        if last:
            self._order.append(key)
        else:
            self._order.insert(0, key)

    def copy(self):
        return OrderedDict(self.items())

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            return list(self.items()) == list(other.items())
        return dict.__eq__(self, other)

    def __repr__(self):
        items = ', '.join(f'({k!r}, {v!r})' for k, v in self.items())
        return f'{self.__class__.__name__}([{items}])'

    def update(self, other=None, /, **kwargs):
        if other is not None:
            if isinstance(other, dict):
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

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d


# ─────────────────────────────────────────────
# defaultdict
# ─────────────────────────────────────────────

class defaultdict(dict):
    """
    A dict subclass that calls a factory function to supply missing values.
    """

    def __init__(self, default_factory=None, /, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if default_factory is not None and not callable(default_factory):
            raise TypeError('first argument must be callable or None')
        self.default_factory = default_factory

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def copy(self):
        return defaultdict(self.default_factory, self)

    def __repr__(self):
        return (f'{self.__class__.__name__}({self.default_factory!r}, '
                f'{dict.__repr__(self)})')

    def __reduce__(self):
        return (self.__class__, (self.default_factory,), None, None, iter(self.items()))


# ─────────────────────────────────────────────
# deque
# ─────────────────────────────────────────────

class deque:
    """
    A double-ended queue with optional maxlen.
    """

    def __init__(self, iterable=(), maxlen=None):
        if maxlen is not None:
            if not isinstance(maxlen, int):
                raise TypeError('an integer is required')
            if maxlen < 0:
                raise ValueError('maxlen must be non-negative')
        self._maxlen = maxlen
        self._data = []
        for item in iterable:
            self.append(item)

    @property
    def maxlen(self):
        return self._maxlen

    def _trim_left(self):
        if self._maxlen is not None:
            while len(self._data) > self._maxlen:
                self._data.pop(0)

    def _trim_right(self):
        if self._maxlen is not None:
            while len(self._data) > self._maxlen:
                self._data.pop()

    def append(self, item):
        self._data.append(item)
        if self._maxlen is not None and len(self._data) > self._maxlen:
            self._data.pop(0)

    def appendleft(self, item):
        self._data.insert(0, item)
        if self._maxlen is not None and len(self._data) > self._maxlen:
            self._data.pop()

    def pop(self):
        if not self._data:
            raise IndexError('pop from an empty deque')
        return self._data.pop()

    def popleft(self):
        if not self._data:
            raise IndexError('pop from an empty deque')
        return self._data.pop(0)

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def extendleft(self, iterable):
        for item in iterable:
            self.appendleft(item)

    def rotate(self, n=1):
        if not self._data:
            return
        n = n % len(self._data) if self._data else 0
        if n:
            self._data[:] = self._data[-n:] + self._data[:-n]

    def clear(self):
        self._data.clear()

    def copy(self):
        return deque(self._data, self._maxlen)

    def count(self, value):
        return self._data.count(value)

    def index(self, value, start=0, stop=None):
        if stop is None:
            stop = len(self._data)
        for i in range(start, stop):
            if self._data[i] == value:
                return i
        raise ValueError(f'{value!r} is not in deque')

    def insert(self, i, value):
        if self._maxlen is not None and len(self._data) >= self._maxlen:
            raise IndexError('deque already at its maximum size')
        self._data.insert(i, value)

    def remove(self, value):
        self._data.remove(value)

    def reverse(self):
        self._data.reverse()

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

    def __delitem__(self, index):
        del self._data[index]

    def __contains__(self, item):
        return item in self._data

    def __iter__(self):
        return iter(self._data)

    def __reversed__(self):
        return reversed(self._data)

    def __repr__(self):
        if self._maxlen is None:
            return f'deque({self._data!r})'
        return f'deque({self._data!r}, maxlen={self._maxlen})'

    def __eq__(self, other):
        if isinstance(other, deque):
            return self._data == other._data
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, deque):
            return deque(self._data + other._data)
        return NotImplemented

    def __mul__(self, n):
        return deque(self._data * n, self._maxlen)

    __rmul__ = __mul__


# ─────────────────────────────────────────────
# Invariant functions
# ─────────────────────────────────────────────

def collections5_chainmap() -> bool:
    """
    ChainMap({'a':1},{'b':2})['a'] == 1 and ['b'] == 2.
    """
    cm = ChainMap({'a': 1}, {'b': 2})
    return cm['a'] == 1 and cm['b'] == 2


def collections5_chainmap_update() -> int:
    """
    ChainMap({'a':1},{'a':2})['a'] == 1 (first wins).
    Returns 1.
    """
    cm = ChainMap({'a': 1}, {'a': 2})
    return cm['a']


def collections5_userdict() -> int:
    """
    UserDict({'x':42})['x'] == 42.
    Returns 42.
    """
    ud = UserDict({'x': 42})
    return ud['x']


# ─────────────────────────────────────────────
# Public exports
# ─────────────────────────────────────────────

__all__ = [
    'ChainMap',
    'UserDict',
    'UserList',
    'UserString',
    'Counter',
    'OrderedDict',
    'defaultdict',
    'deque',
    'collections5_chainmap',
    'collections5_chainmap_update',
    'collections5_userdict',
]