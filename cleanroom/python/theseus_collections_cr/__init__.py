"""Clean-room implementation of collections module primitives.

Implements Counter, defaultdict, OrderedDict, deque, namedtuple, ChainMap
without importing the original collections module.
"""

import sys as _sys
from keyword import iskeyword as _iskeyword


# ---------------------------------------------------------------------------
# defaultdict
# ---------------------------------------------------------------------------

class defaultdict(dict):
    """dict subclass that calls a factory function for missing keys."""

    def __init__(self, default_factory=None, *args, **kwargs):
        if default_factory is not None and not callable(default_factory):
            raise TypeError("first argument must be callable or None")
        super().__init__(*args, **kwargs)
        self.default_factory = default_factory

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        value = self.default_factory()
        self[key] = value
        return value

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def copy(self):
        return type(self)(self.default_factory, self)

    def __copy__(self):
        return self.copy()

    def __reduce__(self):
        if self.default_factory is None:
            args = ()
        else:
            args = (self.default_factory,)
        return (type(self), args, None, None, iter(self.items()))

    def __repr__(self):
        return "defaultdict(%r, %s)" % (self.default_factory, dict.__repr__(self))


# ---------------------------------------------------------------------------
# Counter
# ---------------------------------------------------------------------------

class Counter(dict):
    """Dict subclass for counting hashable items."""

    def __init__(self, iterable=None, **kwds):
        super().__init__()
        self.update(iterable, **kwds)

    def __missing__(self, key):
        return 0

    def get(self, key, default=0):
        return dict.get(self, key, default)

    def update(self, iterable=None, **kwds):
        if iterable is not None:
            if isinstance(iterable, dict):
                for elem, count in iterable.items():
                    self[elem] = dict.get(self, elem, 0) + count
            else:
                for elem in iterable:
                    self[elem] = dict.get(self, elem, 0) + 1
        if kwds:
            self.update(kwds)

    def subtract(self, iterable=None, **kwds):
        if iterable is not None:
            if isinstance(iterable, dict):
                for elem, count in iterable.items():
                    self[elem] = dict.get(self, elem, 0) - count
            else:
                for elem in iterable:
                    self[elem] = dict.get(self, elem, 0) - 1
        if kwds:
            self.subtract(kwds)

    def most_common(self, n=None):
        items = sorted(self.items(), key=lambda kv: kv[1], reverse=True)
        if n is None:
            return items
        return items[:n]

    def elements(self):
        for elem, count in self.items():
            if count > 0:
                for _ in range(count):
                    yield elem

    def total(self):
        return sum(self.values())

    def copy(self):
        return Counter(self)

    def __copy__(self):
        return self.copy()

    def __delitem__(self, elem):
        if elem in self:
            dict.__delitem__(self, elem)

    def __add__(self, other):
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for elem in self:
            v = self[elem] + other.get(elem, 0)
            if v > 0:
                result[elem] = v
        for elem in other:
            if elem not in self and other[elem] > 0:
                result[elem] = other[elem]
        return result

    def __sub__(self, other):
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for elem in self:
            v = self[elem] - other.get(elem, 0)
            if v > 0:
                result[elem] = v
        for elem in other:
            if elem not in self and other[elem] < 0:
                result[elem] = -other[elem]
        return result

    def __or__(self, other):
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for elem in self:
            v = self[elem]
            o = other.get(elem, 0)
            m = v if v > o else o
            if m > 0:
                result[elem] = m
        for elem in other:
            if elem not in self and other[elem] > 0:
                result[elem] = other[elem]
        return result

    def __and__(self, other):
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for elem in self:
            if elem in other:
                v = self[elem]
                o = other[elem]
                m = v if v < o else o
                if m > 0:
                    result[elem] = m
        return result

    def __pos__(self):
        result = Counter()
        for elem, count in self.items():
            if count > 0:
                result[elem] = count
        return result

    def __neg__(self):
        result = Counter()
        for elem, count in self.items():
            if count < 0:
                result[elem] = -count
        return result

    def __repr__(self):
        if not self:
            return "Counter()"
        items = sorted(self.items(), key=lambda kv: kv[1], reverse=True)
        body = ", ".join("%r: %r" % (k, v) for k, v in items)
        return "Counter({%s})" % body


