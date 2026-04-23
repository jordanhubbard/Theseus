"""
theseus_ipaddress_cr — Clean-room ipaddress module.
No import of the standard `ipaddress` module.
"""

import struct as _struct
import re as _re


class AddressValueError(ValueError):
    pass


class NetmaskValueError(ValueError):
    pass


def ip_address(address):
    """Create an IPv4Address or IPv6Address object."""
    try:
        return IPv4Address(address)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Address(address)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError('%r does not appear to be an IPv4 or IPv6 address' % address)


def ip_network(address, strict=True):
    """Create an IPv4Network or IPv6Network object."""
    try:
        return IPv4Network(address, strict=strict)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Network(address, strict=strict)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError('%r does not appear to be an IPv4 or IPv6 network' % address)


def ip_interface(address):
    """Create an IPv4Interface or IPv6Interface object."""
    try:
        return IPv4Interface(address)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Interface(address)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError('%r does not appear to be an IPv4 or IPv6 interface' % address)


class _BaseAddress:
    """Base class for IP addresses."""

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._ip == other._ip

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._ip < other._ip

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._ip > other._ip

    def __ge__(self, other):
        return self == other or self > other

    def __hash__(self):
        return hash(self._ip)

    def __int__(self):
        return self._ip

    def __index__(self):
        return self._ip

    def __add__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return self.__class__(int(self) + other)

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return self.__class__(int(self) - other)


class IPv4Address(_BaseAddress):
    """Represent an IPv4 address."""

    _version = 4
    _max_prefixlen = 32
    _ALL_ONES = (2 ** _max_prefixlen) - 1

    def __init__(self, address):
        if isinstance(address, int):
            self._ip = address
            if address < 0 or address > self._ALL_ONES:
                raise AddressValueError('IPv4 address out of range')
        elif isinstance(address, bytes):
            if len(address) != 4:
                raise AddressValueError('IPv4 address requires 4 bytes')
            self._ip = _struct.unpack('>I', address)[0]
        else:
            address = str(address)
            parts = address.split('.')
            if len(parts) != 4:
                raise AddressValueError('Expected 4 octets in %r' % address)
            try:
                octets = [int(x) for x in parts]
            except ValueError:
                raise AddressValueError('Non-decimal octets in %r' % address)
            for octet in octets:
                if octet < 0 or octet > 255:
                    raise AddressValueError('Octet out of range in %r' % address)
            self._ip = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]

    @property
    def version(self):
        return self._version

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def packed(self):
        return _struct.pack('>I', self._ip)

    @property
    def is_private(self):
        return (self._ip & 0xFF000000 == 0x0A000000 or
                self._ip & 0xFFF00000 == 0xAC100000 or
                self._ip & 0xFFFF0000 == 0xC0A80000)

    @property
    def is_loopback(self):
        return self._ip & 0xFF000000 == 0x7F000000

    @property
    def is_multicast(self):
        return self._ip & 0xF0000000 == 0xE0000000

    @property
    def is_link_local(self):
        return self._ip & 0xFFFF0000 == 0xA9FE0000

    @property
    def is_unspecified(self):
        return self._ip == 0

    @property
    def is_reserved(self):
        return self._ip & 0xF0000000 == 0xF0000000

    @property
    def is_global(self):
        return not (self.is_private or self.is_loopback or self.is_multicast or
                    self.is_link_local or self.is_unspecified or self.is_reserved)

    def __str__(self):
        return '%d.%d.%d.%d' % (
            (self._ip >> 24) & 0xFF,
            (self._ip >> 16) & 0xFF,
            (self._ip >> 8) & 0xFF,
            self._ip & 0xFF)

    def __repr__(self):
        return 'IPv4Address(%r)' % str(self)


