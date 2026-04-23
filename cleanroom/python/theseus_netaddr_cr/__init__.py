"""
theseus_netaddr_cr - Clean-room network address utilities (IPv4Network/IPv6Network).
No import of ipaddress or any third-party library.
"""


def _ipv4_str_to_int(addr_str):
    """Convert dotted-decimal IPv4 string to integer."""
    parts = addr_str.strip().split('.')
    if len(parts) != 4:
        raise ValueError(f"Invalid IPv4 address: {addr_str!r}")
    result = 0
    for part in parts:
        octet = int(part)
        if octet < 0 or octet > 255:
            raise ValueError(f"Invalid IPv4 octet: {part!r}")
        result = (result << 8) | octet
    return result


def _ipv4_int_to_str(addr_int):
    """Convert integer to dotted-decimal IPv4 string."""
    if addr_int < 0 or addr_int > 0xFFFFFFFF:
        raise ValueError(f"Invalid IPv4 integer: {addr_int}")
    return '.'.join([
        str((addr_int >> 24) & 0xFF),
        str((addr_int >> 16) & 0xFF),
        str((addr_int >> 8) & 0xFF),
        str(addr_int & 0xFF),
    ])


def _ipv6_str_to_int(addr_str):
    """Convert IPv6 string to 128-bit integer."""
    addr_str = addr_str.strip()

    # Handle embedded IPv4 in IPv6 (e.g., ::ffff:192.168.1.1)
    # Check if last part looks like IPv4
    def _maybe_ipv4_tail(s):
        parts = s.split(':')
        last = parts[-1]
        if '.' in last:
            # embedded IPv4
            ipv4_int = _ipv4_str_to_int(last)
            ipv4_high = (ipv4_int >> 16) & 0xFFFF
            ipv4_low = ipv4_int & 0xFFFF
            parts[-1] = format(ipv4_high, 'x') + ':' + format(ipv4_low, 'x')
            return ':'.join(parts)
        return s

    addr_str = _maybe_ipv4_tail(addr_str)

    if '::' in addr_str:
        left, right = addr_str.split('::', 1)
        left_groups = [g for g in left.split(':') if g] if left else []
        right_groups = [g for g in right.split(':') if g] if right else []
        missing = 8 - len(left_groups) - len(right_groups)
        groups = left_groups + ['0'] * missing + right_groups
    else:
        groups = addr_str.split(':')

    if len(groups) != 8:
        raise ValueError(f"Invalid IPv6 address: {addr_str!r}")

    result = 0
    for g in groups:
        result = (result << 16) | int(g, 16)
    return result


def _ipv6_int_to_str(addr_int):
    """Convert 128-bit integer to compressed IPv6 string."""
    if addr_int < 0 or addr_int > (2**128 - 1):
        raise ValueError(f"Invalid IPv6 integer: {addr_int}")

    groups = []
    for i in range(7, -1, -1):
        groups.append((addr_int >> (i * 16)) & 0xFFFF)

    # Find longest run of zeros for :: compression
    best_start = -1
    best_len = 0
    cur_start = -1
    cur_len = 0
    for i, g in enumerate(groups):
        if g == 0:
            if cur_start == -1:
                cur_start = i
                cur_len = 1
            else:
                cur_len += 1
            if cur_len > best_len:
                best_len = cur_len
                best_start = cur_start
        else:
            cur_start = -1
            cur_len = 0

    if best_len < 2:
        return ':'.join(format(g, 'x') for g in groups)

    left = ':'.join(format(g, 'x') for g in groups[:best_start])
    right = ':'.join(format(g, 'x') for g in groups[best_start + best_len:])
    return left + '::' + right


class IPv4Address:
    """Represents a single IPv4 address."""

    def __init__(self, address):
        if isinstance(address, int):
            if address < 0 or address > 0xFFFFFFFF:
                raise ValueError(f"IPv4 integer out of range: {address}")
            self._ip = address
            self._str = _ipv4_int_to_str(address)
        elif isinstance(address, str):
            self._ip = _ipv4_str_to_int(address)
            self._str = _ipv4_int_to_str(self._ip)
        elif isinstance(address, IPv4Address):
            self._ip = address._ip
            self._str = address._str
        else:
            raise TypeError(f"Cannot create IPv4Address from {type(address)}")

    @property
    def packed(self):
        return self._ip.to_bytes(4, 'big')

    def __int__(self):
        return self._ip

    def __str__(self):
        return self._str

    def __repr__(self):
        return f"IPv4Address('{self._str}')"

    def __eq__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip == other._ip
        if isinstance(other, str):
            try:
                return self._ip == _ipv4_str_to_int(other)
            except ValueError:
                return False
        if isinstance(other, int):
            return self._ip == other
        return NotImplemented

    def __hash__(self):
        return hash(self._ip)

    def __lt__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip < other._ip
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip <= other._ip
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip > other._ip
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip >= other._ip
        return NotImplemented


