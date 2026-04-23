"""
theseus_ipaddress - Clean-room IP address parsing implementation.
No imports of ipaddress, socket, or any third-party libraries.
"""


class IPv4Address:
    """Represents an IPv4 address."""

    # Private address ranges (RFC 1918 and others)
    _PRIVATE_RANGES = [
        (0x0A000000, 0xFF000000),  # 10.0.0.0/8
        (0xAC100000, 0xFFF00000),  # 172.16.0.0/12
        (0xC0A80000, 0xFFFF0000),  # 192.168.0.0/16
        (0x7F000000, 0xFF000000),  # 127.0.0.0/8 (loopback)
        (0xA9FE0000, 0xFFFF0000),  # 169.254.0.0/16 (link-local)
        (0x00000000, 0xFF000000),  # 0.0.0.0/8
        (0xE0000000, 0xF0000000),  # 224.0.0.0/4 (multicast)
        (0xF0000000, 0xF0000000),  # 240.0.0.0/4 (reserved)
        (0xC0000200, 0xFFFFFF00),  # 192.0.2.0/24 (TEST-NET-1)
        (0xC6336400, 0xFFFFFF00),  # 198.51.100.0/24 (TEST-NET-2)
        (0xCB007100, 0xFFFFFF00),  # 203.0.113.0/24 (TEST-NET-3)
        (0xC6120000, 0xFFFE0000),  # 198.18.0.0/15 (benchmarking)
        (0xFFFFFFFF, 0xFFFFFFFF),  # 255.255.255.255
    ]

    def __init__(self, address):
        if isinstance(address, int):
            if not (0 <= address <= 0xFFFFFFFF):
                raise ValueError(f"IPv4 address integer out of range: {address}")
            self._ip_int = address
            self._address_str = self._int_to_str(address)
        elif isinstance(address, bytes):
            if len(address) != 4:
                raise ValueError(f"IPv4 address bytes must be 4 bytes, got {len(address)}")
            self._ip_int = (address[0] << 24) | (address[1] << 16) | (address[2] << 8) | address[3]
            self._address_str = self._int_to_str(self._ip_int)
        elif isinstance(address, str):
            self._address_str = address.strip()
            self._ip_int = self._parse_str(self._address_str)
        else:
            raise TypeError(f"Expected str, bytes, or int, got {type(address)}")

    def _parse_str(self, address):
        parts = address.split('.')
        if len(parts) != 4:
            raise ValueError(f"Invalid IPv4 address: {address!r}")
        result = 0
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Invalid IPv4 address component: {part!r}")
            octet = int(part)
            if octet < 0 or octet > 255:
                raise ValueError(f"IPv4 address octet out of range: {octet}")
            result = (result << 8) | octet
        return result

    def _int_to_str(self, ip_int):
        return '.'.join([
            str((ip_int >> 24) & 0xFF),
            str((ip_int >> 16) & 0xFF),
            str((ip_int >> 8) & 0xFF),
            str(ip_int & 0xFF),
        ])

    @property
    def packed(self):
        """Return the address as 4 bytes in network (big-endian) order."""
        return bytes([
            (self._ip_int >> 24) & 0xFF,
            (self._ip_int >> 16) & 0xFF,
            (self._ip_int >> 8) & 0xFF,
            self._ip_int & 0xFF,
        ])

    @property
    def is_private(self):
        """Return True if the address is in a private/reserved range."""
        for network_int, mask_int in self._PRIVATE_RANGES:
            if (self._ip_int & mask_int) == network_int:
                return True
        return False

    @property
    def is_loopback(self):
        """Return True if this is a loopback address."""
        return (self._ip_int & 0xFF000000) == 0x7F000000

    @property
    def is_multicast(self):
        """Return True if this is a multicast address."""
        return (self._ip_int & 0xF0000000) == 0xE0000000

    @property
    def is_link_local(self):
        """Return True if this is a link-local address."""
        return (self._ip_int & 0xFFFF0000) == 0xA9FE0000

    @property
    def is_unspecified(self):
        """Return True if this is the unspecified address (0.0.0.0)."""
        return self._ip_int == 0

    @property
    def is_reserved(self):
        """Return True if this is a reserved address."""
        return (self._ip_int & 0xF0000000) == 0xF0000000

    def __int__(self):
        return self._ip_int

    def __str__(self):
        return self._address_str

    def __repr__(self):
        return f"IPv4Address('{self._address_str}')"

    def __eq__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip_int == other._ip_int
        return NotImplemented

    def __hash__(self):
        return hash(self._ip_int)

    def __lt__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip_int < other._ip_int
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip_int <= other._ip_int
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip_int > other._ip_int
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, IPv4Address):
            return self._ip_int >= other._ip_int
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, int):
            return IPv4Address(self._ip_int + other)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, int):
            return IPv4Address(self._ip_int - other)
        if isinstance(other, IPv4Address):
            return self._ip_int - other._ip_int
        return NotImplemented


