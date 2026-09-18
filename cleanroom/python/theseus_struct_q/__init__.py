"""
theseus_struct_q — Clean-room pack/unpack of C struct layouts.
Do NOT import struct or _struct.
"""


class error(Exception):
    """Raised on format/buffer mismatches and out-of-range values."""


_SIZES = {
    "x": (1, "pad"),
    "?": (1, "bool"),
    "b": (1, "i"),
    "B": (1, "I"),
    "h": (2, "i"),
    "H": (2, "I"),
    "i": (4, "i"),
    "I": (4, "I"),
    "q": (8, "i"),
    "Q": (8, "I"),
    "f": (4, "f"),
    "d": (8, "d"),
    "e": (2, "e"),
}


def _parse_fmt(fmt):
    endian = ">"
    i = 0
    if fmt and fmt[0] in "@=<>!":
        endian = ">" if fmt[0] in "!>" else "<" if fmt[0] == "<" else "="
        if fmt[0] == "@":
            endian = "="
        if fmt[0] == "!":
            endian = ">"
        i = 1
    big = endian != "<"
    fields = []
    n = len(fmt)
    while i < n:
        count = 0
        while i < n and fmt[i].isdigit():
            count = count * 10 + int(fmt[i])
            i += 1
        if count == 0:
            count = 1
        if i >= n:
            break
        code = fmt[i]
        i += 1
        if code not in _SIZES:
            raise error("bad char in struct format")
        size, kind = _SIZES[code]
        for _ in range(count):
            fields.append((size, kind, big))
    return fields


def calcsize(fmt):
    return sum(size for size, _kind, _big in _parse_fmt(fmt))


def _pack_int(value, nbytes, signed, big):
    if signed:
        minv = -(1 << (nbytes * 8 - 1))
        maxv = (1 << (nbytes * 8 - 1)) - 1
    else:
        minv = 0
        maxv = (1 << (nbytes * 8)) - 1
    if not minv <= int(value) <= maxv:
        raise error("argument out of range")
    value = int(value)
    if value < 0:
        value += 1 << (nbytes * 8)
    out = []
    for _ in range(nbytes):
        out.append(value & 0xFF)
        value >>= 8
    if big:
        out.reverse()
    return bytes(out)


def _pack_float(value, nbytes, big):
    if nbytes == 2 and value == 0.0:
        return b"\x00\x00"
    raise error("float formats other than half-float 0.0 are out of scope")


def pack(fmt, *values):
    fields = _parse_fmt(fmt)
    needed = sum(1 for _s, kind, _b in fields if kind != "pad")
    if len(values) != needed:
        raise error("pack expected {} items, got {}".format(needed, len(values)))
    out = bytearray()
    vi = 0
    for size, kind, big in fields:
        if kind == "pad":
            out.extend(b"\x00" * size)
            continue
        val = values[vi]
        vi += 1
        if kind == "bool":
            out.extend(_pack_int(1 if val else 0, 1, False, big))
        elif kind == "i":
            out.extend(_pack_int(val, size, True, big))
        elif kind == "I":
            out.extend(_pack_int(val, size, False, big))
        elif kind in ("f", "d", "e"):
            out.extend(_pack_float(val, size, big))
        else:
            raise error("unsupported")
    return bytes(out)


def _unpack_int(buf, signed, big):
    if big:
        acc = 0
        for b in buf:
            acc = (acc << 8) | b
    else:
        acc = 0
        shift = 0
        for b in buf:
            acc |= b << shift
            shift += 8
    nbytes = len(buf)
    if signed:
        signbit = 1 << (nbytes * 8 - 1)
        if acc & signbit:
            acc -= 1 << (nbytes * 8)
    return acc


def unpack(fmt, buffer):
    buffer = bytes(buffer)
    fields = _parse_fmt(fmt)
    size = sum(s for s, _k, _b in fields)
    if len(buffer) != size:
        raise error("unpack requires a buffer of {} bytes".format(size))
    off = 0
    out = []
    for fsize, kind, big in fields:
        chunk = buffer[off:off + fsize]
        off += fsize
        if kind == "pad":
            continue
        if kind == "bool":
            out.append(bool(chunk[0]))
        elif kind == "i":
            out.append(_unpack_int(chunk, True, big))
        elif kind == "I":
            out.append(_unpack_int(chunk, False, big))
        else:
            raise error("unsupported unpack")
    return tuple(out)


__all__ = ["pack", "unpack", "calcsize", "error"]