class IPv6Address:
    """Represents a single IPv6 address."""

    def __init__(self, address):
        if isinstance(address, int):
            if address < 0 or address > (2**128 - 1):
                raise ValueError(f"IPv6 integer out of range: {address}")
            self._ip = address
            self._str = _ipv6_int_to_str(address)
        elif isinstance(address, str):
            self._ip = _ipv6_str_to_int(address)
            self._str = _ipv6_int_to_str(self._ip)
        elif isinstance(address, IPv6Address):
            self._ip = address._ip
            self._str = address._str
        else:
            raise TypeError(f"Cannot create IPv6Address from {type(address)}")

    def __int__(self):
        return self._ip

    def __str__(self):
        return self._str

    def __repr__(self):
        return f"IPv6Address('{self._str}')"

    def __eq__(self, other):
        if isinstance(other, IPv6Address):
            return self._ip == other._ip
        if isinstance(other, str):
            try:
                return self._ip == _ipv6_str_to_int(other)
            except ValueError:
                return False
        if isinstance(other, int):
            return self._ip == other
        return NotImplemented

    def __hash__(self):
        return hash(self._ip)

    def __lt__(self, other):
        if isinstance(other, IPv6Address):
            return self._ip < other._ip
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, IPv6Address):
            return self._ip <= other._ip
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, IPv6Address):
            return self._ip > other._ip
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, IPv6Address):
            return self._ip >= other._ip
        return NotImplemented


