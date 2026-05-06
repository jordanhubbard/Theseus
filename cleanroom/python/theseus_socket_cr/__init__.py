"""
theseus_socket_cr - Clean-room Python socket module.

Implemented from scratch using only Python standard library built-ins.
Does NOT import the `socket` package.
"""

import os as _os
import struct as _struct
import re as _re


# ---------------------------------------------------------------------------
# Address family constants (POSIX values)
# ---------------------------------------------------------------------------
AF_UNSPEC = 0
AF_UNIX = 1
AF_INET = 2
AF_INET6 = 10  # Linux value; constant identity is what matters here

# Socket type constants
SOCK_STREAM = 1
SOCK_DGRAM = 2
SOCK_RAW = 3
SOCK_RDM = 4
SOCK_SEQPACKET = 5

# Protocol constants
IPPROTO_IP = 0
IPPROTO_ICMP = 1
IPPROTO_TCP = 6
IPPROTO_UDP = 17
IPPROTO_IPV6 = 41

# Special addresses
INADDR_ANY = 0x00000000
INADDR_BROADCAST = 0xFFFFFFFF
INADDR_LOOPBACK = 0x7F000001

# Shutdown flags
SHUT_RD = 0
SHUT_WR = 1
SHUT_RDWR = 2

# Socket option levels and names (subset)
SOL_SOCKET = 1
SO_REUSEADDR = 2
SO_KEEPALIVE = 9
SO_BROADCAST = 6


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class error(OSError):
    """Base socket error class (mirrors socket.error)."""
    pass


class herror(error):
    """Address-related error."""
    pass


class gaierror(error):
    """getaddrinfo-related error."""
    pass


class timeout(error):
    """Timeout error."""
    pass


# ---------------------------------------------------------------------------
# Hostname
# ---------------------------------------------------------------------------
def gethostname():
    """Return the host name of the current machine as a string."""
    # Prefer os.uname() on POSIX systems
    try:
        u = _os.uname()
        name = u.nodename
        if name:
            return name
    except (AttributeError, OSError):
        pass

    # Fall back to /etc/hostname
    try:
        with open("/etc/hostname", "r") as f:
            name = f.read().strip()
            if name:
                return name
    except (OSError, IOError):
        pass

    # Environment fallbacks (Windows uses COMPUTERNAME)
    for env in ("HOSTNAME", "COMPUTERNAME", "HOST"):
        v = _os.environ.get(env)
        if v:
            return v

    return "localhost"


def gethostbyname(hostname):
    """Resolve a hostname to a dotted-quad IPv4 string (very limited)."""
    if hostname in ("localhost", ""):
        return "127.0.0.1"
    # If already a dotted IPv4, return as-is after validation
    try:
        inet_aton(hostname)
        return hostname
    except error:
        pass
    if hostname == gethostname():
        return "127.0.0.1"
    raise gaierror("name resolution not supported in clean-room module")


# ---------------------------------------------------------------------------
# Byte order helpers (network is big-endian)
# ---------------------------------------------------------------------------
def htons(x):
    """Convert 16-bit host integer to network byte order."""
    if x < 0 or x > 0xFFFF:
        raise OverflowError("htons argument out of range")
    return _struct.unpack(">H", _struct.pack("=H", x))[0]


def ntohs(x):
    """Convert 16-bit network integer to host byte order."""
    if x < 0 or x > 0xFFFF:
        raise OverflowError("ntohs argument out of range")
    return _struct.unpack("=H", _struct.pack(">H", x))[0]


def htonl(x):
    """Convert 32-bit host integer to network byte order."""
    if x < 0 or x > 0xFFFFFFFF:
        raise OverflowError("htonl argument out of range")
    return _struct.unpack(">I", _struct.pack("=I", x))[0]


def ntohl(x):
    """Convert 32-bit network integer to host byte order."""
    if x < 0 or x > 0xFFFFFFFF:
        raise OverflowError("ntohl argument out of range")
    return _struct.unpack("=I", _struct.pack(">I", x))[0]


# ---------------------------------------------------------------------------
# IPv4 address conversion
# ---------------------------------------------------------------------------
_IPV4_RE = _re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")


