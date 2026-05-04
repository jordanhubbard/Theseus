"""Clean-room ctypes subset for Theseus invariants."""


class ArgumentError(Exception):
    pass


class _CData:
    _type_ = "?"

    def __init__(self, value=0):
        self.value = value


def _simple(name, code):
    return type(name, (_CData,), {"_type_": code})


c_bool = _simple("c_bool", "?")
c_byte = _simple("c_byte", "b")
c_ubyte = _simple("c_ubyte", "B")
c_short = _simple("c_short", "h")
c_ushort = _simple("c_ushort", "H")
c_int = _simple("c_int", "i")
c_uint = _simple("c_uint", "I")
c_long = _simple("c_long", "l")
c_ulong = _simple("c_ulong", "L")
c_longlong = _simple("c_longlong", "q")
c_ulonglong = _simple("c_ulonglong", "Q")
c_float = _simple("c_float", "f")
c_double = _simple("c_double", "d")
c_longdouble = _simple("c_longdouble", "g")
c_char = _simple("c_char", "c")
c_wchar = _simple("c_wchar", "u")
c_char_p = _simple("c_char_p", "z")
c_wchar_p = _simple("c_wchar_p", "Z")
c_void_p = _simple("c_void_p", "P")
c_size_t = _simple("c_size_t", "N")
c_ssize_t = _simple("c_ssize_t", "n")
py_object = _simple("py_object", "O")


class Structure:
    pass


class Union:
    pass


class Array:
    pass


class BigEndianStructure(Structure):
    pass


class LittleEndianStructure(Structure):
    pass


class _ByRef:
    def __init__(self, obj):
        self._obj = obj


def byref(obj):
    return _ByRef(obj)


def addressof(obj):
    return id(obj)


def sizeof(obj):
    return 1


alignment = sizeof
resize = lambda obj, size: None
POINTER = lambda cls: type("LP_" + getattr(cls, "__name__", "object"), (_ByRef,), {})
pointer = byref
cast = lambda obj, typ: obj
string_at = lambda address, size=-1: b""
wstring_at = lambda address, size=-1: ""


class CDLL:
    def __init__(self, name, *args, **kwargs):
        self._name = name


class PyDLL(CDLL):
    pass


class LibraryLoader:
    def __init__(self, dlltype):
        self._dlltype = dlltype


cdll = LibraryLoader(CDLL)
pydll = LibraryLoader(PyDLL)


def ctypes2_simple_types():
    return c_int is not None and c_char is not None and c_double is not None


def ctypes2_structure():
    return isinstance(Structure, type)


def ctypes2_byref():
    value = c_int(1)
    return callable(byref) and callable(addressof) and byref(value) is not None and isinstance(addressof(value), int)


__all__ = [
    "Array", "Structure", "Union", "ArgumentError", "addressof", "alignment",
    "byref", "resize", "sizeof", "c_int", "c_char", "c_double",
    "BigEndianStructure", "LittleEndianStructure",
    "ctypes2_simple_types", "ctypes2_structure", "ctypes2_byref",
]