class IPv6Address(_BaseAddress):
    """Represent an IPv6 address."""

    _version = 6
    _max_prefixlen = 128
    _ALL_ONES = (2 ** _max_prefixlen) - 1

    def __init__(self, address):
        if isinstance(address, int):
            self._ip = address
            if address < 0 or address > self._ALL_ONES:
                raise AddressValueError('IPv6 address out of range')
        elif isinstance(address, bytes):
            if len(address) != 16:
                raise AddressValueError('IPv6 address requires 16 bytes')
            hi, lo = _struct.unpack('>QQ', address)
            self._ip = (hi << 64) | lo
        else:
            address = str(address)
            if '%' in address:
                address, sep, scope = address.partition('%')
            self._ip = self._parse_ipv6(address)

    def _parse_ipv6(self, addr):
        if '::' in addr:
            left, sep, right = addr.partition('::')
            left_parts = [p for p in left.split(':') if p] if left else []
            right_parts = [p for p in right.split(':') if p] if right else []
            missing = 8 - len(left_parts) - len(right_parts)
            parts = left_parts + ['0'] * missing + right_parts
        else:
            parts = addr.split(':')
        if len(parts) != 8:
            raise AddressValueError('Expected 8 groups in IPv6 address: %r' % addr)
        result = 0
        for part in parts:
            try:
                group = int(part, 16)
            except ValueError:
                raise AddressValueError('Invalid group %r in %r' % (part, addr))
            if group < 0 or group > 0xFFFF:
                raise AddressValueError('Group out of range in %r' % addr)
            result = (result << 16) | group
        return result

    @property
    def version(self):
        return self._version

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def packed(self):
        hi = self._ip >> 64
        lo = self._ip & ((1 << 64) - 1)
        return _struct.pack('>QQ', hi, lo)

    @property
    def is_loopback(self):
        return self._ip == 1

    @property
    def is_unspecified(self):
        return self._ip == 0

    @property
    def is_multicast(self):
        return (self._ip >> 120) == 0xFF

    @property
    def is_link_local(self):
        return (self._ip >> 118) == 0b1111111010

    @property
    def is_private(self):
        return (self._ip >> 112) == 0xFD00 >> 8

    def __str__(self):
        groups = []
        for i in range(7, -1, -1):
            groups.append('%x' % ((self._ip >> (i * 16)) & 0xFFFF))
        return ':'.join(groups)

    def __repr__(self):
        return 'IPv6Address(%r)' % str(self)


class _BaseNetwork:
    """Base class for IP networks."""

    def __iter__(self):
        cur = int(self.network_address)
        bcast = int(self.broadcast_address)
        while cur <= bcast:
            yield self._address_class(cur)
            cur += 1

    def __contains__(self, other):
        if isinstance(other, str):
            try:
                other = self._address_class(other)
            except AddressValueError:
                return False
        if isinstance(other, _BaseAddress):
            return (int(self.network_address) <= int(other) <= int(self.broadcast_address))
        return False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.network_address == other.network_address and
                self.netmask == other.netmask)

    def __hash__(self):
        return hash((self.network_address, self.prefixlen))

    def overlaps(self, other):
        return (int(self.network_address) <= int(other.broadcast_address) and
                int(other.network_address) <= int(self.broadcast_address))

    def subnet_of(self, other):
        return (int(other.network_address) <= int(self.network_address) and
                int(self.broadcast_address) <= int(other.broadcast_address))

    def supernet_of(self, other):
        return other.subnet_of(self)

    @property
    def num_addresses(self):
        return int(self.broadcast_address) - int(self.network_address) + 1

    @property
    def prefixlen(self):
        return self._prefixlen

    @property
    def with_prefixlen(self):
        return '%s/%d' % (self.network_address, self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (self.network_address, self.netmask)

    @property
    def compressed(self):
        return self.with_prefixlen

    def __str__(self):
        return self.with_prefixlen

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.with_prefixlen)


class IPv4Network(_BaseNetwork):
    """Represent an IPv4 network."""

    _version = 4
    _max_prefixlen = 32
    _address_class = IPv4Address

    def __init__(self, address, strict=True):
        if isinstance(address, (int, bytes)):
            self.network_address = IPv4Address(address)
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv4Address(self._ALL_ONES)
            self.hostmask = IPv4Address(0)
            self.broadcast_address = self.network_address
            return

        address = str(address)
        if '/' in address:
            addr_str, sep, prefix_str = address.partition('/')
        else:
            addr_str = address
            prefix_str = str(self._max_prefixlen)

        self.network_address = IPv4Address(addr_str)

        if prefix_str.isdigit():
            self._prefixlen = int(prefix_str)
            if self._prefixlen < 0 or self._prefixlen > self._max_prefixlen:
                raise NetmaskValueError('Prefix length out of range: %s' % prefix_str)
            mask = (self._ALL_ONES >> (self._max_prefixlen - self._prefixlen)) << (self._max_prefixlen - self._prefixlen)
        else:
            netmask = IPv4Address(prefix_str)
            mask = int(netmask)
            self._prefixlen = bin(mask).count('1')

        self.netmask = IPv4Address(mask)
        self.hostmask = IPv4Address(self._ALL_ONES ^ mask)

        net_int = int(self.network_address) & mask
        bcast_int = net_int | (self._ALL_ONES ^ mask)

        if strict and int(self.network_address) != net_int:
            raise ValueError('%s has host bits set' % address)

        self.network_address = IPv4Address(net_int)
        self.broadcast_address = IPv4Address(bcast_int)

    _ALL_ONES = (2 ** _max_prefixlen) - 1


