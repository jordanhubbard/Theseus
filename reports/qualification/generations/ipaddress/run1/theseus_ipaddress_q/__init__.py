# generation A ipv4 class

__all__ = ["IPv4Address"]


class AddressValueError(ValueError):
    pass


class IPv4Address(object):
    """IPv4 address object parsed from a dotted-decimal string."""

    __slots__ = ("_ip",)

    def __init__(self, address):
        if isinstance(address, IPv4Address):
            self._ip = address._ip
            return
        if isinstance(address, int):
            if address < 0 or address > 0xFFFFFFFF:
                msg = "%r is not a valid IPv4 address" % (address,)
                raise AddressValueError(msg)
            self._ip = address
            return
        if not isinstance(address, (str, bytes)):
            msg = "address must be str, bytes, int, or IPv4Address"
            raise TypeError(msg)
        if isinstance(address, bytes):
            address = address.decode("ascii")
        self._ip = self._parse_dotted_quad(address)

    @staticmethod
    def _parse_dotted_quad(address):
        if not address:
            raise AddressValueError("%r does not appear to be an IPv4 address" % (address,))
        parts = address.split(".")
        if len(parts) != 4:
            raise AddressValueError("%r does not appear to be an IPv4 address" % (address,))
        octets = []
        for part in parts:
            if not part:
                raise AddressValueError("%r does not appear to be an IPv4 address" % (address,))
            if not part.isdigit():
                raise AddressValueError("%r does not appear to be an IPv4 address" % (address,))
            if len(part) > 1 and part[0] == "0":
                raise AddressValueError("%r does not appear to be an IPv4 address" % (address,))
            try:
                value = int(part, 10)
            except ValueError:
                raise AddressValueError("%r does not appear to be an IPv4 address" % (address,))
            if value > 255:
                raise AddressValueError("%r does not appear to be an IPv4 address" % (address,))
            octets.append(value)
        return (
            (octets[0] << 24)
            | (octets[1] << 16)
            | (octets[2] << 8)
            | octets[3]
        )

    def __str__(self):
        return ".".join(
            str((self._ip >> shift) & 0xFF)
            for shift in (24, 16, 8, 0)
        )

    def __repr__(self):
        return "IPv4Address(%r)" % (str(self),)

    @property
    def is_loopback(self):
        return (self._ip >> 24) == 127

    @property
    def is_private(self):
        first = self._ip >> 24
        if first == 10:
            return True
        if first == 172:
            second = (self._ip >> 16) & 0xFF
            return 16 <= second <= 31
        if first == 192:
            second = (self._ip >> 16) & 0xFF
            return second == 168
        return False
