# generation B adler class


class _Adler:
    _MODULUS = 65521

    def checksum(self, data):
        s1 = 1
        s2 = 0
        for byte in data:
            s1 = (s1 + byte) % self._MODULUS
            s2 = (s2 + s1) % self._MODULUS
        return (s2 << 16) | s1


def adler32(data):
    return _Adler().checksum(data)