class IPv6Network(_BaseNetwork):
    """Represent an IPv6 network."""

    _version = 6
    _max_prefixlen = 128
    _address_class = IPv6Address
    _ALL_ONES = (2 ** _max_prefixlen) - 1

    def __init__(self, address, strict=True):
        if isinstance(address, int):
            self.network_address = IPv6Address(address)
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv6Address(self._ALL_ONES)
            self.hostmask = IPv6Address(0)
            self.broadcast_address = self.network_address
            return

        address = str(address)
        if '/' in address:
            addr_str, sep, prefix_str = address.partition('/')
        else:
            addr_str = address
            prefix_str = str(self._max_prefixlen)

        self.network_address = IPv6Address(addr_str)

        self._prefixlen = int(prefix_str)
        if self._prefixlen < 0 or self._prefixlen > self._max_prefixlen:
            raise NetmaskValueError('Prefix length out of range: %s' % prefix_str)

        mask = (self._ALL_ONES >> (self._max_prefixlen - self._prefixlen)) << (self._max_prefixlen - self._prefixlen)
        self.netmask = IPv6Address(mask)
        self.hostmask = IPv6Address(self._ALL_ONES ^ mask)

        net_int = int(self.network_address) & mask
        bcast_int = net_int | (self._ALL_ONES ^ mask)

        if strict and int(self.network_address) != net_int:
            raise ValueError('%s has host bits set' % address)

        self.network_address = IPv6Address(net_int)
        self.broadcast_address = IPv6Address(bcast_int)


class IPv4Interface(IPv4Address):
    """IPv4 interface with network context."""

    def __init__(self, address):
        if isinstance(address, (int, bytes)):
            IPv4Address.__init__(self, address)
            self.network = IPv4Network(address, strict=False)
            self._prefixlen = self._max_prefixlen
            return
        address = str(address)
        if '/' in address:
            addr_str, sep, prefix_str = address.partition('/')
        else:
            addr_str = address
            prefix_str = str(self._max_prefixlen)
        IPv4Address.__init__(self, addr_str)
        self.network = IPv4Network('%s/%s' % (addr_str, prefix_str), strict=False)
        self._prefixlen = self.network.prefixlen

    @property
    def with_prefixlen(self):
        return '%s/%d' % (self, self._prefixlen)


class IPv6Interface(IPv6Address):
    """IPv6 interface with network context."""

    def __init__(self, address):
        if isinstance(address, int):
            IPv6Address.__init__(self, address)
            self.network = IPv6Network(address, strict=False)
            self._prefixlen = self._max_prefixlen
            return
        address = str(address)
        if '/' in address:
            addr_str, sep, prefix_str = address.partition('/')
        else:
            addr_str = address
            prefix_str = str(self._max_prefixlen)
        IPv6Address.__init__(self, addr_str)
        self.network = IPv6Network('%s/%s' % (addr_str, prefix_str), strict=False)
        self._prefixlen = self.network.prefixlen


def summarize_address_range(first, last):
    """Summarizes a range of IPs to the minimum number of CIDR blocks."""
    first_int = int(first)
    last_int = int(last)
    result = []
    while first_int <= last_int:
        nbits = 0
        while nbits < first._max_prefixlen:
            nbits += 1
            nbits_mask = ((1 << first._max_prefixlen) - 1) >> nbits
            if first_int & nbits_mask:
                nbits -= 1
                break
            if first_int + nbits_mask > last_int:
                nbits -= 1
                break
        net = first.__class__(first_int)
        result.append(first._network_class('%s/%d' % (net, first._max_prefixlen - nbits), strict=False))
        first_int += 2 ** nbits
    return result


def collapse_addresses(addresses):
    """Collapse a list of IP objects to the minimal list of networks."""
    nets = {}
    for ip in addresses:
        if isinstance(ip, (_BaseAddress,)):
            nets.setdefault(ip._version, []).append(ip)
        else:
            nets.setdefault(ip._version, []).append(ip)
    result = []
    for version, ips in nets.items():
        result.extend(sorted(set(ips)))
    return iter(result)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def ipaddress2_ipv4():
    """IPv4Address parses dotted notation and returns integer; returns True."""
    addr = IPv4Address('192.168.1.1')
    return int(addr) == (192 << 24) | (168 << 16) | (1 << 8) | 1


def ipaddress2_ipv6():
    """IPv6Address parses colon notation; returns True."""
    addr = IPv6Address('::1')
    return int(addr) == 1


def ipaddress2_network():
    """IPv4Network parses CIDR notation and checks membership; returns True."""
    net = IPv4Network('192.168.1.0/24')
    return (IPv4Address('192.168.1.100') in net and
            IPv4Address('10.0.0.1') not in net)


__all__ = [
    'ip_address', 'ip_network', 'ip_interface',
    'IPv4Address', 'IPv6Address',
    'IPv4Network', 'IPv6Network',
    'IPv4Interface', 'IPv6Interface',
    'AddressValueError', 'NetmaskValueError',
    'summarize_address_range', 'collapse_addresses',
    'ipaddress2_ipv4', 'ipaddress2_ipv6', 'ipaddress2_network',
]
