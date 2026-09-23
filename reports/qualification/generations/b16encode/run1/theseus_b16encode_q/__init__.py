# generation A hex scan

_HEX = b"0123456789ABCDEF"


def b16encode(data):
    data = bytes(data)
    out = bytearray(len(data) * 2)
    for i, byte in enumerate(data):
        out[2 * i] = _HEX[byte >> 4]
        out[2 * i + 1] = _HEX[byte & 0x0F]
    return bytes(out)