# ---------------------------------------------------------------------------
# deque (doubly linked list implementation)
# ---------------------------------------------------------------------------

class _DequeNode:
    __slots__ = ('value', 'prev', 'next')

    def __init__(self, value):
        self.value = value
        self.prev = None
        self.next = None


class deque:
    """Double-ended queue with O(1) appends/pops on either end."""

    def __init__(self, iterable=None, maxlen=None):
        if maxlen is not None:
            if not isinstance(maxlen, int):
                raise TypeError("an integer is required")
            if maxlen < 0:
                raise ValueError("maxlen must be non-negative")
        self._head = None
        self._tail = None
        self._size = 0
        self._maxlen = maxlen
        if iterable is not None:
            self.extend(iterable)

    @property
    def maxlen(self):
        return self._maxlen

    def __len__(self):
        return self._size

    def append(self, value):
        if self._maxlen == 0:
            return
        node = _DequeNode(value)
        if self._tail is None:
            self._head = node
            self._tail = node
        else:
            node.prev = self._tail
            self._tail.next = node
            self._tail = node
        self._size += 1
        if self._maxlen is not None and self._size > self._maxlen:
            self.popleft()

    def appendleft(self, value):
        if self._maxlen == 0:
            return
        node = _DequeNode(value)
        if self._head is None:
            self._head = node
            self._tail = node
        else:
            node.next = self._head
            self._head.prev = node
            self._head = node
        self._size += 1
        if self._maxlen is not None and self._size > self._maxlen:
            self.pop()

    def pop(self):
        if self._tail is None:
            raise IndexError("pop from an empty deque")
        node = self._tail
        value = node.value
        self._tail = node.prev
        if self._tail is None:
            self._head = None
        else:
            self._tail.next = None
        self._size -= 1
        return value

    def popleft(self):
        if self._head is None:
            raise IndexError("pop from an empty deque")
        node = self._head
        value = node.value
        self._head = node.next
        if self._head is None:
            self._tail = None
        else:
            self._head.prev = None
        self._size -= 1
        return value

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def extendleft(self, iterable):
        for item in iterable:
            self.appendleft(item)

    def clear(self):
        self._head = None
        self._tail = None
        self._size = 0

    def copy(self):
        return deque(self, maxlen=self._maxlen)

    def __copy__(self):
        return self.copy()

    def __iter__(self):
        node = self._head
        while node is not None:
            yield node.value
            node = node.next

    def __reversed__(self):
        node = self._tail
        while node is not None:
            yield node.value
            node = node.prev

    def __contains__(self, value):
        for v in self:
            if v == value:
                return True
        return False

    def _node_at(self, index):
        if index < 0:
            index += self._size
        if index < 0 or index >= self._size:
            raise IndexError("deque index out of range")
        if index <= self._size // 2:
            node = self._head
            for _ in range(index):
                node = node.next
        else:
            node = self._tail
            for _ in range(self._size - 1 - index):
                node = node.prev
        return node

    def __getitem__(self, index):
        return self._node_at(index).value

    def __setitem__(self, index, value):
        self._node_at(index).value = value

    def __delitem__(self, index):
        node = self._node_at(index)
        if node.prev is None:
            self._head = node.next
        else:
            node.prev.next = node.next
        if node.next is None:
            self._tail = node.prev
        else:
            node.next.prev = node.prev
        self._size -= 1

    def rotate(self, n=1):
        if self._size <= 1:
            return
        n = n % self._size
        if n == 0:
            return
        if n > 0:
            for _ in range(n):
                self.appendleft(self.pop())
        else:
            for _ in range(-n):
                self.append(self.popleft())

    def reverse(self):
        node = self._head
        new_head = self._tail
        while node is not None:
            nxt = node.next
            node.prev, node.next = node.next, node.prev
            node = nxt
        self._head, self._tail = self._tail, self._head

    def count(self, value):
        c = 0
        for v in self:
            if v == value:
                c += 1
        return c

    def index(self, value, start=0, stop=None):
        if stop is None:
            stop = self._size
        i = 0
        for v in self:
            if i >= stop:
                break
            if i >= start and v == value:
                return i
            i += 1
        raise ValueError("%r is not in deque" % (value,))

    def remove(self, value):
        node = self._head
        while node is not None:
            if node.value == value:
                if node.prev is None:
                    self._head = node.next
                else:
                    node.prev.next = node.next
                if node.next is None:
                    self._tail = node.prev
                else:
                    node.next.prev = node.prev
                self._size -= 1
                return
            node = node.next
        raise ValueError("deque.remove(x): x not in deque")

    def insert(self, index, value):
        if self._maxlen is not None and self._size >= self._maxlen:
            raise IndexError("deque already at its maximum size")
        if index < 0:
            index += self._size
            if index < 0:
                index = 0
        if index >= self._size:
            self.append(value)
            return
        if index <= 0:
            self.appendleft(value)
            return
        cur = self._node_at(index)
        node = _DequeNode(value)
        node.next = cur
        node.prev = cur.prev
        cur.prev.next = node
        cur.prev = node
        self._size += 1

    def __eq__(self, other):
        if isinstance(other, deque):
            if self._size != other._size:
                return False
            for a, b in zip(self, other):
                if a != b:
                    return False
            return True
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __bool__(self):
        return self._size > 0

    def __add__(self, other):
        if not isinstance(other, deque):
            return NotImplemented
        result = deque(self, maxlen=self._maxlen)
        result.extend(other)
        return result

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __mul__(self, n):
        if not isinstance(n, int):
            return NotImplemented
        if n <= 0:
            return deque(maxlen=self._maxlen)
        result = deque(maxlen=self._maxlen)
        for _ in range(n):
            result.extend(self)
        return result

    def __repr__(self):
        items = list(self)
        if self._maxlen is None:
            return "deque(%r)" % (items,)
        return "deque(%r, maxlen=%d)" % (items, self._maxlen)


