"""Clean-room subset of struct used by Theseus invariants."""


class error(Exception):
    pass


_SIZES = {"B": 1, "b": 1, "H": 2, "h": 2, "I": 4, "i": 4, "Q": 8, "q": 8}


def _tokens(fmt):
    fmt = fmt.strip()
    if fmt[:1] in "@=<>!":
        endian = "big" if fmt[0] in ">!" else "little"
        fmt = fmt[1:]
    else:
        endian = "little"
    out = []
    count = ""
    for ch in fmt:
        if ch.isdigit():
            count += ch
        elif ch == "s":
            out.append((ch, int(count or "1")))
            count = ""
        else:
            n = int(count or "1")
            out.extend((ch, 1) for _ in range(n))
            count = ""
    return endian, out


def calcsize(fmt):
    total = 0
    for ch, count in _tokens(fmt)[1]:
        total += count if ch == "s" else _SIZES[ch]
    return total


def pack(fmt, *values):
    endian, tokens = _tokens(fmt)
    if len(values) != len(tokens):
        raise error("pack expected %d items for packing" % len(tokens))
    chunks = []
    for (ch, count), value in zip(tokens, values):
        if ch == "s":
            b = bytes(value)
            chunks.append(b[:count].ljust(count, b"\x00"))
        else:
            chunks.append(int(value).to_bytes(_SIZES[ch], endian, signed=ch.islower()))
    return b"".join(chunks)


def unpack(fmt, data):
    endian, tokens = _tokens(fmt)
    data = bytes(data)
    if len(data) != calcsize(fmt):
        raise error("unpack requires a buffer of %d bytes" % calcsize(fmt))
    pos = 0
    values = []
    for ch, count in tokens:
        if ch == "s":
            values.append(data[pos:pos + count])
            pos += count
        else:
            size = _SIZES[ch]
            values.append(int.from_bytes(data[pos:pos + size], endian, signed=ch.islower()))
            pos += size
    return tuple(values)


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


def struct2_pack():
    return pack(">HI", 0x1234, 0xDEADBEEF) == b"\x12\x34\xDE\xAD\xBE\xEF"


def struct2_unpack():
    return unpack(">HI", b"\x12\x34\xDE\xAD\xBE\xEF") == (0x1234, 0xDEADBEEF)


def struct2_calcsize():
    return calcsize("B") == 1 and calcsize("H") == 2 and calcsize("I") == 4 and calcsize("Q") == 8 and calcsize("4s") == 4


__all__ = [
    "pack", "unpack", "pack_into", "unpack_from", "iter_unpack",
    "calcsize", "Struct", "error",
    "struct2_pack", "struct2_unpack", "struct2_calcsize",
]
