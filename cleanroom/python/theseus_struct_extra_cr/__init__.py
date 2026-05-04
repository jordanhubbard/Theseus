"""Extra clean-room struct invariants."""


class error(Exception):
    pass


_SIZES = {"B": 1, "H": 2, "I": 4, "Q": 8}


def _tokens(fmt):
    fmt = fmt.strip()
    endian = "big" if fmt[:1] in ">!" else "little"
    if fmt[:1] in "@=<>!":
        fmt = fmt[1:]
    out = []
    count = ""
    for ch in fmt:
        if ch.isdigit():
            count += ch
        else:
            n = int(count or "1")
            out.extend([ch] * n)
            count = ""
    return endian, out


def calcsize(fmt):
    return sum(_SIZES[ch] for ch in _tokens(fmt)[1])


def pack(fmt, *values):
    endian, tokens = _tokens(fmt)
    if len(tokens) != len(values):
        raise error("pack expected %d items" % len(tokens))
    return b"".join(int(v).to_bytes(_SIZES[ch], endian) for ch, v in zip(tokens, values))


def unpack(fmt, data):
    endian, tokens = _tokens(fmt)
    data = bytes(data)
    pos = 0
    out = []
    for ch in tokens:
        size = _SIZES[ch]
        out.append(int.from_bytes(data[pos:pos + size], endian))
        pos += size
    return tuple(out)


def pack_into(fmt, buffer, offset, *values):
    buffer[offset:offset + calcsize(fmt)] = pack(fmt, *values)


def unpack_from(fmt, buffer, offset=0):
    return unpack(fmt, bytes(buffer)[offset:offset + calcsize(fmt)])


def iter_unpack(fmt, buffer):
    size = calcsize(fmt)
    data = bytes(buffer)
    for pos in range(0, len(data), size):
        yield unpack(fmt, data[pos:pos + size])


class Struct:
    def __init__(self, fmt):
        self.format = fmt
        self.size = calcsize(fmt)

    def pack(self, *values):
        return pack(self.format, *values)

    def unpack(self, data):
        return unpack(self.format, data)


def struct2_pack_unpack():
    data = pack(">HH", 1234, 5678)
    return unpack(">HH", data) == (1234, 5678)


def struct2_calcsize():
    return calcsize(">HH") == 4 and calcsize(">I") == 4 and calcsize(">Q") == 8


def struct2_network_order():
    return pack("!I", 0x01020304) == b"\x01\x02\x03\x04"


__all__ = [
    "error", "pack", "pack_into", "unpack", "unpack_from", "iter_unpack",
    "calcsize", "Struct",
    "struct2_pack_unpack", "struct2_calcsize", "struct2_network_order",
]
