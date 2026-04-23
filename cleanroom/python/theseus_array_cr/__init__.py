"""
theseus_array_cr — Clean-room array module.
No import of the standard `array` module.
"""

import struct as _struct

_TYPECODES = {
    'b': ('b', 1),
    'B': ('B', 1),
    'h': ('h', 2),
    'H': ('H', 2),
    'i': ('i', 4),
    'I': ('I', 4),
    'l': ('l', 4),
    'L': ('L', 4),
    'q': ('q', 8),
    'Q': ('Q', 8),
    'f': ('f', 4),
    'd': ('d', 8),
}

typecodes = 'bBhHiIlLqQfd'


class array:
    def __init__(self, typecode, initializer=()):
        if typecode not in _TYPECODES:
            raise ValueError(f"bad typecode")
        self._typecode = typecode
        fmt, self._itemsize = _TYPECODES[typecode]
        self._fmt = fmt
        self._data = list(initializer)

    @property
    def typecode(self):
        return self._typecode

    @property
    def itemsize(self):
        return self._itemsize

    def append(self, x):
        self._data.append(x)

    def extend(self, iterable):
        for x in iterable:
            self._data.append(x)

    def insert(self, i, x):
        self._data.insert(i, x)

    def pop(self, i=-1):
        return self._data.pop(i)

    def remove(self, x):
        self._data.remove(x)

    def index(self, x):
        return self._data.index(x)

    def reverse(self):
        self._data.reverse()

    def count(self, x):
        return self._data.count(x)

    def tolist(self):
        return list(self._data)

    def fromlist(self, lst):
        self._data.extend(lst)

    def tobytes(self):
        if not self._data:
            return b''
        return _struct.pack(f'<{len(self._data)}{self._fmt}', *self._data)

    def frombytes(self, buf):
        n = len(buf) // self._itemsize
        vals = _struct.unpack(f'<{n}{self._fmt}', buf[:n * self._itemsize])
        self._data.extend(vals)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def __setitem__(self, idx, val):
        self._data[idx] = val

    def __delitem__(self, idx):
        del self._data[idx]

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return f"array({self._typecode!r}, {self._data!r})"

    def __eq__(self, other):
        if isinstance(other, array):
            return self._typecode == other._typecode and self._data == other._data
        return NotImplemented


def array2_typecode():
    return array('i', [1, 2, 3]).typecode


def array2_append():
    a = array('i', [1, 2, 3])
    a.append(4)
    return len(a)


def array2_tolist():
    a = array('d', [1.5, 2.5, 3.5])
    return a.tolist() == [1.5, 2.5, 3.5]


__all__ = [
    'array', 'typecodes',
    'array2_typecode', 'array2_append', 'array2_tolist',
]
