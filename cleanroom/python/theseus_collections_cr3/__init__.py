# theseus_collections_cr3 - Clean-room implementation of extended collections
# No import of 'collections' or any third-party library allowed.


class ChainMap:
    """
    A ChainMap groups multiple dicts (or other mappings) together to create
    a single, updateable view. Lookups search the underlying mappings in order
    until a key is found.
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

    def __setitem__(self, key, value):
        self.maps[0][key] = value

    def __delitem__(self, key):
        try:
            del self.maps[0][key]
        except KeyError:
            raise KeyError(f'Key not found in the first mapping: {key!r}')

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

    def __repr__(self):
        return f'{self.__class__.__name__}({", ".join(map(repr, self.maps))})'

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return list(self)

    def values(self):
        return [self[k] for k in self]

    def items(self):
        return [(k, self[k]) for k in self]

    def new_child(self, m=None):
        if m is None:
            m = {}
        return self.__class__(m, *self.maps)

    @property
    def parents(self):
        return self.__class__(*self.maps[1:])

    def copy(self):
        return self.__class__(self.maps[0].copy(), *self.maps[1:])

    __copy__ = copy

    def __eq__(self, other):
        if isinstance(other, ChainMap):
            return dict(self.items()) == dict(other.items())
        return NotImplemented


class UserDict:
    """
    A wrapper around dict providing the full dict interface.
    Subclasses can override methods to customize behavior.
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

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        if hasattr(self.__class__, '__missing__'):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)

    def __setitem__(self, key, item):
        self.data[key] = item

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __contains__(self, key):
        return key in self.data

    def __repr__(self):
        return repr(self.data)

    def __eq__(self, other):
        if isinstance(other, UserDict):
            return self.data == other.data
        return self.data == other

    def __or__(self, other):
        if isinstance(other, UserDict):
            new = self.copy()
            new.update(other.data)
            return new
        if isinstance(other, dict):
            new = self.copy()
            new.update(other)
            return new
        return NotImplemented

    def __ior__(self, other):
        if isinstance(other, UserDict):
            self.data.update(other.data)
        else:
            self.data.update(other)
        return self

    def get(self, key, default=None):
        return self.data.get(key, default)

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def pop(self, key, *args):
        return self.data.pop(key, *args)

    def popitem(self):
        return self.data.popitem()

    def clear(self):
        self.data.clear()

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

    def update(self, other=None, **kwargs):
        if other is not None:
            if isinstance(other, UserDict):
                self.data.update(other.data)
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for key, value in other:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d