class IPv4Network:
    """
    Represents an IPv4 network (CIDR notation).

    Example: IPv4Network('192.168.1.0/24')
    """

    def __init__(self, address, strict=True):
        if isinstance(address, str):
            if '/' in address:
                addr_part, prefix_part = address.split('/', 1)
                # Check if prefix is a dotted-decimal mask or integer
                if '.' in prefix_part:
                    # Netmask in dotted-decimal form
                    mask_int = _ipv4_str_to_int(prefix_part)
                    prefixlen = _mask_to_prefixlen(mask_int, 32)
                else:
                    prefixlen = int(prefix_part)
            else:
                addr_part = address
                prefixlen = 32

            if prefixlen < 0 or prefixlen > 32:
                raise ValueError(f"Invalid prefix length: {prefixlen}")

            addr_int = _ipv4_str_to_int(addr_part)
            mask = _prefixlen_to_mask(prefixlen, 32)

            if strict and (addr_int & ~mask) != 0:
                raise ValueError(
                    f"Host bits set in {address!r}. "
                    f"Use strict=False to suppress this error."
                )

            self._network_int = addr_int & mask
            self._prefixlen = prefixlen
            self._mask = mask

        elif isinstance(address, (list, tuple)) and len(address) == 2:
            addr_int, prefixlen = address
            if prefixlen < 0 or prefixlen > 32:
                raise ValueError(f"Invalid prefix length: {prefixlen}")
            mask = _prefixlen_to_mask(prefixlen, 32)
            self._network_int = addr_int & mask
            self._prefixlen = prefixlen
            self._mask = mask
        else:
            raise TypeError(f"Cannot create IPv4Network from {type(address)}")

    @property
    def prefixlen(self):
        return self._prefixlen

    @property
    def netmask(self):
        return IPv4Address(self._mask)

    @property
    def network_address(self):
        return IPv4Address(self._network_int)

    @property
    def broadcast_address(self):
        # All host bits set
        host_mask = ~self._mask & 0xFFFFFFFF
        return IPv4Address(self._network_int | host_mask)

    @property
    def num_addresses(self):
        return 2 ** (32 - self._prefixlen)

    def __contains__(self, address):
        if isinstance(address, IPv4Address):
            addr_int = address._ip
        elif isinstance(address, str):
            addr_int = _ipv4_str_to_int(address)
        elif isinstance(address, int):
            addr_int = address
        else:
            return False
        return (addr_int & self._mask) == self._network_int

    def __str__(self):
        return f"{_ipv4_int_to_str(self._network_int)}/{self._prefixlen}"

    def __repr__(self):
        return f"IPv4Network('{self}')"

    def __eq__(self, other):
        if isinstance(other, IPv4Network):
            return (self._network_int == other._network_int and
                    self._prefixlen == other._prefixlen)
        return NotImplemented

    def __hash__(self):
        return hash((self._network_int, self._prefixlen))

    def __iter__(self):
        """Iterate over all addresses in the network."""
        start = self._network_int
        end = self._network_int | (~self._mask & 0xFFFFFFFF)
        current = start
        while current <= end:
            yield IPv4Address(current)
            current += 1

    def hosts(self):
        """Iterate over usable host addresses (excludes network and broadcast)."""
        if self._prefixlen >= 31:
            # /31 and /32 have no traditional network/broadcast
            yield from self
        else:
            start = self._network_int + 1
            end = (self._network_int | (~self._mask & 0xFFFFFFFF)) - 1
            current = start
            while current <= end:
                yield IPv4Address(current)
                current += 1

    def overlaps(self, other):
        """Return True if this network overlaps with other."""
        if not isinstance(other, IPv4Network):
            raise TypeError(f"Expected IPv4Network, got {type(other)}")
        return (other.network_address in self or
                other.broadcast_address in self or
                self.network_address in other or
                self.broadcast_address in other)

    def subnet_of(self, other):
        """Return True if this network is a subnet of other."""
        if not isinstance(other, IPv4Network):
            raise TypeError(f"Expected IPv4Network, got {type(other)}")
        return (other._network_int == (self._network_int & other._mask) and
                self._prefixlen >= other._prefixlen)

    def supernet_of(self, other):
        """Return True if this network is a supernet of other."""
        if not isinstance(other, IPv4Network):
            raise TypeError(f"Expected IPv4Network, got {type(other)}")
        return other.subnet_of(self)

    def subnets(self, prefixlen_diff=1, new_prefix=None):
        """Divide this network into subnets."""
        if new_prefix is not None:
            if new_prefix < self._prefixlen:
                raise ValueError("new_prefix must be longer than current prefix")
            prefixlen_diff = new_prefix - self._prefixlen
        new_prefixlen = self._prefixlen + prefixlen_diff
        if new_prefixlen > 32:
            raise ValueError("Prefix length exceeds 32")
        new_mask = _prefixlen_to_mask(new_prefixlen, 32)
        start = self._network_int
        end = self._network_int | (~self._mask & 0xFFFFFFFF)
        step = 2 ** (32 - new_prefixlen)
        current = start
        while current <= end:
            yield IPv4Network((current, new_prefixlen), strict=False) if False else _make_ipv4_network(current, new_prefixlen)
            current += step

    def supernet(self, prefixlen_diff=1, new_prefix=None):
        """Return the supernet of this network."""
        if new_prefix is not None:
            if new_prefix > self._prefixlen:
                raise ValueError("new_prefix must be shorter than current prefix")
            prefixlen_diff = self._prefixlen - new_prefix
        new_prefixlen = self._prefixlen - prefixlen_diff
        if new_prefixlen < 0:
            raise ValueError("Prefix length below 0")
        new_mask = _prefixlen_to_mask(new_prefixlen, 32)
        new_network = self._network_int & new_mask
        return _make_ipv4_network(new_network, new_prefixlen)

    def with_prefixlen(self):
        return str(self)

    def compressed(self):
        return str(self)


def _make_ipv4_network(network_int, prefixlen):
    """Helper to create IPv4Network from integer and prefixlen."""
    net = IPv4Network.__new__(IPv4Network)
    net._network_int = network_int
    net._prefixlen = prefixlen
    net._mask = _prefixlen_to_mask(prefixlen, 32)
    return net


