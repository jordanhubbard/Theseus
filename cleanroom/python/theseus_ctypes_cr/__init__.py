"""Clean-room ctypes-like module for Theseus.

Implements a minimal subset of ctypes-style functionality without importing
ctypes. Provides simple numeric types, a Structure base class, and a byref
helper. Invariant functions self-test the implementation and return True.
"""

import struct as _struct


# ---------------------------------------------------------------------------
# Simple numeric types
# ---------------------------------------------------------------------------

class _SimpleType(object):
    """Base class for simple numeric types.

    Subclasses define class attributes:
        _fmt_   : struct format character (e.g. 'i', 'I', 'd')
        _size_  : size in bytes
        _signed_: whether the type is signed (numeric only)
        _default_: default value when constructed without args
    """

    _fmt_ = 'i'
    _size_ = 4
    _signed_ = True
    _default_ = 0

    def __init__(self, value=None):
        if value is None:
            value = self.__class__._default_
        self.value = value

    # value mediated through a property so we can clamp/convert on assignment
    def _get_value(self):
        return self.__dict__.get('_value', self.__class__._default_)

    def _set_value(self, v):
        self.__dict__['_value'] = self._coerce(v)

    value = property(_get_value, _set_value)

    @classmethod
    def _coerce(cls, v):
        # Round-trip through struct to enforce range/representation.
        try:
            packed = _struct.pack(cls._fmt_, v)
            return _struct.unpack(cls._fmt_, packed)[0]
        except _struct.error:
            # Wrap into the type's range for integer types using modular math.
            if cls._fmt_ in ('b', 'h', 'i', 'l', 'q', 'B', 'H', 'I', 'L', 'Q'):
                bits = cls._size_ * 8
                mod = 1 << bits
                v = int(v) % mod
                if cls._signed_ and v >= (mod >> 1):
                    v -= mod
                return v
            raise

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)

    def __eq__(self, other):
        if isinstance(other, _SimpleType):
            return self.value == other.value
        return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.__class__.__name__, self.value))


def _make_simple(name, fmt, size, signed, default=0):
    cls = type(name, (_SimpleType,), {
        '_fmt_': fmt,
        '_size_': size,
        '_signed_': signed,
        '_default_': default,
    })
    return cls


c_byte    = _make_simple('c_byte',    'b', 1, True)
c_ubyte   = _make_simple('c_ubyte',   'B', 1, False)
c_short   = _make_simple('c_short',   'h', 2, True)
c_ushort  = _make_simple('c_ushort',  'H', 2, False)
c_int     = _make_simple('c_int',     'i', 4, True)
c_uint    = _make_simple('c_uint',    'I', 4, False)
c_long    = _make_simple('c_long',    'q', 8, True)
c_ulong   = _make_simple('c_ulong',   'Q', 8, False)
c_int8    = _make_simple('c_int8',    'b', 1, True)
c_uint8   = _make_simple('c_uint8',   'B', 1, False)
c_int16   = _make_simple('c_int16',   'h', 2, True)
c_uint16  = _make_simple('c_uint16',  'H', 2, False)
c_int32   = _make_simple('c_int32',   'i', 4, True)
c_uint32  = _make_simple('c_uint32',  'I', 4, False)
c_int64   = _make_simple('c_int64',   'q', 8, True)
c_uint64  = _make_simple('c_uint64',  'Q', 8, False)
c_float   = _make_simple('c_float',   'f', 4, True, default=0.0)
c_double  = _make_simple('c_double',  'd', 8, True, default=0.0)


def sizeof(obj_or_type):
    """Return the size (in bytes) of a simple type, structure, or instance."""
    if isinstance(obj_or_type, type):
        if issubclass(obj_or_type, _SimpleType):
            return obj_or_type._size_
        if issubclass(obj_or_type, Structure):
            return obj_or_type._compute_size()
    else:
        return sizeof(obj_or_type.__class__)
    raise TypeError("don't know how to compute sizeof(%r)" % (obj_or_type,))


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

class Structure(object):
    """Minimal Structure base class.

    Subclasses define `_fields_` as a list of (name, type) tuples where
    type is one of the c_* simple types defined in this module.
    """

    _fields_ = []

    def __init__(self, *args, **kwargs):
        # Initialize each field to the type's default.
        for name, ftype in self.__class__._fields_:
            object.__setattr__(self, '_' + name, ftype())
        # Positional args fill fields in declaration order.
        for (name, _ftype), val in zip(self.__class__._fields_, args):
            setattr(self, name, val)
        # Keyword args override.
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def _field_types(cls):
        return dict(cls._fields_)

    @classmethod
    def _compute_size(cls):
        return sum(ftype._size_ for _, ftype in cls._fields_)

    def __setattr__(self, name, value):
        ftypes = self.__class__._field_types()
        if name in ftypes:
            ftype = ftypes[name]
            if isinstance(value, _SimpleType):
                inst = ftype(value.value)
            else:
                inst = ftype(value)
            object.__setattr__(self, '_' + name, inst)
        else:
            object.__setattr__(self, name, value)

    def __getattribute__(self, name):
        # Avoid recursion: resolve _fields_ via the class.
        if name.startswith('_') or name in ('__class__', '__dict__'):
            return object.__getattribute__(self, name)
        cls = object.__getattribute__(self, '__class__')
        ftypes = dict(getattr(cls, '_fields_', []))
        if name in ftypes:
            inst = object.__getattribute__(self, '_' + name)
            return inst.value
        return object.__getattribute__(self, name)

    def __repr__(self):
        parts = []
        for name, _ftype in self.__class__._fields_:
            parts.append('%s=%r' % (name, getattr(self, name)))
        return '%s(%s)' % (self.__class__.__name__, ', '.join(parts))

    def __eq__(self, other):
        if not isinstance(other, Structure):
            return NotImplemented
        if self.__class__ is not other.__class__:
            return False
        for name, _ftype in self.__class__._fields_:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __ne__(self, other):
        r = self.__eq__(other)
        if r is NotImplemented:
            return r
        return not r