class UserList:
    """
    A wrapper around list providing the full list interface.
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

    def __lt__(self, other):
        return self.data < self.__cast(other)

    def __le__(self, other):
        return self.data <= self.__cast(other)

    def __eq__(self, other):
        return self.data == self.__cast(other)

    def __gt__(self, other):
        return self.data > self.__cast(other)

    def __ge__(self, other):
        return self.data >= self.__cast(other)

    def __cast(self, other):
        return other.data if isinstance(other, UserList) else other

    def __contains__(self, item):
        return item in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return self.__class__(self.data[i])
        return self.data[i]

    def __setitem__(self, i, item):
        self.data[i] = item

    def __delitem__(self, i):
        del self.data[i]

    def __add__(self, other):
        if isinstance(other, UserList):
            return self.__class__(self.data + other.data)
        elif isinstance(other, list):
            return self.__class__(self.data + other)
        return self.__class__(self.data + list(other))

    def __radd__(self, other):
        if isinstance(other, UserList):
            return self.__class__(other.data + self.data)
        elif isinstance(other, list):
            return self.__class__(other + self.data)
        return self.__class__(list(other) + self.data)

    def __iadd__(self, other):
        if isinstance(other, UserList):
            self.data += other.data
        elif isinstance(other, list):
            self.data += other
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

    def __reversed__(self):
        return reversed(self.data)

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


class UserString:
    """
    A wrapper around str providing the full str interface.
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

    def __int__(self):
        return int(self.data)

    def __float__(self):
        return float(self.data)

    def __complex__(self):
        return complex(self.data)

    def __hash__(self):
        return hash(self.data)

    def __bool__(self):
        return bool(self.data)

    def __eq__(self, other):
        if isinstance(other, UserString):
            return self.data == other.data
        return self.data == other

    def __lt__(self, other):
        if isinstance(other, UserString):
            return self.data < other.data
        return self.data < other

    def __le__(self, other):
        if isinstance(other, UserString):
            return self.data <= other.data
        return self.data <= other

    def __gt__(self, other):
        if isinstance(other, UserString):
            return self.data > other.data
        return self.data > other

    def __ge__(self, other):
        if isinstance(other, UserString):
            return self.data >= other.data
        return self.data >= other

    def __contains__(self, char):
        if isinstance(char, UserString):
            char = char.data
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

    def __mod__(self, args):
        return self.__class__(self.data % args)

    def __rmod__(self, template):
        return self.__class__(template % self.data)

    def __iter__(self):
        return iter(self.data)

    def capitalize(self):
        return self.__class__(self.data.capitalize())

    def casefold(self):
        return self.__class__(self.data.casefold())

    def center(self, width, *args):
        return self.__class__(self.data.center(width, *args))

    def count(self, sub, *args):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.count(sub, *args)

    def encode(self, encoding='utf-8', errors='strict'):
        return self.data.encode(encoding, errors)

    def endswith(self, suffix, *args):
        if isinstance(suffix, UserString):
            suffix = suffix.data
        return self.data.endswith(suffix, *args)

    def expandtabs(self, tabsize=8):
        return self.__class__(self.data.expandtabs(tabsize))

    def find(self, sub, *args):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.find(sub, *args)

    def format(self, /, *args, **kwargs):
        return self.__class__(self.data.format(*args, **kwargs))

    def format_map(self, mapping):
        return self.__class__(self.data.format_map(mapping))

    def index(self, sub, *args):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.index(sub, *args)

    def isalpha(self):
        return self.data.isalpha()

    def isalnum(self):
        return self.data.isalnum()

    def isascii(self):
        return self.data.isascii()

    def isdecimal(self):
        return self.data.isdecimal()

    def isdigit(self):
        return self.data.isdigit()

    def isidentifier(self):
        return self.data.isidentifier()

    def islower(self):
        return self.data.islower()

    def isnumeric(self):
        return self.data.isnumeric()

    def isprintable(self):
        return self.data.isprintable()

    def isspace(self):
        return self.data.isspace()

    def istitle(self):
        return self.data.istitle()

    def isupper(self):
        return self.data.isupper()

    def join(self, iterable):
        return self.__class__(self.data.join(iterable))

    def ljust(self, width, *args):
        return self.__class__(self.data.ljust(width, *args))

    def lower(self):
        return self.__class__(self.data.lower())

    def lstrip(self, chars=None):
        if isinstance(chars, UserString):
            chars = chars.data
        return self.__class__(self.data.lstrip(chars))

    def maketrans(self, *args):
        return self.data.maketrans(*args)

    def partition(self, sep):
        if isinstance(sep, UserString):
            sep = sep.data
        return self.data.partition(sep)

    def removeprefix(self, prefix):
        if isinstance(prefix, UserString):
            prefix = prefix.data
        return self.__class__(self.data.removeprefix(prefix))

    def removesuffix(self, suffix):
        if isinstance(suffix, UserString):
            suffix = suffix.data
        return self.__class__(self.data.removesuffix(suffix))

    def replace(self, old, new, *args):
        if isinstance(old, UserString):
            old = old.data
        if isinstance(new, UserString):
            new = new.data
        return self.__class__(self.data.replace(old, new, *args))

    def rfind(self, sub, *args):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.rfind(sub, *args)

    def rindex(self, sub, *args):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.rindex(sub, *args)

    def rjust(self, width, *args):
        return self.__class__(self.data.rjust(width, *args))

    def rpartition(self, sep):
        if isinstance(sep, UserString):
            sep = sep.data
        return self.data.rpartition(sep)

    def rsplit(self, sep=None, maxsplit=-1):
        if isinstance(sep, UserString):
            sep = sep.data
        return self.data.rsplit(sep, maxsplit)

    def rstrip(self, chars=None):
        if isinstance(chars, UserString):
            chars = chars.data
        return self.__class__(self.data.rstrip(chars))

    def split(self, sep=None, maxsplit=-1):
        if isinstance(sep, UserString):
            sep = sep.data
        return self.data.split(sep, maxsplit)

    def splitlines(self, keepends=False):
        return self.data.splitlines(keepends)

    def startswith(self, prefix, *args):
        if isinstance(prefix, UserString):
            prefix = prefix.data
        return self.data.startswith(prefix, *args)

    def strip(self, chars=None):
        if isinstance(chars, UserString):
            chars = chars.data
        return self.__class__(self.data.strip(chars))

    def swapcase(self):
        return self.__class__(self.data.swapcase())

    def title(self):
        return self.__class__(self.data.title())

    def translate(self, *args):
        return self.__class__(self.data.translate(*args))

    def upper(self):
        return self.__class__(self.data.upper())

    def zfill(self, width):
        return self.__class__(self.data.zfill(width))


# --- Invariant functions ---

def collections3_chainmap():
    """ChainMap({'a':1},{'b':2})['b'] == 2"""
    return ChainMap({'a': 1}, {'b': 2})['b']


def collections3_chainmap_precedence():
    """ChainMap({'x':1},{'x':2})['x'] == 1 (first map wins)"""
    return ChainMap({'x': 1}, {'x': 2})['x']


def collections3_userdict():
    """d=UserDict({'k':42}); d['k'] == 42"""
    d = UserDict({'k': 42})
    return d['k']