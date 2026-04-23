"""
theseus_array_cr3 - Clean-room implementation of typed array utilities.
Do NOT import the 'array' module.
"""

import struct


# Typecode metadata: (struct_format_char, item_size_bytes, is_float, is_signed)
_TYPECODE_INFO = {
    'b': ('b', 1, False, True),
    'B': ('B', 1, False, False),
    'h': ('h', 2, False, True),
    'H': ('H', 2, False, False),
    'i': ('i', 4, False, True),
    'I': ('I', 4, False, False),
    'l': ('l', 4, False, True),
    'L': ('L', 4, False, False),
    'f': ('f', 4, True, False),
    'd': ('d', 8, True, False),
}


class array:
    """
    A typed array of primitive values, similar to the standard library array.
    Supports typecodes: 'b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'f', 'd'.
    """

    def __init__(self, typecode, initializer=None):
        if typecode not in _TYPECODE_INFO:
            raise ValueError(f"bad typecode (must be b, B, h, H, i, I, l, L, f, or d): {typecode!r}")
        self.typecode = typecode
        fmt_char, item_size, is_float, is_signed = _TYPECODE_INFO[typecode]
        self._fmt_char = fmt_char
        self._item_size = item_size
        self._is_float = is_float
        self._is_signed = is_signed
        self._data = []

        if initializer is not None:
            for item in initializer:
                self._data.append(self._coerce(item))

    def _coerce(self, value):
        """Coerce a value to the appropriate Python type for this typecode."""
        if self._is_float:
            v = float(value)
            # Pack and unpack to simulate precision loss for 'f'
            packed = struct.pack(self._fmt_char, v)
            return struct.unpack(self._fmt_char, packed)[0]
        else:
            v = int(value)
            # Validate range by packing
            try:
                packed = struct.pack(self._fmt_char, v)
            except struct.error as e:
                raise OverflowError(str(e))
            return struct.unpack(self._fmt_char, packed)[0]

    def tolist(self):
        """Convert the array to a regular Python list."""
        return list(self._data)

    def index(self, value):
        """Return the index of the first occurrence of value."""
        coerced = self._coerce(value)
        for i, item in enumerate(self._data):
            if item == coerced:
                return i
        raise ValueError(f"{value!r} is not in array")

    def count(self, value):
        """Return the number of occurrences of value."""
        coerced = self._coerce(value)
        return sum(1 for item in self._data if item == coerced)

    def append(self, value):
        """Append a value to the end of the array."""
        self._data.append(self._coerce(value))

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = self._coerce(value)

    def __repr__(self):
        return f"array({self.typecode!r}, {self._data!r})"

    def __eq__(self, other):
        if isinstance(other, array):
            return self.typecode == other.typecode and self._data == other._data
        return NotImplemented


# Zero-arg invariant functions

def array3_tolist():
    """array('i', [1, 2, 3]).tolist() == [1, 2, 3]"""
    return array('i', [1, 2, 3]).tolist()


def array3_index():
    """array('i', [10, 20, 30]).index(20) == 1"""
    return array('i', [10, 20, 30]).index(20)


def array3_count():
    """array('i', [1, 2, 2, 3]).count(2) == 2"""
    return array('i', [1, 2, 2, 3]).count(2)