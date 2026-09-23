# generation A adler scan

_MOD = 65521


def adler32(data):
    s1 = 1
    s2 = 0
    for byte in data:
        s1 = (s1 + byte) % _MOD
        s2 = (s2 + s1) % _MOD
    return (s2 << 16) | s1
