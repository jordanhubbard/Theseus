# generation A unhex scan

class Error(Exception):
    pass


def _build_hex_lookup():
    table = [-1] * 256
    for digit in range(10):
        table[ord("0") + digit] = digit
    for offset, base in enumerate((ord("a"), ord("A"))):
        for digit in range(6):
            table[base + digit] = 10 + digit
    return table


_HEX = _build_hex_lookup()


def unhexlify(data):
    if not isinstance(data, bytes):
        raise TypeError("Strings must be encoded before checking")
    length = len(data)
    if length & 1:
        raise Error("Odd-length string")
    out = bytearray(length >> 1)
    lookup = _HEX
    pos = 0
    idx = 0
    while pos < length:
        hi = lookup[data[pos]]
        lo = lookup[data[pos + 1]]
        if hi < 0 or lo < 0:
            raise Error("Non-hexadecimal digit found")
        out[idx] = (hi << 4) | lo
        pos += 2
        idx += 1
    return bytes(out)