def inet_aton(ip_string):
    """Convert a dotted-quad IPv4 string to 4-byte packed binary form."""
    if not isinstance(ip_string, str):
        raise TypeError("inet_aton expects a string")
    m = _IPV4_RE.match(ip_string)
    if not m:
        raise error("illegal IP address string passed to inet_aton")
    parts = []
    for g in m.groups():
        v = int(g)
        if v > 255:
            raise error("illegal IP address string passed to inet_aton")
        parts.append(v)
    return bytes(parts)


def inet_ntoa(packed_ip):
    """Convert a 4-byte packed IPv4 address to a dotted-quad string."""
    if not isinstance(packed_ip, (bytes, bytearray)):
        raise TypeError("inet_ntoa expects bytes")
    if len(packed_ip) != 4:
        raise error("packed IP wrong length for inet_ntoa")
    return "%d.%d.%d.%d" % tuple(packed_ip)


# ---------------------------------------------------------------------------
# IPv6 address conversion
# ---------------------------------------------------------------------------
def _inet_pton6(ip_string):
    """Convert an IPv6 string to 16-byte packed binary form."""
    if not isinstance(ip_string, str):
        raise TypeError("inet_pton expects a string")
    if "::" in ip_string:
        # Split on "::" once; left and right sides each have 0..7 groups.
        if ip_string.count("::") > 1:
            raise error("illegal IPv6 address string passed to inet_pton")
        left, right = ip_string.split("::", 1)
        left_groups = left.split(":") if left else []
        right_groups = right.split(":") if right else []
        if "" in left_groups or "" in right_groups:
            raise error("illegal IPv6 address string passed to inet_pton")
        missing = 8 - (len(left_groups) + len(right_groups))
        if missing < 0:
            raise error("illegal IPv6 address string passed to inet_pton")
        groups = left_groups + ["0"] * missing + right_groups
    else:
        groups = ip_string.split(":")
        if len(groups) != 8:
            raise error("illegal IPv6 address string passed to inet_pton")

    out = bytearray()
    for g in groups:
        if not g or len(g) > 4:
            raise error("illegal IPv6 address string passed to inet_pton")
        try:
            v = int(g, 16)
        except ValueError:
            raise error("illegal IPv6 address string passed to inet_pton")
        if v < 0 or v > 0xFFFF:
            raise error("illegal IPv6 address string passed to inet_pton")
        out.append((v >> 8) & 0xFF)
        out.append(v & 0xFF)
    return bytes(out)


def _inet_ntop6(packed):
    """Convert 16-byte packed IPv6 to canonical (compressed) string form."""
    if not isinstance(packed, (bytes, bytearray)):
        raise TypeError("inet_ntop expects bytes")
    if len(packed) != 16:
        raise ValueError("invalid length of packed IP address string")
    groups = []
    for i in range(0, 16, 2):
        groups.append((packed[i] << 8) | packed[i + 1])

    # Find the longest run of zeros (length >= 2) for "::" compression.
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
        return ":".join("%x" % g for g in groups)

    left = ":".join("%x" % g for g in groups[:best_start])
    right = ":".join("%x" % g for g in groups[best_start + best_len:])
    return left + "::" + right


def inet_pton(address_family, ip_string):
    """Convert an IP address from string to packed binary form."""
    if address_family == AF_INET:
        return inet_aton(ip_string)
    if address_family == AF_INET6:
        return _inet_pton6(ip_string)
    raise error("unknown address family")


def inet_ntop(address_family, packed_ip):
    """Convert an IP address from packed binary form to string."""
    if address_family == AF_INET:
        if not isinstance(packed_ip, (bytes, bytearray)) or len(packed_ip) != 4:
            raise ValueError("invalid length of packed IP address string")
        return inet_ntoa(bytes(packed_ip))
    if address_family == AF_INET6:
        return _inet_ntop6(packed_ip)
    raise error("unknown address family")


# ---------------------------------------------------------------------------
# Invariant functions (self-tests)
# ---------------------------------------------------------------------------
def socket2_constants():
    """Verify that socket-style constants are defined with expected values."""
    # Address families
    if AF_UNSPEC != 0 or AF_UNIX != 1 or AF_INET != 2:
        return False
    # Socket types
    if SOCK_STREAM != 1 or SOCK_DGRAM != 2 or SOCK_RAW != 3:
        return False
    # Protocols
    if IPPROTO_TCP != 6 or IPPROTO_UDP != 17 or IPPROTO_ICMP != 1:
        return False
    # Special addresses
    if INADDR_ANY != 0 or INADDR_LOOPBACK != 0x7F000001:
        return False
    if INADDR_BROADCAST != 0xFFFFFFFF:
        return False
    # Shutdown flags
    if SHUT_RD != 0 or SHUT_WR != 1 or SHUT_RDWR != 2:
        return False
    # Byte-order helpers should round-trip (works on any endianness)
    if ntohs(htons(0x1234)) != 0x1234:
        return False
    if ntohl(htonl(0xDEADBEEF)) != 0xDEADBEEF:
        return False
    if htons(0) != 0 or htonl(0) != 0:
        return False
    if ntohs(0xFFFF) != 0xFFFF or ntohl(0xFFFFFFFF) != 0xFFFFFFFF:
        return False
    return True


