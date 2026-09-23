# generation B hex class


class _Hex:
    _DIGITS = b"0123456789abcdef"

    def encode(self, data):
        result = bytearray(len(data) * 2)
        for index, value in enumerate(data):
            result[index * 2] = self._DIGITS[value >> 4]
            result[index * 2 + 1] = self._DIGITS[value & 15]
        return bytes(result)


def hexlify(data):
    return _Hex().encode(data)