class IPv4Network:
    """Represents an IPv4 network."""

    def __init__(self, address, strict=True):
        if isinstance(address, str):
            address = address.strip()
            if '/' in address:
                addr_str, prefix_str = address.rsplit('/', 1)
                # Check if prefix is a mask or prefix length
                if '.' in prefix_str:
                    # It's a netmask
                    mask_addr = IPv4Address(prefix_str)
                    self._prefixlen = self._mask_to_prefixlen(int(mask_addr))
                else:
                    if not prefix_str.isdigit():
                        raise ValueError(f"Invalid prefix length: {prefix_str!r}")
                    self._prefixlen = int(prefix_str)
                    if self._prefixlen < 0 or self._prefixlen > 32:
                        raise ValueError(f"Prefix length out of range: {self._prefixlen}")
                host_addr = IPv4Address(addr_str)
            else:
                host_addr = IPv4Address(address)
                self._prefixlen = 32

            self._netmask_int = self._prefixlen_to_mask(self._prefixlen)
            network_int = int(host_addr) & self._netmask_int

            if strict and network_int != int(host_addr):
                raise ValueError(
                    f"Host bits set in {address!r}. "
                    f"Did you mean {self._int_to_str(network_int)}/{self._prefixlen}?"
                )

            self._network_int = network_int
        elif isinstance(address, tuple):
            # (IPv4Address, prefixlen) or (int, prefixlen)
            addr, prefixlen = address
            if isinstance(addr, IPv4Address):
                addr_int = int(addr)
            else:
                addr_int = addr
            self._prefixlen = prefixlen
            self._netmask_int = self._prefixlen_to_mask(self._prefixlen)
            self._network_int = addr_int & self._netmask_int
        else:
            raise TypeError(f"Expected str or tuple, got {type(address)}")

    def _prefixlen_to_mask(self, prefixlen):
        if prefixlen == 0:
            return 0
        return ((1 << prefixlen) - 1) << (32 - prefixlen)

    def _mask_to_prefixlen(self, mask_int):
        # Validate it's a valid contiguous mask
        if mask_int == 0:
            return 0
        # Count leading ones
        count = 0
        for i in range(31, -1, -1):
            if mask_int & (1 << i):
                count += 1
            else:
                break
        # Verify no ones after the zeros
        expected = self._prefixlen_to_mask(count)
        if expected != mask_int:
            raise ValueError(f"Invalid netmask: {self._int_to_str(mask_int)}")
        return count

    def _int_to_str(self, ip_int):
        return '.'.join([
            str((ip_int >> 24) & 0xFF),
            str((ip_int >> 16) & 0xFF),
            str((ip_int >> 8) & 0xFF),
            str(ip_int & 0xFF),
        ])

    @property
    def network_address(self):
        """Return the network address."""
        return IPv4Address(self._network_int)

    @property
    def broadcast_address(self):
        """Return the broadcast address."""
        broadcast_int = self._network_int | (~self._netmask_int & 0xFFFFFFFF)
        return IPv4Address(broadcast_int)

    @property
    def prefixlen(self):
        """Return the prefix length."""
        return self._prefixlen

    @property
    def netmask(self):
        """Return the netmask."""
        return IPv4Address(self._netmask_int)

    @property
    def hostmask(self):
        """Return the host mask (inverse of netmask)."""
        return IPv4Address(~self._netmask_int & 0xFFFFFFFF)

    @property
    def num_addresses(self):
        """Return the total number of addresses in this network."""
        return 1 << (32 - self._prefixlen)

    def __contains__(self, address):
        if isinstance(address, IPv4Address):
            return (int(address) & self._netmask_int) == self._network_int
        if isinstance(address, str):
            return (int(IPv4Address(address)) & self._netmask_int) == self._network_int
        return False

    def __iter__(self):
        """Iterate over all addresses in the network."""
        broadcast_int = self._network_int | (~self._netmask_int & 0xFFFFFFFF)
        current = self._network_int
        while current <= broadcast_int:
            yield IPv4Address(current)
            current += 1

    def hosts(self):
        """Iterate over usable host addresses (excludes network and broadcast)."""
        if self._prefixlen >= 31:
            # /31 and /32 networks - yield all addresses
            yield from self
        else:
            broadcast_int = self._network_int | (~self._netmask_int & 0xFFFFFFFF)
            current = self._network_int + 1
            while current < broadcast_int:
                yield IPv4Address(current)
                current += 1

    def overlaps(self, other):
        """Return True if this network overlaps with other."""
        if not isinstance(other, IPv4Network):
            raise TypeError(f"Expected IPv4Network, got {type(other)}")
        return (
            other.network_address in self or
            other.broadcast_address in self or
            self.network_address in other or
            self.broadcast_address in other
        )

    def subnets(self, prefixlen_diff=1, new_prefix=None):
        """Divide this network into subnets."""
        if new_prefix is not None:
            if new_prefix < self._prefixlen:
                raise ValueError("new_prefix must be longer than current prefix")
            prefixlen_diff = new_prefix - self._prefixlen
        new_prefixlen = self._prefixlen + prefixlen_diff
        if new_prefixlen > 32:
            raise ValueError("Prefix length too long")
        count = 1 << prefixlen_diff
        subnet_size = self.num_addresses // count
        for i in range(count):
            subnet_int = self._network_int + i * subnet_size
            yield IPv4Network((subnet_int, new_prefixlen))

    def supernet(self, prefixlen_diff=1, new_prefix=None):
        """Return the supernet of this network."""
        if new_prefix is not None:
            if new_prefix > self._prefixlen:
                raise ValueError("new_prefix must be shorter than current prefix")
            prefixlen_diff = self._prefixlen - new_prefix
        new_prefixlen = self._prefixlen - prefixlen_diff
        if new_prefixlen < 0:
            raise ValueError("Prefix length too short")
        new_mask = self._prefixlen_to_mask(new_prefixlen)
        new_network_int = self._network_int & new_mask
        return IPv4Network((new_network_int, new_prefixlen))

    def __str__(self):
        return f"{self._int_to_str(self._network_int)}/{self._prefixlen}"

    def __repr__(self):
        return f"IPv4Network('{self}')"

    def __eq__(self, other):
        if isinstance(other, IPv4Network):
            return (self._network_int == other._network_int and
                    self._prefixlen == other._prefixlen)
        return NotImplemented

    def __hash__(self):
        return hash((self._network_int, self._prefixlen))

    def __lt__(self, other):
        if isinstance(other, IPv4Network):
            if self._network_int != other._network_int:
                return self._network_int < other._network_int
            return self._prefixlen < other._prefixlen
        return NotImplemented


