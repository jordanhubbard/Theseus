"""
theseus_array_cr2 - Clean-room implementation of typed array sequences.
Do NOT import the original 'array' module.
"""

import struct

typecodes = 'bBifdу'  # supported typecodes (u for unicode, deprecated)

# Mapping from typecode to struct format character and item size
_TYPECODE_INFO = {
    'b': ('b', 1),   # signed byte
    'B': ('B', 1),   # unsigned byte
    'i': ('i', 4),   # signed int
    'f': ('f', 4),   # float
    'd': ('d', 8),   # double
    'u': ('u', 4),   # unicode char (deprecated) - stored as uint32
}

# Override 'u' since struct doesn't support 'u'
_UNICODE_TYPECODE = 'u'


class array:
    """
    A typed sequence of values, similar to the built-in array module.
    
    Supported typecodes:
        'b' - signed byte (1 byte)
        'B' - unsigned byte (1 byte)
        'i' - signed int (4 bytes)
        'f' - float (4 bytes)
        'd' - double (8 bytes)
        'u' - unicode char, deprecated (4 bytes, stored as code point)
    """

    def __init__(self, typecode, initializer=None):
        if initializer is None:
            initializer = []
        
        if typecode not in _TYPECODE_INFO and typecode != _UNICODE_TYPECODE:
            raise ValueError(f"bad typecode (must be b, B, i, f, d or u): {typecode!r}")
        
        self.typecode = typecode
        self._data = []
        
        if typecode == _UNICODE_TYPECODE:
            self._fmt = None
            self._itemsize = 4
        else:
            fmt_char, itemsize = _TYPECODE_INFO[typecode]
            self._fmt = fmt_char
            self._itemsize = itemsize
        
        # Initialize from initializer
        if isinstance(initializer, (bytes, bytearray)):
            self.frombytes(initializer)
        elif isinstance(initializer, str) and typecode == 'u':
            for ch in initializer:
                self._data.append(ord(ch))
        else:
            for item in initializer:
                self.append(item)

    def _validate_and_convert(self, x):
        """Validate and convert a value for storage."""
        tc = self.typecode
        if tc == 'b':
            x = int(x)
            if not (-128 <= x <= 127):
                raise OverflowError(f"signed byte value out of range: {x}")
            return x
        elif tc == 'B':
            x = int(x)
            if not (0 <= x <= 255):
                raise OverflowError(f"unsigned byte value out of range: {x}")
            return x
        elif tc == 'i':
            x = int(x)
            if not (-2147483648 <= x <= 2147483647):
                raise OverflowError(f"signed int value out of range: {x}")
            return x
        elif tc == 'f':
            return float(x)
        elif tc == 'd':
            return float(x)
        elif tc == 'u':
            if isinstance(x, str) and len(x) == 1:
                return ord(x)
            elif isinstance(x, int):
                return x
            else:
                raise TypeError(f"array item must be unicode character, not {type(x).__name__}")
        else:
            raise ValueError(f"unknown typecode: {tc!r}")

    def append(self, x):
        """Add element x to the end of the array."""
        val = self._validate_and_convert(x)
        self._data.append(val)

    def extend(self, iterable):
        """Extend the array by appending all elements from the iterable."""
        for item in iterable:
            self.append(item)

    def tobytes(self):
        """Return the array as a bytes object."""
        tc = self.typecode
        if tc == 'u':
            # Store unicode as 4-byte little-endian code points
            result = bytearray()
            for cp in self._data:
                result += struct.pack('<I', cp)
            return bytes(result)
        else:
            fmt_char = self._fmt
            result = bytearray()
            for val in self._data:
                result += struct.pack(fmt_char, val)
            return bytes(result)

    def frombytes(self, b):
        """
        Append items from the bytes object b.
        The bytes must be a multiple of the item size.
        """
        if not isinstance(b, (bytes, bytearray)):
            raise TypeError(f"a bytes-like object is required, not {type(b).__name__}")
        
        tc = self.typecode
        itemsize = self._itemsize
        
        if len(b) % itemsize != 0:
            raise ValueError(
                f"bytes length not a multiple of item size ({itemsize})"
            )
        
        n = len(b) // itemsize
        
        if tc == 'u':
            for i in range(n):
                chunk = b[i * itemsize:(i + 1) * itemsize]
                cp = struct.unpack('<I', chunk)[0]
                self._data.append(cp)
        else:
            fmt_char = self._fmt
            for i in range(n):
                chunk = b[i * itemsize:(i + 1) * itemsize]
                val = struct.unpack(fmt_char, chunk)[0]
                self._data.append(val)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index):
        if isinstance(index, slice):
            new_arr = array(self.typecode)
            items = self._data[index]
            new_arr._data = list(items)
            return new_arr
        else:
            if index < 0:
                index += len(self._data)
            if not (0 <= index < len(self._data)):
                raise IndexError("array index out of range")
            val = self._data[index]
            if self.typecode == 'u':
                return chr(val)
            return val

    def __setitem__(self, index, value):
        if index < 0:
            index += len(self._data)
        if not (0 <= index < len(self._data)):
            raise IndexError("array assignment index out of range")
        self._data[index] = self._validate_and_convert(value)

    def __delitem__(self, index):
        if index < 0:
            index += len(self._data)
        if not (0 <= index < len(self._data)):
            raise IndexError("array assignment index out of range")
        del self._data[index]

    def __iter__(self):
        tc = self.typecode
        if tc == 'u':
            for cp in self._data:
                yield chr(cp)
        else:
            yield from self._data

    def __repr__(self):
        tc = self.typecode
        if tc == 'u':
            items = ''.join(chr(cp) for cp in self._data)
            return f"array({tc!r}, {items!r})"
        else:
            return f"array({tc!r}, {list(self._data)!r})"

    def __eq__(self, other):
        if isinstance(other, array):
            return self.typecode == other.typecode and self._data == other._data
        return NotImplemented

    @property
    def itemsize(self):
        return self._itemsize

    def tolist(self):
        """Convert array to a regular Python list."""
        if self.typecode == 'u':
            return [chr(cp) for cp in self._data]
        return list(self._data)

    def insert(self, i, x):
        """Insert a new item with value x before position i."""
        val = self._validate_and_convert(x)
        self._data.insert(i, val)

    def pop(self, i=-1):
        """Remove and return item at index i (default last)."""
        if not self._data:
            raise IndexError("pop from empty array")
        val = self._data.pop(i)
        if self.typecode == 'u':
            return chr(val)
        return val

    def remove(self, x):
        """Remove first occurrence of x."""
        val = self._validate_and_convert(x)
        try:
            self._data.remove(val)
        except ValueError:
            raise ValueError("array.remove(x): x not in array")

    def index(self, x):
        """Return index of first occurrence of x."""
        val = self._validate_and_convert(x)
        try:
            return self._data.index(val)
        except ValueError:
            raise ValueError(f"{x!r} is not in array")

    def count(self, x):
        """Return number of occurrences of x."""
        val = self._validate_and_convert(x)
        return self._data.count(val)

    def reverse(self):
        """Reverse the order of items in the array."""
        self._data.reverse()

    def buffer_info(self):
        """Return a tuple (address, length) giving the memory address and length."""
        # We can't really give a memory address in pure Python, return 0
        return (0, len(self._data))


# ─── Invariant test functions ────────────────────────────────────────────────

def array2_append():
    """a=array('i',[1,2]); a.append(3); a[2] == 3 → returns 3"""
    a = array('i', [1, 2])
    a.append(3)
    return a[2]


def array2_tobytes():
    """array('B',[1,2,3]).tobytes() == b'\\x01\\x02\\x03' → returns True"""
    return array('B', [1, 2, 3]).tobytes() == b'\x01\x02\x03'


def array2_frombytes():
    """a=array('B',[]); a.frombytes(b'\\x01\\x02'); len(a) == 2 → returns 2"""
    a = array('B', [])
    a.frombytes(b'\x01\x02')
    return len(a)