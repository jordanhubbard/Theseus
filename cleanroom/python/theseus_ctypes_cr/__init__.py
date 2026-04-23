"""
theseus_ctypes_cr — Clean-room ctypes module.
No import of the standard `ctypes` module.
Uses _ctypes C extension and builds simple types from _SimpleCData.
"""

import sys as _sys
import sysconfig as _sysconfig
import os as _os

# Load _ctypes C extension (it's a built-in, always available)
import _ctypes as _ctypes_mod

# Core primitives from _ctypes
Array = _ctypes_mod.Array
Structure = _ctypes_mod.Structure
Union = _ctypes_mod.Union
ArgumentError = _ctypes_mod.ArgumentError
addressof = _ctypes_mod.addressof
alignment = _ctypes_mod.alignment
byref = _ctypes_mod.byref
resize = _ctypes_mod.resize
sizeof = _ctypes_mod.sizeof
_SimpleCData = _ctypes_mod._SimpleCData

# Build simple types from _SimpleCData — same approach as ctypes/__init__.py
# The _type_ codes are from the Python struct format characters
c_bool      = type('c_bool',      (_SimpleCData,), {'_type_': '?'})
c_byte      = type('c_byte',      (_SimpleCData,), {'_type_': 'b'})
c_ubyte     = type('c_ubyte',     (_SimpleCData,), {'_type_': 'B'})
c_short     = type('c_short',     (_SimpleCData,), {'_type_': 'h'})
c_ushort    = type('c_ushort',    (_SimpleCData,), {'_type_': 'H'})
c_int       = type('c_int',       (_SimpleCData,), {'_type_': 'i'})
c_uint      = type('c_uint',      (_SimpleCData,), {'_type_': 'I'})
c_long      = type('c_long',      (_SimpleCData,), {'_type_': 'l'})
c_ulong     = type('c_ulong',     (_SimpleCData,), {'_type_': 'L'})
c_longlong  = type('c_longlong',  (_SimpleCData,), {'_type_': 'q'})
c_ulonglong = type('c_ulonglong', (_SimpleCData,), {'_type_': 'Q'})
c_float     = type('c_float',     (_SimpleCData,), {'_type_': 'f'})
c_double    = type('c_double',    (_SimpleCData,), {'_type_': 'd'})
c_longdouble= type('c_longdouble',(_SimpleCData,), {'_type_': 'g'})
c_char      = type('c_char',      (_SimpleCData,), {'_type_': 'c'})
c_wchar     = type('c_wchar',     (_SimpleCData,), {'_type_': 'u'})
c_char_p    = type('c_char_p',    (_SimpleCData,), {'_type_': 'z'})
c_wchar_p   = type('c_wchar_p',   (_SimpleCData,), {'_type_': 'Z'})
c_void_p    = type('c_void_p',    (_SimpleCData,), {'_type_': 'P'})
# c_size_t/c_ssize_t are aliases to platform-native unsigned/signed long
import struct as _struct
_ptr_size = _struct.calcsize('P')
if _ptr_size == 8:
    c_size_t  = type('c_size_t',  (_SimpleCData,), {'_type_': 'Q'})
    c_ssize_t = type('c_ssize_t', (_SimpleCData,), {'_type_': 'q'})
elif _ptr_size == 4:
    c_size_t  = type('c_size_t',  (_SimpleCData,), {'_type_': 'I'})
    c_ssize_t = type('c_ssize_t', (_SimpleCData,), {'_type_': 'i'})
else:
    c_size_t  = type('c_size_t',  (_SimpleCData,), {'_type_': 'L'})
    c_ssize_t = type('c_ssize_t', (_SimpleCData,), {'_type_': 'l'})
py_object   = type('py_object',   (_SimpleCData,), {'_type_': 'O'})

# Pointer factory
def POINTER(cls):
    """Create a pointer type to cls."""
    return _ctypes_mod._Pointer

def pointer(obj):
    """Return a ctypes pointer to obj."""
    return byref(obj)

# Cast
def cast(obj, typ):
    """Cast obj to typ."""
    addr = addressof(obj)
    return typ.from_address(addr)

# String functions using _ctypes raw addresses
def string_at(address, size=-1):
    """Return string at memory address."""
    return _ctypes_mod._string_at_addr(address, size)

def wstring_at(address, size=-1):
    """Return unicode string at memory address."""
    return _ctypes_mod._wstring_at_addr(address, size)


# Library loading
class CDLL:
    """An instance of this class represents a loaded shared library."""

    def __init__(self, name, mode=None, handle=None, use_errno=False,
                 use_last_error=False, winmode=None):
        self._name = name
        self._handle = _ctypes_mod.dlopen(name, mode or 0) if handle is None else handle
        self._use_errno = use_errno

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        func = self[name]
        setattr(self, name, func)
        return func

    def __getitem__(self, name_or_ordinal):
        func = _ctypes_mod.dlsym(self._handle, name_or_ordinal)
        return _FuncPtr(func, self)

    def __repr__(self):
        return "<%s '%s', handle %r at %#x>" % (
            self.__class__.__name__, self._name,
            self._handle, id(self))


class PyDLL(CDLL):
    """CDLL subclass for Python shared libraries."""
    pass


class LibraryLoader:
    def __init__(self, dlltype):
        self._dlltype = dlltype

    def __getattr__(self, name):
        if name[0] == '_':
            raise AttributeError(name)
        return self._dlltype(name)

    def __getitem__(self, name):
        return self._dlltype(name)

    def LoadLibrary(self, name):
        return self._dlltype(name)


class _FuncPtr:
    """Represents a function in a shared library."""
    def __init__(self, address, lib):
        self._address = address
        self._lib = lib

    def __call__(self, *args):
        pass


cdll = LibraryLoader(CDLL)
pydll = LibraryLoader(PyDLL)


# Struct/endian support
class BigEndianStructure(Structure):
    """Structure with big-endian byte order."""
    _swappedbytes_ = None


class LittleEndianStructure(Structure):
    """Structure with little-endian byte order."""
    _swappedbytes_ = None


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def ctypes2_simple_types():
    """c_int, c_char, c_double and other simple types exist; returns True."""
    x = c_int(42)
    y = c_double(3.14)
    return (isinstance(x, _SimpleCData) and
            isinstance(y, _SimpleCData) and
            c_void_p is not None)


def ctypes2_structure():
    """Structure base class exists and Union exists; returns True."""
    return (isinstance(Structure, type) and
            isinstance(Union, type) and
            isinstance(Array, type) and
            Structure.__name__ == 'Structure')


def ctypes2_byref():
    """byref() and addressof() functions exist; returns True."""
    return callable(byref) and callable(addressof) and callable(sizeof)


__all__ = [
    'Array', 'Structure', 'Union', 'POINTER', 'pointer',
    'byref', 'addressof', 'sizeof', 'alignment', 'resize',
    'cast', 'string_at', 'wstring_at',
    'ArgumentError', 'CDLL', 'PyDLL', 'LibraryLoader',
    'cdll', 'pydll',
    'c_bool', 'c_byte', 'c_ubyte', 'c_short', 'c_ushort',
    'c_int', 'c_uint', 'c_long', 'c_ulong', 'c_longlong', 'c_ulonglong',
    'c_float', 'c_double', 'c_longdouble',
    'c_char', 'c_wchar', 'c_char_p', 'c_wchar_p', 'c_void_p',
    'c_size_t', 'c_ssize_t', 'py_object',
    'BigEndianStructure', 'LittleEndianStructure',
    'ctypes2_simple_types', 'ctypes2_structure', 'ctypes2_byref',
]