# --- Public API functions ---

def parse_v4(address_str):
    """
    Parse an IPv4 address string and return True if valid.
    
    Returns True if the address string is a valid IPv4 address,
    raises ValueError if invalid.
    """
    try:
        IPv4Address(address_str)
        return True
    except (ValueError, TypeError):
        return False


def is_private(address_str):
    """
    Return True if the given IPv4 address string is a private address.
    """
    addr = IPv4Address(address_str)
    return addr.is_private


def network_prefix(cidr_str):
    """
    Return the prefix length of the given CIDR network string.
    """
    net = IPv4Network(cidr_str)
    return net.prefixlen


def packed(address_str):
    """
    Return the packed bytes representation of the given IPv4 address string.
    """
    addr = IPv4Address(address_str)
    return addr.packed


def is_loopback(address_str):
    """
    Return True if the given IPv4 address string is a loopback address.
    """
    addr = IPv4Address(address_str)
    return addr.is_loopback


def is_multicast(address_str):
    """
    Return True if the given IPv4 address string is a multicast address.
    """
    addr = IPv4Address(address_str)
    return addr.is_multicast


def is_link_local(address_str):
    """
    Return True if the given IPv4 address string is a link-local address.
    """
    addr = IPv4Address(address_str)
    return addr.is_link_local


def network_contains(cidr_str, address_str):
    """
    Return True if the given CIDR network contains the given address.
    """
    net = IPv4Network(cidr_str)
    addr = IPv4Address(address_str)
    return addr in net


def network_broadcast(cidr_str):
    """
    Return the broadcast address of the given CIDR network as a string.
    """
    net = IPv4Network(cidr_str)
    return str(net.broadcast_address)


def network_netmask(cidr_str):
    """
    Return the netmask of the given CIDR network as a string.
    """
    net = IPv4Network(cidr_str)
    return str(net.netmask)


# Keep old names as aliases for compatibility
def ipaddress_parse_v4():
    addr = IPv4Address('192.168.1.1')
    return addr.packed == b'\xc0\xa8\x01\x01'


def ipaddress_is_private():
    """Test: IPv4Address('192.168.1.1').is_private == True"""
    addr = IPv4Address('192.168.1.1')
    return addr.is_private


def ipaddress_network_prefix():
    """Test: IPv4Network('192.168.1.0/24').prefixlen == 24"""
    return network_prefix('192.168.1.0/24')