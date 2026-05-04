"""Clean-room collections subset for Theseus invariants."""


def namedtuple(typename, field_names, **kwargs):
    fields = field_names.replace(",", " ").split() if isinstance(field_names, str) else list(field_names)

    class _Tuple(tuple):
        __slots__ = ()
        _fields = tuple(fields)

        def __new__(cls, *values):
            return tuple.__new__(cls, values)

        def __getattr__(self, name):
            if name in self._fields:
                return self[self._fields.index(name)]
            raise AttributeError(name)

    _Tuple.__name__ = typename
    return _Tuple


class deque:
    def __init__(self, iterable=(), maxlen=None):
        self._data = list(iterable)
        self.maxlen = maxlen

    def append(self, value):
        self._data.append(value)
        if self.maxlen is not None and len(self._data) > self.maxlen:
            self._data.pop(0)

    def appendleft(self, value):
        self._data.insert(0, value)
        if self.maxlen is not None and len(self._data) > self.maxlen:
            self._data.pop()

    def pop(self):
        return self._data.pop()

    def popleft(self):
        return self._data.pop(0)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


class Counter(dict):
    def __init__(self, iterable=None, **kwds):
        super().__init__()
        if iterable is not None:
            self.update(iterable)
        if kwds:
            self.update(kwds)

    def __missing__(self, key):
        return 0

    def update(self, iterable=None, **kwds):
        if iterable is None:
            pass
        elif hasattr(iterable, "items"):
            for key, value in iterable.items():
                self[key] = self[key] + value
        else:
            for key in iterable:
                self[key] = self[key] + 1
        for key, value in kwds.items():
            self[key] = self[key] + value


class defaultdict(dict):
    def __init__(self, default_factory=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_factory = default_factory

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value


class OrderedDict(dict):
    pass


class ChainMap:
    def __init__(self, *maps):
        self.maps = list(maps) or [{}]


class UserDict:
    def __init__(self, dict=None, **kwargs):
        self.data = {}
        if dict:
            self.data.update(dict)
        self.data.update(kwargs)


class UserList(list):
    pass


class UserString(str):
    pass


def collections2_counter():
    c = Counter("aabbbcccc")
    return c["a"] == 2 and c["b"] == 3 and c["c"] == 4


def collections2_defaultdict():
    d = defaultdict(int)
    d["x"] += 1
    d["x"] += 1
    return d["x"] == 2 and d["y"] == 0


def collections2_deque():
    dq = deque([1, 2, 3])
    dq.appendleft(0)
    dq.append(4)
    return list(dq) == [0, 1, 2, 3, 4]


__all__ = [
    "namedtuple", "deque", "Counter", "defaultdict", "OrderedDict",
    "ChainMap", "UserDict", "UserList", "UserString",
    "collections2_counter", "collections2_defaultdict", "collections2_deque",
]