# ---------------------------------------------------------------------------
# OrderedDict
# ---------------------------------------------------------------------------

class OrderedDict(dict):
    """Dict that remembers insertion order and supports move_to_end."""

    def __init__(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError("expected at most 1 argument, got %d" % len(args))
        super().__init__()
        if args:
            src = args[0]
            if hasattr(src, 'keys'):
                for k in src.keys():
                    self[k] = src[k]
            else:
                for k, v in src:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def move_to_end(self, key, last=True):
        if key not in self:
            raise KeyError(key)
        value = dict.__getitem__(self, key)
        dict.__delitem__(self, key)
        if last:
            dict.__setitem__(self, key, value)
        else:
            items = [(key, value)] + [(k, dict.__getitem__(self, k)) for k in list(self.keys())]
            dict.clear(self)
            for k, v in items:
                dict.__setitem__(self, k, v)

    def popitem(self, last=True):
        if not self:
            raise KeyError("dictionary is empty")
        if last:
            key = next(reversed(list(self.keys())))
        else:
            key = next(iter(self.keys()))
        value = dict.__getitem__(self, key)
        dict.__delitem__(self, key)
        return key, value

    def copy(self):
        return OrderedDict(self)

    def __copy__(self):
        return self.copy()

    def __reduce__(self):
        return (type(self), (list(self.items()),))

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for (k1, v1), (k2, v2) in zip(self.items(), other.items()):
                if k1 != k2 or v1 != v2:
                    return False
            return True
        if isinstance(other, dict):
            return dict.__eq__(self, other)
        return NotImplemented

    def __ne__(self, other):
        r = self.__eq__(other)
        if r is NotImplemented:
            return r
        return not r

    def __repr__(self):
        if not self:
            return "OrderedDict()"
        return "OrderedDict(%r)" % (list(self.items()),)


# ---------------------------------------------------------------------------
# namedtuple
# ---------------------------------------------------------------------------

def namedtuple(typename, field_names, *, rename=False, defaults=None, module=None):
    """Returns a new tuple subclass named typename."""
    if isinstance(field_names, str):
        field_names = field_names.replace(',', ' ').split()
    field_names = list(map(str, field_names))

    if rename:
        seen = set()
        for i, name in enumerate(field_names):
            if (not name.isidentifier()
                    or _iskeyword(name)
                    or name.startswith('_')
                    or name in seen):
                field_names[i] = '_%d' % i
            seen.add(name)

    for name in [typename] + field_names:
        if not isinstance(name, str):
            raise TypeError("Type names and field names must be strings")
        if not name.isidentifier():
            raise ValueError("Type names and field names must be valid identifiers: %r" % name)
        if _iskeyword(name):
            raise ValueError("Type names and field names cannot be a keyword: %r" % name)

    seen = set()
    for name in field_names:
        if name.startswith('_') and not rename:
            raise ValueError("Field names cannot start with an underscore: %r" % name)
        if name in seen:
            raise ValueError("Encountered duplicate field name: %r" % name)
        seen.add(name)

    field_names = tuple(field_names)
    n = len(field_names)

    if defaults is not None:
        defaults = tuple(defaults)
        if len(defaults) > n:
            raise TypeError("Got more default values than field names")
    else:
        defaults = ()

    def _new(cls, *args, **kwargs):
        if len(args) > n:
            raise TypeError("__new__() takes %d positional arguments but %d were given"
                            % (n + 1, len(args) + 1))
        values = list(args)
        remaining = field_names[len(args):]
        for fname in remaining:
            if fname in kwargs:
                values.append(kwargs.pop(fname))
            else:
                default_start = n - len(defaults)
                idx = field_names.index(fname)
                if idx >= default_start:
                    values.append(defaults[idx - default_start])
                else:
                    raise TypeError("__new__() missing required argument: %r" % fname)
        if kwargs:
            raise TypeError("__new__() got unexpected keyword arguments: %r" % list(kwargs))
        return tuple.__new__(cls, values)

    def _repr(self):
        body = ", ".join("%s=%r" % (fn, getattr(self, fn)) for fn in field_names)
        return "%s(%s)" % (typename, body)

    def _asdict(self):
        return {fn: getattr(self, fn) for fn in field_names}

    def _replace(self, **kwargs):
        values = list(self)
        for k, v in kwargs.items():
            if k not in field_names:
                raise ValueError("Got unexpected field names: %r" % [k])
            values[field_names.index(k)] = v
        return type(self)(*values)

    def _make(cls, iterable):
        result = tuple.__new__(cls, iterable)
        if len(result) != n:
            raise TypeError("Expected %d arguments, got %d" % (n, len(result)))
        return result

    cls_dict = {
        '__new__': _new,
        '__repr__': _repr,
        '__slots__': (),
        '_fields': field_names,
        '_field_defaults': dict(zip(field_names[n - len(defaults):], defaults)),
        '_asdict': _asdict,
        '_replace': _replace,
        '_make': classmethod(_make),
    }

    for i, fname in enumerate(field_names):
        def make_getter(idx):
            def getter(self, _idx=idx):
                return tuple.__getitem__(self, _idx)
            return property(getter)
        cls_dict[fname] = make_getter(i)

    cls = type(typename, (tuple,), cls_dict)

    if module is None:
        try:
            module = _sys._getframe(1).f_globals.get('__name__', '__main__')
        except (AttributeError, ValueError):
            module = '__main__'
    cls.__module__ = module

    return cls


# ---------------------------------------------------------------------------
# ChainMap
# ---------------------------------------------------------------------------

class ChainMap:
    """Groups multiple dicts (or mappings) together to create a single view."""

    def __init__(self, *maps):
        self.maps = list(maps) if maps else [{}]

    def __getitem__(self, key):
        for m in self.maps:
            if key in m:
                return m[key]
        return self.__missing__(key)

    def __missing__(self, key):
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        keys = set()
        for m in self.maps:
            keys.update(m.keys())
        return len(keys)

    def __iter__(self):
        seen = set()
        for m in self.maps:
            for k in m:
                if k not in seen:
                    seen.add(k)
                    yield k

    def __contains__(self, key):
        return any(key in m for m in self.maps)

    def __bool__(self):
        return any(self.maps)

    def keys(self):
        return list(iter(self))

    def values(self):
        return [self[k] for k in self]

    def items(self):
        return [(k, self[k]) for k in self]

    @property
    def parents(self):
        return ChainMap(*self.maps[1:])

    def new_child(self, m=None):
        if m is None:
            m = {}
        return ChainMap(m, *self.maps)

    def __setitem__(self, key, value):
        self.maps[0][key] = value

    def __delitem__(self, key):
        try:
            del self.maps[0][key]
        except KeyError:
            raise KeyError("Key not found in the first mapping: %r" % (key,))

    def pop(self, key, *args):
        try:
            return self.maps[0].pop(key, *args) if args else self.maps[0].pop(key)
        except KeyError:
            raise KeyError("Key not found in the first mapping: %r" % (key,))

    def popitem(self):
        try:
            return self.maps[0].popitem()
        except KeyError:
            raise KeyError("No keys found in the first mapping.")

    def clear(self):
        self.maps[0].clear()

    def copy(self):
        first = dict(self.maps[0])
        return ChainMap(first, *self.maps[1:])

    def __copy__(self):
        return self.copy()

    def __repr__(self):
        return "ChainMap(%s)" % ", ".join(repr(m) for m in self.maps)


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def collections2_counter():
    c = Counter("abracadabra")
    if c['a'] != 5:
        return False
    if c['b'] != 2:
        return False
    if c['r'] != 2:
        return False
    if c['c'] != 1:
        return False
    if c['z'] != 0:
        return False
    mc = c.most_common(2)
    if len(mc) != 2:
        return False
    if mc[0][0] != 'a' or mc[0][1] != 5:
        return False
    c2 = Counter({'x': 2, 'y': 3})
    c.update(c2)
    if c['x'] != 2 or c['y'] != 3:
        return False
    c.subtract({'a': 1})
    if c['a'] != 4:
        return False
    elements = sorted(Counter("aab").elements())
    if elements != ['a', 'a', 'b']:
        return False
    s = Counter(a=3, b=1) + Counter(a=1, c=2)
    if s['a'] != 4 or s['b'] != 1 or s['c'] != 2:
        return False
    return True


def collections2_defaultdict():
    d = defaultdict(list)
    d['a'].append(1)
    d['a'].append(2)
    d['b'].append(3)
    if d['a'] != [1, 2]:
        return False
    if d['b'] != [3]:
        return False
    if 'c' in d:
        return False
    _ = d['c']
    if d['c'] != []:
        return False

    d2 = defaultdict(int)
    d2['x'] += 1
    d2['x'] += 2
    if d2['x'] != 3:
        return False

    d3 = defaultdict(None)
    d3['k'] = 1
    if d3['k'] != 1:
        return False
    try:
        _ = d3['missing']
    except KeyError:
        pass
    else:
        return False

    d4 = defaultdict(lambda: "default")
    if d4['anything'] != "default":
        return False

    return True


def collections2_deque():
    d = deque([1, 2, 3])
    d.append(4)
    d.appendleft(0)
    if list(d) != [0, 1, 2, 3, 4]:
        return False
    if len(d) != 5:
        return False
    if d.pop() != 4:
        return False
    if d.popleft() != 0:
        return False
    if list(d) != [1, 2, 3]:
        return False

    bounded = deque(maxlen=3)
    for i in range(5):
        bounded.append(i)
    if list(bounded) != [2, 3, 4]:
        return False
    if bounded.maxlen != 3:
        return False

    rot = deque([1, 2, 3, 4, 5])
    rot.rotate(2)
    if list(rot) != [4, 5, 1, 2, 3]:
        return False
    rot.rotate(-2)
    if list(rot) != [1, 2, 3, 4, 5]:
        return False

    e = deque()
    try:
        e.pop()
    except IndexError:
        pass
    else:
        return False

    rev = deque([1, 2, 3])
    if list(reversed(rev)) != [3, 2, 1]:
        return False

    if 2 not in rev:
        return False
    if rev.count(2) != 1:
        return False

    rev[0] = 99
    if rev[0] != 99:
        return False

    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    'Counter',
    'defaultdict',
    'OrderedDict',
    'deque',
    'namedtuple',
    'ChainMap',
    'collections2_counter',
    'collections2_defaultdict',
    'collections2_deque',
]