def socket2_gethostname():
    """Verify that gethostname() returns a non-empty string."""
    name = gethostname()
    if not isinstance(name, str):
        return False
    if len(name) == 0:
        return False
    # Hostname should not contain whitespace or null bytes
    if any(c.isspace() or c == "\x00" for c in name):
        return False
    return True


def socket2_addr():
    """Verify IPv4 and IPv6 address conversion round-trips."""
    # IPv4 round-trip cases
    cases_v4 = [
        ("0.0.0.0", b"\x00\x00\x00\x00"),
        ("127.0.0.1", b"\x7f\x00\x00\x01"),
        ("255.255.255.255", b"\xff\xff\xff\xff"),
        ("192.168.1.1", b"\xc0\xa8\x01\x01"),
        ("8.8.8.8", b"\x08\x08\x08\x08"),
    ]
    for s, packed in cases_v4:
        if inet_aton(s) != packed:
            return False
        if inet_ntoa(packed) != s:
            return False
        if inet_pton(AF_INET, s) != packed:
            return False
        if inet_ntop(AF_INET, packed) != s:
            return False

    # Invalid IPv4 should raise
    for bad in ("256.0.0.1", "1.2.3", "a.b.c.d", "1.2.3.4.5", ""):
        try:
            inet_aton(bad)
        except error:
            continue
        return False

    # IPv6 round-trip cases
    if _inet_pton6("::") != b"\x00" * 16:
        return False
    if _inet_pton6("::1") != b"\x00" * 15 + b"\x01":
        return False
    full = "2001:db8:85a3:0:0:8a2e:370:7334"
    packed_full = _inet_pton6(full)
    if len(packed_full) != 16:
        return False
    # Round trip via canonical form
    canon = _inet_ntop6(packed_full)
    if _inet_pton6(canon) != packed_full:
        return False

    # ntop should compress longest zero run
    if _inet_ntop6(b"\x00" * 16) != "::":
        return False
    if _inet_ntop6(b"\x00" * 15 + b"\x01") != "::1":
        return False
    # "1::" — trailing zero run
    if _inet_ntop6(b"\x00\x01" + b"\x00" * 14) != "1::":
        return False

    # inet_pton/ntop dispatch
    if inet_pton(AF_INET6, "::1") != b"\x00" * 15 + b"\x01":
        return False
    if inet_ntop(AF_INET6, b"\x00" * 15 + b"\x01") != "::1":
        return False

    # Invalid IPv6 should raise
    for bad in ("1:::2", "gggg::", "1:2:3:4:5:6:7:8:9", ":::"):
        try:
            _inet_pton6(bad)
        except error:
            continue
        return False

    return True


__all__ = [
    # Constants
    "AF_UNSPEC", "AF_UNIX", "AF_INET", "AF_INET6",
    "SOCK_STREAM", "SOCK_DGRAM", "SOCK_RAW", "SOCK_RDM", "SOCK_SEQPACKET",
    "IPPROTO_IP", "IPPROTO_ICMP", "IPPROTO_TCP", "IPPROTO_UDP", "IPPROTO_IPV6",
    "INADDR_ANY", "INADDR_BROADCAST", "INADDR_LOOPBACK",
    "SHUT_RD", "SHUT_WR", "SHUT_RDWR",
    "SOL_SOCKET", "SO_REUSEADDR", "SO_KEEPALIVE", "SO_BROADCAST",
    # Exceptions
    "error", "herror", "gaierror", "timeout",
    # Functions
    "gethostname", "gethostbyname",
    "htons", "ntohs", "htonl", "ntohl",
    "inet_aton", "inet_ntoa", "inet_pton", "inet_ntop",
    # Invariants
    "socket2_constants", "socket2_gethostname", "socket2_addr",
]