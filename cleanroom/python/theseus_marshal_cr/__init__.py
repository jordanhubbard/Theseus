"""
theseus_marshal_cr — Clean-room marshal module.

Implements a marshal-style binary serializer for a useful subset of Python
objects from scratch, using only the standard library's `struct` module
for fixed-width packing.  No import of the original `marshal` module.
"""

import struct as _struct


_T_NULL   = 0x30  # b'0'
_T_NONE   = 0x4E  # b'N'
_T_FALSE  = 0x46  # b'F'
_T_TRUE   = 0x54  # b'T'
_T_INT32  = 0x69  # b'i'
_T_LONG   = 0x6C  # b'l'
_T_FLOAT  = 0x67  # b'g'
_T_CPLX   = 0x79  # b'y'
_T_BYTES  = 0x73  # b's'
_T_STR    = 0x75  # b'u'
_T_TUPLE  = 0x28  # b'('
_T_LIST   = 0x5B  # b'['
_T_DICT   = 0x7B  # b'{'
_T_SET    = 0x3C  # b'<'
_T_FSET   = 0x3E  # b'>'

version = 4


def _emit_int32(out, value):
    out.append(_T_INT32)
    out.extend(_struct.pack('<i', value))


def _emit_long(out, value):
    out.append(_T_LONG)
    if value == 0:
        out.extend(_struct.pack('<i', 0))
        return
    if value < 0:
        sign = -1
        v = -value
    else:
        sign = 1
        v = value
    digits = []
    while v:
        digits.append(v & 0x7FFF)
        v >>= 15
    out.extend(_struct.pack('<i', sign * len(digits)))
    for d in digits:
        out.extend(_struct.pack('<H', d))


def _emit(value, out):
    if value is None:
        out.append(_T_NONE)
    elif value is True:
        out.append(_T_TRUE)
    elif value is False:
        out.append(_T_FALSE)
    elif isinstance(value, int):
        if -0x80000000 <= value <= 0x7FFFFFFF:
            _emit_int32(out, value)
        else:
            _emit_long(out, value)
    elif isinstance(value, float):
        out.append(_T_FLOAT)
        out.extend(_struct.pack('<d', value))
    elif isinstance(value, complex):
        out.append(_T_CPLX)
        out.extend(_struct.pack('<dd', value.real, value.imag))
    elif isinstance(value, (bytes, bytearray)):
        b = bytes(value)
        out.append(_T_BYTES)
        out.extend(_struct.pack('<i', len(b)))
        out.extend(b)
    elif isinstance(value, str):
        encoded = value.encode('utf-8')
        out.append(_T_STR)
        out.extend(_struct.pack('<i', len(encoded)))
        out.extend(encoded)
    elif isinstance(value, tuple):
        out.append(_T_TUPLE)
        out.extend(_struct.pack('<i', len(value)))
        for item in value:
            _emit(item, out)
    elif isinstance(value, list):
        out.append(_T_LIST)
        out.extend(_struct.pack('<i', len(value)))
        for item in value:
            _emit(item, out)
    elif isinstance(value, dict):
        out.append(_T_DICT)
        for k, v in value.items():
            _emit(k, out)
            _emit(v, out)
        out.append(_T_NULL)
    elif isinstance(value, frozenset):
        out.append(_T_FSET)
        items = list(value)
        out.extend(_struct.pack('<i', len(items)))
        for item in items:
            _emit(item, out)
    elif isinstance(value, set):
        out.append(_T_SET)
        items = list(value)
        out.extend(_struct.pack('<i', len(items)))
        for item in items:
            _emit(item, out)
    else:
        raise ValueError(
            "unmarshallable object of type %r" % (type(value).__name__,)
        )


def dumps(value, version=version):
    out = bytearray()
    _emit(value, out)
    return bytes(out)


def dump(value, file, version=version):
    file.write(dumps(value, version))


class _Reader:
    __slots__ = ('buf', 'pos', 'end')

    def __init__(self, buf):
        if not isinstance(buf, (bytes, bytearray, memoryview)):
            raise TypeError(
                "marshal data must be bytes-like, got %r" % type(buf).__name__
            )
        self.buf = bytes(buf)
        self.pos = 0
        self.end = len(self.buf)

    def take(self, n):
        if self.pos + n > self.end:
            raise EOFError("marshal data too short")
        chunk = self.buf[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def take_byte(self):
        if self.pos >= self.end:
            raise EOFError("marshal data too short")
        b = self.buf[self.pos]
        self.pos += 1
        return b


def _read(reader):
    code = reader.take_byte()

    if code == _T_NONE:
        return None
    if code == _T_TRUE:
        return True
    if code == _T_FALSE:
        return False

    if code == _T_INT32:
        return _struct.unpack('<i', reader.take(4))[0]

    if code == _T_LONG:
        n = _struct.unpack('<i', reader.take(4))[0]
        if n == 0:
            return 0
        sign = 1 if n > 0 else -1
        ndigits = n if n > 0 else -n
        result = 0
        for i in range(ndigits):
            d = _struct.unpack('<H', reader.take(2))[0]
            result |= d << (i * 15)
        return sign * result

    if code == _T_FLOAT:
        return _struct.unpack('<d', reader.take(8))[0]

    if code == _T_CPLX:
        re, im = _struct.unpack('<dd', reader.take(16))
        return complex(re, im)

    if code == _T_BYTES:
        n = _struct.unpack('<i', reader.take(4))[0]
        return reader.take(n)

    if code == _T_STR:
        n = _struct.unpack('<i', reader.take(4))[0]
        return reader.take(n).decode('utf-8')

    if code == _T_TUPLE:
        n = _struct.unpack('<i', reader.take(4))[0]
        return tuple(_read(reader) for _ in range(n))

    if code == _T_LIST:
        n = _struct.unpack('<i', reader.take(4))[0]
        return [_read(reader) for _ in range(n)]

    if code == _T_DICT:
        result = {}
        while True:
            if reader.pos >= reader.end:
                raise EOFError("unterminated dict in marshal data")
            if reader.buf[reader.pos] == _T_NULL:
                reader.pos += 1
                return result
            k = _read(reader)
            v = _read(reader)
            result[k] = v

    if code == _T_SET:
        n = _struct.unpack('<i', reader.take(4))[0]
        return set(_read(reader) for _ in range(n))

    if code == _T_FSET:
        n = _struct.unpack('<i', reader.take(4))[0]
        return frozenset(_read(reader) for _ in range(n))

    raise ValueError("bad marshal type code: 0x%02x" % code)


def loads(data):
    return _read(_Reader(data))


def load(file):
    return loads(file.read())


def marshal2_roundtrip():
    data = [1, 'hello', None, True, 3.14]
    return loads(dumps(data)) == data


def marshal2_int():
    b = dumps(42)
    return isinstance(b, bytes) and loads(b) == 42


def marshal2_version():
    return isinstance(version, int)


__all__ = [
    'dumps', 'loads', 'dump', 'load', 'version',
    'marshal2_roundtrip', 'marshal2_int', 'marshal2_version',
]