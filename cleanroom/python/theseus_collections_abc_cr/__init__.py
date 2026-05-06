"""Clean-room implementation of collections.abc.

Provides abstract base classes for containers, iterators, sequences, etc.
Does NOT import collections.abc — built from scratch on top of abc.ABCMeta.
"""

from abc import ABCMeta, abstractmethod


__all__ = [
    "Hashable", "Iterable", "Iterator", "Reversible", "Generator",
    "Sized", "Container", "Callable", "Collection",
    "Set", "MutableSet",
    "Mapping", "MutableMapping",
    "MappingView", "KeysView", "ItemsView", "ValuesView",
    "Sequence", "MutableSequence",
    "colabc2_sequence", "colabc2_register", "colabc2_iterator",
]


def _check_methods(C, *methods):
    """Return True iff every name in `methods` is found (and not None)
    somewhere in C's MRO. Otherwise return NotImplemented.
    """
    mro = C.__mro__
    for method in methods:
        for B in mro:
            if method in B.__dict__:
                if B.__dict__[method] is None:
                    return NotImplemented
                break
        else:
            return NotImplemented
    return True


# ---------------------------------------------------------------------------
# Hashable
# ---------------------------------------------------------------------------
class Hashable(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __hash__(self):
        return 0

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Hashable:
            return _check_methods(C, "__hash__")
        return NotImplemented


# ---------------------------------------------------------------------------
# Iterable / Iterator / Reversible / Generator
# ---------------------------------------------------------------------------
class Iterable(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __iter__(self):
        while False:
            yield None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Iterable:
            return _check_methods(C, "__iter__")
        return NotImplemented


class Iterator(Iterable):
    __slots__ = ()

    @abstractmethod
    def __next__(self):
        raise StopIteration

    def __iter__(self):
        return self

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Iterator:
            return _check_methods(C, "__iter__", "__next__")
        return NotImplemented


class Reversible(Iterable):
    __slots__ = ()

    @abstractmethod
    def __reversed__(self):
        while False:
            yield None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Reversible:
            return _check_methods(C, "__reversed__", "__iter__")
        return NotImplemented


class Generator(Iterator):
    __slots__ = ()

    def __next__(self):
        return self.send(None)

    @abstractmethod
    def send(self, value):
        raise StopIteration

    @abstractmethod
    def throw(self, typ, val=None, tb=None):
        if val is None:
            if tb is None:
                raise typ
            val = typ()
        if tb is not None:
            val = val.with_traceback(tb)
        raise val

    def close(self):
        try:
            self.throw(GeneratorExit)
        except (GeneratorExit, StopIteration):
            pass
        else:
            raise RuntimeError("generator ignored GeneratorExit")

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Generator:
            return _check_methods(C, "__iter__", "__next__", "send", "throw", "close")
        return NotImplemented


# ---------------------------------------------------------------------------
# Sized / Container / Callable / Collection
# ---------------------------------------------------------------------------
class Sized(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __len__(self):
        return 0

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Sized:
            return _check_methods(C, "__len__")
        return NotImplemented


class Container(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __contains__(self, x):
        return False

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Container:
            return _check_methods(C, "__contains__")
        return NotImplemented


class Callable(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __call__(self, *args, **kwds):
        return False

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Callable:
            return _check_methods(C, "__call__")
        return NotImplemented


class Collection(Sized, Iterable, Container):
    __slots__ = ()

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Collection:
            return _check_methods(C, "__len__", "__iter__", "__contains__")
        return NotImplemented


# ---------------------------------------------------------------------------
# Set / MutableSet
# ---------------------------------------------------------------------------
class Set(Collection):
    __slots__ = ()

    @abstractmethod
    def __contains__(self, x):
        return False

    def __le__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        if len(self) > len(other):
            return False
        for elem in self:
            if elem not in other:
                return False
        return True

    def __lt__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        return len(self) < len(other) and self.__le__(other)

    def __gt__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        return len(self) > len(other) and self.__ge__(other)

    def __ge__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        if len(self) < len(other):
            return False
        for elem in other:
            if elem not in self:
                return False
        return True

    def __eq__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        return len(self) == len(other) and self.__le__(other)

    @classmethod
    def _from_iterable(cls, it):
        return cls(it)

    def __and__(self, other):
        if not isinstance(other, Iterable):
            return NotImplemented
        return self._from_iterable(value for value in other if value in self)

    __rand__ = __and__

    def isdisjoint(self, other):
        for value in other:
            if value in self:
                return False
        return True

    def __or__(self, other):
        if not isinstance(other, Iterable):
            return NotImplemented
        chain = (e for s in (self, other) for e in s)
        return self._from_iterable(chain)

    __ror__ = __or__

    def __sub__(self, other):
        if not isinstance(other, Set):
            if not isinstance(other, Iterable):
                return NotImplemented
            other = self._from_iterable(other)
        return self._from_iterable(value for value in self if value not in other)

    def __rsub__(self, other):
        if not isinstance(other, Set):
            if not isinstance(other, Iterable):
                return NotImplemented
            other = self._from_iterable(other)
        return self._from_iterable(value for value in other if value not in self)

    def __xor__(self, other):
        if not isinstance(other, Set):
            if not isinstance(other, Iterable):
                return NotImplemented
            other = self._from_iterable(other)
        return (self - other) | (other - self)

    __rxor__ = __xor__


class MutableSet(Set):
    __slots__ = ()

    @abstractmethod
    def add(self, value):
        raise NotImplementedError

    @abstractmethod
    def discard(self, value):
        raise NotImplementedError

    def remove(self, value):
        if value not in self:
            raise KeyError(value)
        self.discard(value)

    def pop(self):
        it = iter(self)
        try:
            value = next(it)
        except StopIteration:
            raise KeyError from None
        self.discard(value)
        return value

    def clear(self):
        try:
            while True:
                self.pop()
        except KeyError:
            pass

    def __ior__(self, it):
        for value in it:
            self.add(value)
        return self

    def __iand__(self, it):
        for value in (self - it):
            self.discard(value)
        return self

    def __ixor__(self, it):
        if it is self:
            self.clear()
        else:
            if not isinstance(it, Set):
                it = self._from_iterable(it)
            for value in it:
                if value in self:
                    self.discard(value)
                else:
                    self.add(value)
        return self

    def __isub__(self, it):
        if it is self:
            self.clear()
        else:
            for value in it:
                self.discard(value)
        return self


# ---------------------------------------------------------------------------
# Mapping / MutableMapping / Views
# ---------------------------------------------------------------------------
class Mapping(Collection):
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, key):
        raise KeyError

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    def keys(self):
        return KeysView(self)

    def items(self):
        return ItemsView(self)

    def values(self):
        return ValuesView(self)

    def __eq__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        return dict(self) == dict(other)

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq


class MappingView(Sized):
    __slots__ = ("_mapping",)

    def __init__(self, mapping):
        self._mapping = mapping

    def __len__(self):
        return len(self._mapping)

    def __repr__(self):
        return "{0.__class__.__name__}({0._mapping!r})".format(self)


class KeysView(MappingView, Set):
    __slots__ = ()

    @classmethod
    def _from_iterable(cls, it):
        return set(it)

    def __contains__(self, key):
        return key in self._mapping

    def __iter__(self):
        yield from self._mapping


class ItemsView(MappingView, Set):
    __slots__ = ()

    @classmethod
    def _from_iterable(cls, it):
        return set(it)

    def __contains__(self, item):
        key, value = item
        try:
            v = self._mapping[key]
        except KeyError:
            return False
        return v is value or v == value

    def __iter__(self):
        for key in self._mapping:
            yield (key, self._mapping[key])


class ValuesView(MappingView, Collection):
    __slots__ = ()

    def __contains__(self, value):
        for key in self._mapping:
            v = self._mapping[key]
            if v is value or v == value:
                return True
        return False

    def __iter__(self):
        for key in self._mapping:
            yield self._mapping[key]


class MutableMapping(Mapping):
    __slots__ = ()

    @abstractmethod
    def __setitem__(self, key, value):
        raise KeyError

    @abstractmethod
    def __delitem__(self, key):
        raise KeyError

    __marker = object()

    def pop(self, key, default=__marker):
        try:
            value = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return value

    def popitem(self):
        try:
            key = next(iter(self))
        except StopIteration:
            raise KeyError from None
        value = self[key]
        del self[key]
        return key, value

    def clear(self):
        try:
            while True:
                self.popitem()
        except KeyError:
            pass

    def update(self, other=(), /, **kwds):
        if isinstance(other, Mapping):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, "keys"):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return default


# ---------------------------------------------------------------------------
# Sequence / MutableSequence
# ---------------------------------------------------------------------------
class Sequence(Reversible, Collection):
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, index):
        raise IndexError

    def __iter__(self):
        i = 0
        try:
            while True:
                v = self[i]
                yield v
                i += 1
        except IndexError:
            return

    def __contains__(self, value):
        for v in self:
            if v is value or v == value:
                return True
        return False

    def __reversed__(self):
        for i in reversed(range(len(self))):
            yield self[i]

    def index(self, value, start=0, stop=None):
        if start is not None and start < 0:
            start = max(len(self) + start, 0)
        if stop is not None and stop < 0:
            stop += len(self)
        i = start
        while stop is None or i < stop:
            try:
                v = self[i]
            except IndexError:
                break
            if v is value or v == value:
                return i
            i += 1
        raise ValueError

    def count(self, value):
        return sum(1 for v in self if v is value or v == value)


class MutableSequence(Sequence):
    __slots__ = ()

    @abstractmethod
    def __setitem__(self, index, value):
        raise IndexError

    @abstractmethod
    def __delitem__(self, index):
        raise IndexError

    @abstractmethod
    def insert(self, index, value):
        raise IndexError

    def append(self, value):
        self.insert(len(self), value)

    def clear(self):
        try:
            while True:
                self.pop()
        except IndexError:
            pass

    def reverse(self):
        n = len(self)
        for i in range(n // 2):
            self[i], self[n - i - 1] = self[n - i - 1], self[i]

    def extend(self, values):
        if values is self:
            values = list(values)
        for v in values:
            self.append(v)

    def pop(self, index=-1):
        v = self[index]
        del self[index]
        return v

    def remove(self, value):
        del self[self.index(value)]

    def __iadd__(self, values):
        self.extend(values)
        return self


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------
def colabc2_sequence():
    """Verify that Sequence ABC machinery works end-to-end."""

    class MySeq(Sequence):
        def __init__(self, data):
            self._data = list(data)

        def __getitem__(self, i):
            return self._data[i]

        def __len__(self):
            return len(self._data)

    s = MySeq([10, 20, 30, 20])

    if not isinstance(s, Sequence):
        return False
    if not isinstance(s, Iterable):
        return False
    if not isinstance(s, Container):
        return False
    if not isinstance(s, Sized):
        return False
    if not isinstance(s, Reversible):
        return False
    if len(s) != 4:
        return False
    if list(s) != [10, 20, 30, 20]:
        return False
    if 20 not in s:
        return False
    if 99 in s:
        return False
    if s.index(20) != 1:
        return False
    if s.count(20) != 2:
        return False
    if list(reversed(s)) != [20, 30, 20, 10]:
        return False
    # Cannot instantiate without overriding abstract method
    try:
        class Bad(Sequence):
            pass
        Bad()
        return False
    except TypeError:
        pass
    return True


def colabc2_register():
    """Verify that ABC.register() creates virtual subclasses."""

    class Foo:
        pass

    # Foo isn't iterable yet
    if isinstance(Foo(), Iterable):
        return False

    Iterable.register(Foo)

    if not isinstance(Foo(), Iterable):
        return False
    if not issubclass(Foo, Iterable):
        return False

    # register with another ABC
    class Bar:
        pass

    Sized.register(Bar)
    if not issubclass(Bar, Sized):
        return False

    # register should return the class
    class Baz:
        pass
    result = Container.register(Baz)
    if result is not Baz:
        return False

    return True


def colabc2_iterator():
    """Verify that Iterator ABC works for both real and duck-typed iterators."""

    class Counter:
        def __init__(self, n):
            self._n = n
            self._i = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self._i >= self._n:
                raise StopIteration
            self._i += 1
            return self._i

    c = Counter(3)
    # Iterator's __subclasshook__ should detect duck-typed iterators
    if not isinstance(c, Iterator):
        return False
    if not isinstance(c, Iterable):
        return False
    if list(c) != [1, 2, 3]:
        return False

    # Now via subclassing
    class MyIter(Iterator):
        def __init__(self, vals):
            self._vals = list(vals)
            self._idx = 0

        def __next__(self):
            if self._idx >= len(self._vals):
                raise StopIteration
            v = self._vals[self._idx]
            self._idx += 1
            return v

    m = MyIter(["a", "b", "c"])
    if not isinstance(m, Iterator):
        return False
    if iter(m) is not m:
        return False
    if list(m) != ["a", "b", "c"]:
        return False

    # An object missing __next__ should not be an Iterator
    class NotIter:
        def __iter__(self):
            return iter([])

    if isinstance(NotIter(), Iterator):
        return False

    return True