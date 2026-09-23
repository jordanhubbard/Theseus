# generation A typed list

_SUPPORTED = ("b", "I")


def _normalize_signed_byte(value):
    n = int(value) % 256
    if n >= 128:
        n -= 256
    return n


def _normalize_unsigned_int(value):
    return int(value) % (2 ** 32)


_NORMALIZERS = {
    "b": _normalize_signed_byte,
    "I": _normalize_unsigned_int,
}


class TypedSequence(object):
    __slots__ = ("_typecode", "_data")

    def __init__(self, typecode, initializer):
        if typecode not in _NORMALIZERS:
            raise ValueError("bad typecode")
        normalize = _NORMALIZERS[typecode]
        self._typecode = typecode
        self._data = [normalize(item) for item in initializer]

    def tolist(self):
        return list(self._data)


def array(typecode, initializer):
    return TypedSequence(typecode, initializer)
