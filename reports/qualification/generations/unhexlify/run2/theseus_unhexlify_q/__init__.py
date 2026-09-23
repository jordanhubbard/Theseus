# generation B unhex class


class _Unhex:
    def decode(self, data):
        if isinstance(data, str):
            try:
                data = data.encode("ascii")
            except UnicodeEncodeError:
                raise ValueError("Non-hexadecimal digit found")
        elif not isinstance(data, bytes):
            raise TypeError("argument should be bytes or ASCII string")

        if len(data) % 2:
            raise ValueError("Odd-length string")

        result = bytearray()
        for index in range(0, len(data), 2):
            high = self._digit(data[index])
            low = self._digit(data[index + 1])
            result.append((high << 4) | low)
        return bytes(result)

    @staticmethod
    def _digit(value):
        if 48 <= value <= 57:
            return value - 48
        if 65 <= value <= 70:
            return value - 55
        if 97 <= value <= 102:
            return value - 87
        raise ValueError("Non-hexadecimal digit found")


def unhexlify(data):
    return _Unhex().decode(data)
