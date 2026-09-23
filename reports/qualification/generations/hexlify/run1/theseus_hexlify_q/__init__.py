# generation A hex scan

_HEX = b"0123456789abcdef"


def hexlify(data):
    out = bytearray(len(data) * 2)
    j = 0
    for byte in data:
        out[j] = _HEX[byte >> 4]
        out[j + 1] = _HEX[byte & 0x0F]
        j += 2
    return bytes(out)
