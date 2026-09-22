# generation A bytearray emit
import array
import math
import sys

CODE_SIZE = {
    "x": 1,
    "c": 1,
    "b": 1,
    "B": 1,
    "h": 2,
    "H": 2,
    "i": 4,
    "I": 4,
    "l": 4,
    "L": 4,
    "q": 8,
    "Q": 8,
    "?": 1,
    "e": 2,
    "f": 4,
    "d": 8,
    "s": 1,
}


class error(Exception):
    pass


def _emit(buf, data):
    buf.extend(data)


def _parse_format(fmt):
    if fmt is None or fmt == "":
        raise error("bad format string")
    idx = 0
    endian = sys.byteorder
    if fmt[0] in "<>!=":
        ch = fmt[0]
        if ch == ">":
            endian = "big"
        elif ch == "<":
            endian = "little"
        elif ch == "!":
            endian = "big"
        elif ch == "=":
            endian = sys.byteorder
        idx = 1
    items = []
    n = len(fmt)
    while idx < n:
        count = 0
        while idx < n and fmt[idx].isdigit():
            count = count * 10 + int(fmt[idx])
            idx += 1
        if count == 0:
            count = 1
        if idx >= n:
            raise error("bad format string")
        code = fmt[idx]
        idx += 1
        if code not in CODE_SIZE:
            raise error("bad format string")
        items.append((count, code))
    if not items:
        raise error("bad format string")
    return endian, items


def _item_size(count, code):
    if code == "s":
        return count
    return count * CODE_SIZE[code]


def calcsize(fmt):
    endian, items = _parse_format(fmt)
    total = 0
    for count, code in items:
        total += _item_size(count, code)
    return total


def _check_int_range(value, bits, signed):
    if not isinstance(value, int):
        raise error("required argument is not an integer")
    if signed:
        lo = -(1 << (bits - 1))
        hi = (1 << (bits - 1)) - 1
    else:
        lo = 0
        hi = (1 << bits) - 1
    if value < lo or value > hi:
        raise error("integer out of range")


def _pack_int(value, size, signed, endian):
    _check_int_range(value, size * 8, signed)
    return int(value).to_bytes(size, endian, signed=signed)


def _pack_bool(value):
    if isinstance(value, bool):
        b = 1 if value else 0
    elif isinstance(value, int):
        b = 1 if value else 0
    else:
        raise error("required argument is not an integer")
    return bytes([b])


def _pack_char(value):
    if isinstance(value, bytes):
        if len(value) != 1:
            raise error("char format requires a bytes object of length 1")
        return value
    if isinstance(value, bytearray):
        if len(value) != 1:
            raise error("char format requires a bytes object of length 1")
        return bytes(value)
    if isinstance(value, int):
        if value < 0 or value > 255:
            raise error("integer out of range")
        return bytes([value])
    if isinstance(value, str):
        if len(value) != 1:
            raise error("char format requires a string of length 1")
        return value.encode("latin1")
    raise error("char format requires a bytes object of length 1")


def _pack_string(value, count):
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, bytearray):
        data = bytes(value)
    elif isinstance(value, str):
        data = value.encode("latin1")
    else:
        raise error("argument for 's' must be a bytes object")
    if len(data) > count:
        raise error("string too long")
    return data.ljust(count, b"\x00")


def _float_to_half(value):
    if not isinstance(value, (int, float)):
        raise error("required argument is not a float")
    fv = float(value)
    if math.isnan(fv):
        return 0x7E00
    if math.isinf(fv):
        return 0x7C00 if fv > 0 else 0xFC00
    if fv == 0.0:
        return 0x8000 if math.copysign(1.0, fv) < 0 else 0x0000
    sign = 0
    if fv < 0.0:
        sign = 1
        fv = -fv
    m, e = math.frexp(fv)
    exp = e + 14
    if exp <= 0:
        frac = int(round(m * (2 ** (24 + exp - 1))))
        if frac == 0:
            return sign << 15
        return (sign << 15) | frac
    if exp >= 31:
        return (sign << 15) | 0x7C00
    frac = int(round((m * 2.0 - 1.0) * (1 << 10)))
    if frac == (1 << 10):
        frac = 0
        exp += 1
        if exp >= 31:
            return (sign << 15) | 0x7C00
    return (sign << 15) | (exp << 10) | (frac & 0x3FF)


def _half_to_float(h):
    sign = (h >> 15) & 1
    exp = (h >> 10) & 0x1F
    frac = h & 0x3FF
    if exp == 0:
        if frac == 0:
            return -0.0 if sign else 0.0
        val = (frac / 1024.0) * (2 ** -14)
    elif exp == 31:
        if frac == 0:
            return float("-inf") if sign else float("inf")
        return float("nan")
    else:
        val = (1.0 + frac / 1024.0) * (2 ** (exp - 15))
    return -val if sign else val


