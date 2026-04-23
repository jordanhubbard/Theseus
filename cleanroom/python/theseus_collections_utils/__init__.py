"""
Theseus Collections Utils - Clean-room implementation of common collection types.
No import of the `collections` module allowed.
"""


class Counter:
    """
    Counts element frequencies from an iterable.
    Counter('aabbc')['a'] == 2
    """

    def __init__(self, iterable=None):
        self._data = {}
        if iterable is not None:
            for item in iterable:
                self._data[item] = self._data.get(item, 0) + 1

    def __getitem__(self, key):
        return self._data.get(key, 0)

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"Counter({self._data!r})"

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def get(self, key, default=0):
        return self._data.get(key, default)

    def most_common(self, n=None):
        sorted_items = sorted(self._data.items(), key=lambda x: x[1], reverse=True)
        if n is None:
            return sorted_items
        return sorted_items[:n]

    def update(self, iterable=None, **kwargs):
        if iterable is not None:
            if hasattr(iterable, 'items'):
                for key, count in iterable.items():
                    self._data[key] = self._data.get(key, 0) + count
            else:
                for item in iterable:
                    self._data[item] = self._data.get(item, 0) + 1
        for key, count in kwargs.items():
            self._data[key] = self._data.get(key, 0) + count

    def subtract(self, iterable=None, **kwargs):
        if iterable is not None:
            if hasattr(iterable, 'items'):
                for key, count in iterable.items():
                    self._data[key] = self._data.get(key, 0) - count
            else:
                for item in iterable:
                    self._data[item] = self._data.get(item, 0) - 1
        for key, count in kwargs.items():
            self._data[key] = self._data.get(key, 0) - count

    def elements(self):
        for key, count in self._data.items():
            for _ in range(max(0, count)):
                yield key

    def total(self):
        return sum(self._data.values())

    def __add__(self, other):
        result = Counter()
        for key in set(list(self._data.keys()) + list(other._data.keys())):
            val = self[key] + other[key]
            if val > 0:
                result[key] = val
        return result

    def __sub__(self, other):
        result = Counter()
        for key in self._data:
            val = self[key] - other[key]
            if val > 0:
                result[key] = val
        return result

    def __eq__(self, other):
        if isinstance(other, Counter):
            return self._data == other._data
        return NotImplemented

    def copy(self):
        c = Counter()
        c._data = dict(self._data)
        return c


class defaultdict:
    """
    A dict-like object that returns default_factory() for missing keys.
    """

    def __init__(self, default_factory=None, *args, **kwargs):
        self.default_factory = default_factory
        self._data = {}
        # Handle initialization from mapping or iterable
        if args:
            if len(args) == 1:
                arg = args[0]
                if hasattr(arg, 'items'):
                    for k, v in arg.items():
                        self._data[k] = v
                else:
                    for k, v in arg:
                        self._data[k] = v
            else:
                raise TypeError("defaultdict expected at most 1 positional argument after default_factory")
        for k, v in kwargs.items():
            self._data[k] = v

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        value = self.default_factory()
        self._data[key] = value
        return value

    def __getitem__(self, key):
        if key not in self._data:
            return self.__missing__(key)
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"defaultdict({self.default_factory!r}, {self._data!r})"

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, *args):
        return self._data.pop(key, *args)

    def setdefault(self, key, default=None):
        if key not in self._data:
            self._data[key] = default
        return self._data[key]

    def update(self, other=None, **kwargs):
        if other is not None:
            if hasattr(other, 'items'):
                for k, v in other.items():
                    self._data[k] = v
            else:
                for k, v in other:
                    self._data[k] = v
        for k, v in kwargs.items():
            self._data[k] = v

    def copy(self):
        d = defaultdict(self.default_factory)
        d._data = dict(self._data)
        return d

    def __eq__(self, other):
        if isinstance(other, defaultdict):
            return self._data == other._data
        if isinstance(other, dict):
            return self._data == other
        return NotImplemented


class _DequeNode:
    __slots__ = ('value', 'prev', 'next')

    def __init__(self, value, prev=None, next=None):
        self.value = value
        self.prev = prev
        self.next = next


