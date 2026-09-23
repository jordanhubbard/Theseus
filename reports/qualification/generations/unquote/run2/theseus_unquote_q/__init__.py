# generation B unquote class


class _Decode:
    _HEX = "0123456789abcdefABCDEF"

    def __init__(self, string):
        self.string = string

    def decode(self):
        result = []
        index = 0
        length = len(self.string)

        while index < length:
            if (
                self.string[index] == "%"
                and index + 2 < length
                and self.string[index + 1] in self._HEX
                and self.string[index + 2] in self._HEX
            ):
                octets = bytearray()
                while (
                    index + 2 < length
                    and self.string[index] == "%"
                    and self.string[index + 1] in self._HEX
                    and self.string[index + 2] in self._HEX
                ):
                    octets.append(int(self.string[index + 1:index + 3], 16))
                    index += 3
                result.append(octets.decode("utf-8", "replace"))
            else:
                result.append(self.string[index])
                index += 1

        return "".join(result)


def unquote(string):
    return _Decode(string).decode()