def _pack_float_ieee(value, code, endian):
    if not isinstance(value, (int, float)):
        raise error("required argument is not a float")
    fv = float(value)
    if code == "e":
        bits = _float_to_half(fv)
        return bits.to_bytes(2, endian)
    if code == "f":
        typecode = "f"
    else:
        typecode = "d"
    arr = array.array(typecode, [fv])
    if sys.byteorder != endian:
        arr.byteswap()
    return arr.tobytes()


def _unpack_int(data, offset, size, signed, endian):
    chunk = data[offset : offset + size]
    return int.from_bytes(chunk, endian, signed=signed), offset + size


def _unpack_bool(data, offset):
    b = data[offset]
    return (b != 0), offset + 1


def _unpack_char(data, offset):
    return bytes([data[offset]]), offset + 1


def _unpack_string(data, offset, count):
    chunk = data[offset : offset + count]
    return chunk, offset + count


def _unpack_float_ieee(data, offset, code, endian):
    if code == "e":
        h = int.from_bytes(data[offset : offset + 2], endian)
        return _half_to_float(h), offset + 2
    if code == "f":
        size = 4
        typecode = "f"
    else:
        size = 8
        typecode = "d"
    chunk = data[offset : offset + size]
    arr = array.array(typecode)
    arr.frombytes(chunk)
    if sys.byteorder != endian:
        arr.byteswap()
    return arr[0], offset + size


def pack(fmt, *values):
    endian, items = _parse_format(fmt)
    buf = bytearray()
    vi = 0
    for count, code in items:
        if code == "x":
            for _ in range(count):
                _emit(buf, b"\x00")
            continue
        if code == "s":
            if vi >= len(values):
                raise error("pack expected more arguments")
            _emit(buf, _pack_string(values[vi], count))
            vi += 1
            continue
        for _ in range(count):
            if vi >= len(values):
                raise error("pack expected more arguments")
            value = values[vi]
            vi += 1
            if code == "c":
                chunk = _pack_char(value)
            elif code == "b":
                chunk = _pack_int(value, 1, True, endian)
            elif code == "B":
                chunk = _pack_int(value, 1, False, endian)
            elif code == "h":
                chunk = _pack_int(value, 2, True, endian)
            elif code == "H":
                chunk = _pack_int(value, 2, False, endian)
            elif code == "i":
                chunk = _pack_int(value, 4, True, endian)
            elif code == "I":
                chunk = _pack_int(value, 4, False, endian)
            elif code == "l":
                chunk = _pack_int(value, 4, True, endian)
            elif code == "L":
                chunk = _pack_int(value, 4, False, endian)
            elif code == "q":
                chunk = _pack_int(value, 8, True, endian)
            elif code == "Q":
                chunk = _pack_int(value, 8, False, endian)
            elif code == "?":
                chunk = _pack_bool(value)
            elif code in ("e", "f", "d"):
                chunk = _pack_float_ieee(value, code, endian)
            else:
                raise error("bad format string")
            _emit(buf, chunk)
    if vi != len(values):
        raise error("pack expected %d items for packing (got %d)" % (vi, len(values)))
    return bytes(buf)


def unpack(fmt, buffer):
    if isinstance(buffer, bytearray):
        data = bytes(buffer)
    elif isinstance(buffer, memoryview):
        data = buffer.tobytes()
    elif isinstance(buffer, bytes):
        data = buffer
    else:
        raise error("unpack requires a bytes-like object")
    endian, items = _parse_format(fmt)
    need = calcsize(fmt)
    if len(data) < need:
        raise error("unpack requires a buffer of %d bytes" % need)
    if len(data) > need:
        raise error("unpack requires a buffer of %d bytes" % need)
    offset = 0
    out = []
    for count, code in items:
        if code == "x":
            offset += count
            continue
        if code == "s":
            val, offset = _unpack_string(data, offset, count)
            out.append(val)
            continue
        for _ in range(count):
            if code == "c":
                val, offset = _unpack_char(data, offset)
            elif code == "b":
                val, offset = _unpack_int(data, offset, 1, True, endian)
            elif code == "B":
                val, offset = _unpack_int(data, offset, 1, False, endian)
            elif code == "h":
                val, offset = _unpack_int(data, offset, 2, True, endian)
            elif code == "H":
                val, offset = _unpack_int(data, offset, 2, False, endian)
            elif code == "i":
                val, offset = _unpack_int(data, offset, 4, True, endian)
            elif code == "I":
                val, offset = _unpack_int(data, offset, 4, False, endian)
            elif code == "l":
                val, offset = _unpack_int(data, offset, 4, True, endian)
            elif code == "L":
                val, offset = _unpack_int(data, offset, 4, False, endian)
            elif code == "q":
                val, offset = _unpack_int(data, offset, 8, True, endian)
            elif code == "Q":
                val, offset = _unpack_int(data, offset, 8, False, endian)
            elif code == "?":
                val, offset = _unpack_bool(data, offset)
            elif code in ("e", "f", "d"):
                val, offset = _unpack_float_ieee(data, offset, code, endian)
            else:
                raise error("bad format string")
            out.append(val)
    return tuple(out)
