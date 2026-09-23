# generation B v4 factory


class _V4:
    __slots__ = ("_value", "_text")

    def __init__(self, address):
        if not isinstance(address, str):
            raise ValueError("IPv4 address must be a dotted-quad string")

        parts = address.split(".")
        if len(parts) != 4:
            raise ValueError("IPv4 address must contain four octets")

        octets = []
        for part in parts:
            if not part or any(character not in "0123456789" for character in part):
                raise ValueError("IPv4 octets must be decimal integers")
            if len(part) > 1 and part[0] == "0":
                raise ValueError("leading zeros are not permitted in IPv4 octets")
            value = int(part)
            if value > 255:
                raise ValueError("IPv4 octet exceeds 255")
            octets.append(value)

        self._value = (
            (octets[0] << 24)
            | (octets[1] << 16)
            | (octets[2] << 8)
            | octets[3]
        )
        self._text = ".".join(str(octet) for octet in octets)

    def __str__(self):
        return self._text

    def __repr__(self):
        return "IPv4Address(%r)" % self._text

    def __eq__(self, other):
        if not isinstance(other, _V4):
            return NotImplemented
        return self._value == other._value

    def __hash__(self):
        return hash(self._value)

    @property
    def is_loopback(self):
        return (self._value >> 24) == 127

    @property
    def is_private(self):
        first = self._value >> 24
        second = (self._value >> 16) & 255
        return (
            first == 10
            or (first == 172 and 16 <= second <= 31)
            or (first == 192 and second == 168)
        )


def IPv4Address(address):
    return _V4(address)