class deque:
    """
    Double-ended queue with appendleft/popleft/append/pop.
    Supports optional maxlen.
    """

    def __init__(self, iterable=None, maxlen=None):
        self.maxlen = maxlen
        self._head = None  # leftmost
        self._tail = None  # rightmost
        self._size = 0

        if iterable is not None:
            for item in iterable:
                self.append(item)

    def _append_node(self, node):
        """Append node to the right."""
        if self._tail is None:
            self._head = self._tail = node
            node.prev = None
            node.next = None
        else:
            node.prev = self._tail
            node.next = None
            self._tail.next = node
            self._tail = node
        self._size += 1

    def _appendleft_node(self, node):
        """Append node to the left."""
        if self._head is None:
            self._head = self._tail = node
            node.prev = None
            node.next = None
        else:
            node.next = self._head
            node.prev = None
            self._head.prev = node
            self._head = node
        self._size += 1

    def append(self, value):
        """Append to the right."""
        node = _DequeNode(value)
        self._append_node(node)
        if self.maxlen is not None and self._size > self.maxlen:
            self.popleft()

    def appendleft(self, value):
        """Append to the left."""
        node = _DequeNode(value)
        self._appendleft_node(node)
        if self.maxlen is not None and self._size > self.maxlen:
            self.pop()

    def pop(self):
        """Remove and return from the right."""
        if self._tail is None:
            raise IndexError("pop from an empty deque")
        value = self._tail.value
        if self._head is self._tail:
            self._head = self._tail = None
        else:
            self._tail = self._tail.prev
            self._tail.next = None
        self._size -= 1
        return value

    def popleft(self):
        """Remove and return from the left."""
        if self._head is None:
            raise IndexError("pop from an empty deque")
        value = self._head.value
        if self._head is self._tail:
            self._head = self._tail = None
        else:
            self._head = self._head.next
            self._head.prev = None
        self._size -= 1
        return value

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def extendleft(self, iterable):
        for item in iterable:
            self.appendleft(item)

    def rotate(self, n=1):
        if self._size == 0:
            return
        n = n % self._size
        if n == 0:
            return
        for _ in range(n):
            self.appendleft(self.pop())

    def clear(self):
        self._head = self._tail = None
        self._size = 0

    def __len__(self):
        return self._size

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

    def __repr__(self):
        items = list(self)
        if self.maxlen is None:
            return f"deque({items!r})"
        return f"deque({items!r}, maxlen={self.maxlen})"

    def __contains__(self, value):
        for item in self:
            if item == value:
                return True
        return False

    def __getitem__(self, index):
        if index < 0:
            index += self._size
        if index < 0 or index >= self._size:
            raise IndexError("deque index out of range")
        node = self._head
        for _ in range(index):
            node = node.next
        return node.value

    def __setitem__(self, index, value):
        if index < 0:
            index += self._size
        if index < 0 or index >= self._size:
            raise IndexError("deque index out of range")
        node = self._head
        for _ in range(index):
            node = node.next
        node.value = value

    def __eq__(self, other):
        if isinstance(other, deque):
            if self._size != other._size:
                return False
            for a, b in zip(self, other):
                if a != b:
                    return False
            return True
        return NotImplemented

    def count(self, value):
        return sum(1 for item in self if item == value)

    def index(self, value, start=0, stop=None):
        if stop is None:
            stop = self._size
        for i, item in enumerate(self):
            if i < start:
                continue
            if i >= stop:
                break
            if item == value:
                return i
        raise ValueError(f"{value!r} is not in deque")

    def remove(self, value):
        node = self._head
        while node is not None:
            if node.value == value:
                if node.prev is not None:
                    node.prev.next = node.next
                else:
                    self._head = node.next
                if node.next is not None:
                    node.next.prev = node.prev
                else:
                    self._tail = node.prev
                self._size -= 1
                return
            node = node.next
        raise ValueError(f"{value!r} is not in deque")

    def copy(self):
        return deque(self, maxlen=self.maxlen)


class OrderedDict:
    """
    A dict that remembers insertion order.
    Iteration order matches insertion order.
    """

    def __init__(self, *args, **kwargs):
        self._keys = []  # insertion-ordered list of keys
        self._data = {}

        if args:
            if len(args) > 1:
                raise TypeError(f"OrderedDict expected at most 1 argument, got {len(args)}")
            arg = args[0]
            if hasattr(arg, 'items'):
                for k, v in arg.items():
                    self[k] = v
            else:
                for k, v in arg:
                    self[k] = v

        for k, v in kwargs.items():
            self[k] = v

    def __setitem__(self, key, value):
        if key not in self._data:
            self._keys.append(key)
        self._data[key] = value

    def __getitem__(self, key):
        if key not in self._data:
            raise KeyError(key)
        return self._data[key]

    def __delitem__(self, key):
        if key not in self._data:
            raise KeyError(key)
        del self._data[key]
        self._keys.remove(key)

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._keys)

    def __repr__(self):
        items = ", ".join(f"{k!r}: {self._data[k]!r}" for k in self._keys)
        return f"OrderedDict({{{items}}})"

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for (k1, v1), (k2, v2) in zip(self.items(), other.items()):
                if k1 != k2 or v1 != v2:
                    return False
            return True
        if isinstance(other, dict):
            return self._data == other
        return NotImplemented

    def keys(self):
        return list(self._keys)

    def values(self):
        return [self._data[k] for k in self._keys]

    def items(self):
        return [(k, self._data[k]) for k in self._keys]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, *args):
        if key not in self._data:
            if args:
                return args[0]
            raise KeyError(key)
        value = self._data.pop(key)
        self._keys.remove(key)
        return value

    def popitem(self, last=True):
        if not self._keys:
            raise KeyError("dictionary is empty")
        if last:
            key = self._keys[-1]
        else:
            key = self._keys[0]
        value = self._data.pop(key)
        self._keys.remove(key)
        return (key, value)

    def setdefault(self, key, default=None):
        if key not in self._data:
            self[key] = default
        return self._data[key]

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

    def clear(self):
        self._keys.clear()
        self._data.clear()

    def copy(self):
        od = OrderedDict()
        for k in self._keys:
            od[k] = self._data[k]
        return od

    def move_to_end(self, key, last=True):
        if key not in self._data:
            raise KeyError(key)
        self._keys.remove(key)
        if last:
            self._keys.append(key)
        else:
            self._keys.insert(0, key)

    def __reversed__(self):
        return reversed(self._keys)


# ─── Invariant functions ───────────────────────────────────────────────────────

def collections_counter_freq():
    """Counter('aabbc')['a'] == 2"""
    c = Counter('aabbc')
    return c['a']


def collections_defaultdict_missing():
    """defaultdict(int) returns 0 for missing keys."""
    d = defaultdict(int)
    return d['missing_key']


def collections_deque_appendleft():
    """deque appendleft puts element at front; popleft returns it."""
    d = deque([1, 2, 3])
    d.appendleft(99)
    return d.popleft()