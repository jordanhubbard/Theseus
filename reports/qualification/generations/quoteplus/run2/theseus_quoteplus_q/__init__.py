# generation B quote class


class _Quote:
    _SAFE = frozenset(
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        b"abcdefghijklmnopqrstuvwxyz"
        b"0123456789"
        b"-._~"
    )
    _HEX = "0123456789ABCDEF"

    def encode(self, string):
        encoded = string.encode("utf-8")
        result = []
        for value in encoded:
            if value in self._SAFE:
                result.append(chr(value))
            elif value == 32:
                result.append("+")
            else:
                result.append("%")
                result.append(self._HEX[value >> 4])
                result.append(self._HEX[value & 15])
        return "".join(result)


def quote_plus(string):
    return _Quote().encode(string)