# ---------------------------------------------------------------------------
# byref / pointer-like reference
# ---------------------------------------------------------------------------

class _CArgObject(object):
    """Lightweight reference wrapper, analogous to ctypes' byref result."""

    __slots__ = ('_obj', '_offset')

    def __init__(self, obj, offset=0):
        self._obj = obj
        self._offset = offset

    @property
    def _type_(self):
        return type(self._obj)

    def __repr__(self):
        return '<cparam ref to %r>' % (self._obj,)


def byref(obj, offset=0):
    """Return a lightweight reference to a simple type or structure instance."""
    if not isinstance(obj, (_SimpleType, Structure)):
        raise TypeError(
            "byref() argument must be a c-type instance, got %r" % (type(obj),)
        )
    return _CArgObject(obj, offset)


def _deref(ref):
    """Dereference a byref result back to the underlying object."""
    if not isinstance(ref, _CArgObject):
        raise TypeError("expected byref result, got %r" % (type(ref),))
    return ref._obj


# ---------------------------------------------------------------------------
# Invariant self-tests
# ---------------------------------------------------------------------------

def ctypes2_simple_types():
    """Verify simple numeric types behave correctly."""
    # default values
    if c_int().value != 0:
        return False
    if c_double().value != 0.0:
        return False

    # construction with value
    if c_int(42).value != 42:
        return False
    if c_uint(7).value != 7:
        return False

    # signedness round-trips
    if c_byte(-1).value != -1:
        return False
    if c_ubyte(255).value != 255:
        return False

    # overflow wrapping for fixed-width int
    if c_uint8(256).value != 0:
        return False
    if c_int8(128).value != -128:
        return False

    # float
    f = c_float(1.5)
    if abs(f.value - 1.5) > 1e-6:
        return False

    # sizeof reports the expected byte widths
    if sizeof(c_int32) != 4:
        return False
    if sizeof(c_int64) != 8:
        return False
    if sizeof(c_int16) != 2:
        return False
    if sizeof(c_double) != 8:
        return False

    # equality semantics
    if c_int(5) != c_int(5):
        return False
    if c_int(5) != 5:
        return False
    if c_int(5) == c_int(6):
        return False

    # mutability
    x = c_int(1)
    x.value = 99
    if x.value != 99:
        return False

    return True


def ctypes2_structure():
    """Verify Structure subclasses store and expose typed fields."""

    class Point(Structure):
        _fields_ = [('x', c_int), ('y', c_int)]

    class Mixed(Structure):
        _fields_ = [('a', c_uint8), ('b', c_int32), ('c', c_double)]

    # default construction
    p = Point()
    if p.x != 0 or p.y != 0:
        return False

    # positional args
    p = Point(3, 4)
    if p.x != 3 or p.y != 4:
        return False

    # keyword args
    p = Point(y=7, x=2)
    if p.x != 2 or p.y != 7:
        return False

    # mutation
    p.x = 11
    if p.x != 11:
        return False

    # type coercion / wrapping
    m = Mixed(256, 1, 2.5)  # 256 wraps to 0 in uint8
    if m.a != 0:
        return False
    if m.b != 1:
        return False
    if abs(m.c - 2.5) > 1e-9:
        return False

    # sizeof for structure equals sum of field sizes
    if sizeof(Point) != 8:
        return False
    if sizeof(Mixed) != 1 + 4 + 8:
        return False
    if sizeof(p) != 8:
        return False

    # equality on structures
    if Point(1, 2) != Point(1, 2):
        return False
    if Point(1, 2) == Point(1, 3):
        return False

    # different structures with same shape are not equal
    class Other(Structure):
        _fields_ = [('x', c_int), ('y', c_int)]

    if Point(1, 2) == Other(1, 2):
        return False

    return True


def ctypes2_byref():
    """Verify byref() produces a reference that mirrors mutations."""

    # byref on a simple type
    n = c_int(10)
    ref = byref(n)
    if not isinstance(ref, _CArgObject):
        return False
    if _deref(ref) is not n:
        return False
    if _deref(ref).value != 10:
        return False

    # mutation through original is observed via the reference
    n.value = 42
    if _deref(ref).value != 42:
        return False

    # mutation through the dereferenced reference is observed in original
    _deref(ref).value = 7
    if n.value != 7:
        return False

    # byref on a Structure
    class Box(Structure):
        _fields_ = [('w', c_int), ('h', c_int)]

    b = Box(3, 4)
    rb = byref(b)
    if _deref(rb) is not b:
        return False
    if _deref(rb).w != 3 or _deref(rb).h != 4:
        return False

    _deref(rb).w = 99
    if b.w != 99:
        return False

    # byref rejects non c-type objects
    try:
        byref(123)
    except TypeError:
        pass
    else:
        return False

    try:
        byref("hello")
    except TypeError:
        pass
    else:
        return False

    # offset is preserved
    ref2 = byref(n, 4)
    if ref2._offset != 4:
        return False

    return True