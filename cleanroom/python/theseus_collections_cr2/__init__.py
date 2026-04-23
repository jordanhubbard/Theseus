# theseus_collections_cr2 - Clean-room implementation of extended collections
# No import of 'collections' allowed.


class UserDict:
    """A mutable mapping that wraps a dict, easy to subclass."""

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

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __contains__(self, key):
        return key in self.data

    def __repr__(self):
        return f'{self.__class__.__name__}({self.data!r})'

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
        if kwargs:
            self.data.update(kwargs)

    def setdefault(self, key, default=None):
        return self.data.setdefault(key, default)

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

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d


class UserList:
    """A mutable sequence that wraps a list, easy to subclass."""

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
        return f'{self.__class__.__name__}({self.data!r})'

    def __lt__(self, other):
        return self.data < (other.data if isinstance(other, UserList) else other)

    def __le__(self, other):
        return self.data <= (other.data if isinstance(other, UserList) else other)

    def __eq__(self, other):
        return self.data == (other.data if isinstance(other, UserList) else other)

    def __gt__(self, other):
        return self.data > (other.data if isinstance(other, UserList) else other)

    def __ge__(self, other):
        return self.data >= (other.data if isinstance(other, UserList) else other)

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
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, list):
            return self.__class__(other + self.data)
        return NotImplemented

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

    def __imul__(self, n):
        self.data *= n
        return self

    def __rmul__(self, n):
        return self.__class__(self.data * n)

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
    """A mutable string wrapper."""

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
        return f'{self.__class__.__name__}({self.data!r})'

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
        elif isinstance(other, str):
            return self.__class__(self.data + other)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str):
            return self.__class__(other + self.data)
        return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, UserString):
            self.data += other.data
        elif isinstance(other, str):
            self.data += other
        else:
            self.data += str(other)
        return self

    def __mul__(self, n):
        return self.__class__(self.data * n)

    def __rmul__(self, n):
        return self.__class__(self.data * n)

    def __imul__(self, n):
        self.data *= n
        return self

    def __iter__(self):
        return iter(self.data)

    def __mod__(self, args):
        return self.__class__(self.data % args)

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

    def join(self, seq):
        return self.__class__(self.data.join(seq))

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

    def rstrip(self, chars=None):
        if isinstance(chars, UserString):
            chars = chars.data
        return self.__class__(self.data.rstrip(chars))

    def split(self, sep=None, maxsplit=-1):
        if isinstance(sep, UserString):
            sep = sep.data
        return self.data.split(sep, maxsplit)

    def rsplit(self, sep=None, maxsplit=-1):
        if isinstance(sep, UserString):
            sep = sep.data
        return self.data.rsplit(sep, maxsplit)

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


class ChainMap:
    """Multiple dict views as a single logical mapping."""

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
            raise KeyError(f'Key not found in the first mapping: {key!r}')

    def __iter__(self):
        seen = set()
        for mapping in self.maps:
            for key in mapping:
                if key not in seen:
                    seen.add(key)
                    yield key

    def __len__(self):
        return len(set().union(*self.maps))

    def __contains__(self, key):
        return any(key in m for m in self.maps)

    def __bool__(self):
        return any(self.maps)

    def __repr__(self):
        return f'{self.__class__.__name__}({", ".join(map(repr, self.maps))})'

    def __eq__(self, other):
        if isinstance(other, ChainMap):
            return dict(self) == dict(other)
        return dict(self) == other

    def keys(self):
        return list(self.__iter__())

    def values(self):
        return [self[key] for key in self]

    def items(self):
        return [(key, self[key]) for key in self]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, *args):
        try:
            return self.maps[0].pop(key)
        except KeyError:
            if args:
                return args[0]
            raise

    def popitem(self):
        try:
            return self.maps[0].popitem()
        except KeyError:
            raise KeyError('No keys found in the first mapping.')

    def clear(self):
        self.maps[0].clear()

    def update(self, other=None, **kwargs):
        if other is not None:
            if hasattr(other, 'items'):
                for key, value in other.items():
                    self.maps[0][key] = value
            else:
                for key, value in other:
                    self.maps[0][key] = value
        for key, value in kwargs.items():
            self.maps[0][key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def new_child(self, m=None, **kwargs):
        if m is None:
            m = {}
        m.update(kwargs)
        return self.__class__(m, *self.maps)

    @property
    def parents(self):
        return self.__class__(*self.maps[1:])

    def copy(self):
        return self.__class__(self.maps[0].copy(), *self.maps[1:])

    def __copy__(self):
        return self.copy()

    def fromkeys(self, iterable, value=None):
        d = {}
        for key in iterable:
            d[key] = value
        return self.__class__(d)


# --- Invariant test functions ---

def collections2_userdict():
    """UserDict({'a':1})['a'] == 1"""
    return UserDict({'a': 1})['a']


def collections2_chainmap():
    """ChainMap({'a':1}, {'b':2})['b'] == 2"""
    return ChainMap({'a': 1}, {'b': 2})['b']


def collections2_userlist():
    """UserList([1,2,3])[0] == 1"""
    return UserList([1, 2, 3])[0]