class IPv6Network:
    """
    Represents an IPv6 network (CIDR notation).

    Example: IPv6Network('::1/128')
    """

    def __init__(self, address, strict=True):
        if isinstance(address, str):
            if '/' in address:
                addr_part, prefix_part = address.split('/', 1)
                prefixlen = int(prefix_part)
            else:
                addr_part = address
                prefixlen = 128

            if prefixlen < 0 or prefixlen > 128:
                raise ValueError(f"Invalid prefix length: {prefixlen}")

            addr_int = _ipv6_str_to_int(addr_part)
            mask = _prefixlen_to_mask(prefixlen, 128)

            if strict and (addr_int & ~mask) != 0:
                raise ValueError(
                    f"Host bits set in {address!r}. "
                    f"Use strict=False to suppress this error."
                )

            self._network_int = addr_int & mask
            self._prefixlen = prefixlen
            self._mask = mask

        elif isinstance(address, (list, tuple)) and len(address) == 2:
            addr_int, prefixlen = address
            if prefixlen < 0 or prefixlen > 128:
                raise ValueError(f"Invalid prefix length: {prefixlen}")
            mask = _prefixlen_to_mask(prefixlen, 128)
            self._network_int = addr_int & mask
            self._prefixlen = prefixlen
            self._mask = mask
        else:
            raise TypeError(f"Cannot create IPv6Network from {type(address)}")

    @property
    def prefixlen(self):
        return self._prefixlen

    @property
    def netmask(self):
        return IPv6Address(self._mask)

    @property
    def network_address(self):
        return IPv6Address(self._network_int)

    @property
    def broadcast_address(self):
        host_mask = ~self._mask & ((1 << 128) - 1)
        return IPv6Address(self._network_int | host_mask)

    @property
    def num_addresses(self):
        return 2 ** (128 - self._prefixlen)

    def __contains__(self, address):
        if isinstance(address, IPv6Address):
            addr_int = address._ip
        elif isinstance(address, str):
            addr_int = _ipv6_str_to_int(address)
        elif isinstance(address, int):
            addr_int = address
        else:
            return False
        return (addr_int & self._mask) == self._network_int

    def __str__(self):
        return f"{_ipv6_int_to_str(self._network_int)}/{self._prefixlen}"

    def __repr__(self):
        return f"IPv6Network('{self}')"

    def __eq__(self, other):
        if isinstance(other, IPv6Network):
            return (self._network_int == other._network_int and
                    self._prefixlen == other._prefixlen)
        return NotImplemented

    def __hash__(self):
        return hash((self._network_int, self._prefixlen))

    def overlaps(self, other):
        if not isinstance(other, IPv6Network):
            raise TypeError(f"Expected IPv6Network, got {type(other)}")
        return (other.network_address in self or
                other.broadcast_address in self or
                self.network_address in other or
                self.broadcast_address in other)

    def subnet_of(self, other):
        if not isinstance(other, IPv6Network):
            raise TypeError(f"Expected IPv6Network, got {type(other)}")
        return (other._network_int == (self._network_int & other._mask) and
                self._prefixlen >= other._prefixlen)

    def supernet_of(self, other):
        if not isinstance(other, IPv6Network):
            raise TypeError(f"Expected IPv6Network, got {type(other)}")
        return other.subnet_of(self)


def _prefixlen_to_mask(prefixlen, bits):
    """Convert prefix length to integer mask."""
    if prefixlen == 0:
        return 0
    if prefixlen == bits:
        return (1 << bits) - 1
    return ((1 << bits) - 1) ^ ((1 << (bits - prefixlen)) - 1)


def _mask_to_prefixlen(mask_int, bits):
    """Convert integer mask to prefix length."""
    # Validate it's a valid contiguous mask
    if mask_int == 0:
        return 0
    # Count leading ones
    count = 0
    for i in range(bits - 1, -1, -1):
        if mask_int & (1 << i):
            count += 1
        else:
            break
    # Verify the rest are zeros
    expected = _prefixlen_to_mask(count, bits)
    if expected != mask_int:
        raise ValueError(f"Invalid netmask: {mask_int}")
    return count


# ─── Invariant functions ────────────────────────────────────────────────────

def netaddr_v4_prefixlen():
    """Returns the prefix length of IPv4Network('10.0.0.0/8'), which is 8."""
    net = IPv4Network('10.0.0.0/8')
    return net.prefixlen


def netaddr_v4_broadcast():
    """Returns the broadcast address of IPv4Network('192.168.1.0/24') as string."""
    net = IPv4Network('192.168.1.0/24')
    return str(net.broadcast_address)


def netaddr_v4_contains():
    """Returns True if IPv4Address('10.0.0.5') is in IPv4Network('10.0.0.0/8')."""
    addr = IPv4Address('10.0.0.5')
    net = IPv4Network('10.0.0.0/8')
    return addr in net


__all__ = [
    'IPv4Address',
    'IPv6Address',
    'IPv4Network',
    'IPv6Network',
    'netaddr_v4_prefixlen',
    'netaddr_v4_broadcast',
    'netaddr_v4_contains',
]