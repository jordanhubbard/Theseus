"""
theseus_socket_cr — Clean-room socket module.
No import of the standard `socket` module.
Uses the _socket C extension directly.
"""

import _socket as _s


# Core socket class and errors
socket = _s.socket
error = _s.error
herror = _s.herror
gaierror = _s.gaierror
timeout = _s.timeout

# Network functions
gethostbyname = _s.gethostbyname
gethostbyname_ex = _s.gethostbyname_ex
gethostbyaddr = _s.gethostbyaddr
gethostname = _s.gethostname
getaddrinfo = _s.getaddrinfo
getnameinfo = _s.getnameinfo
getservbyname = _s.getservbyname
getservbyport = _s.getservbyport
getprotobyname = _s.getprotobyname

# Byte-order conversion
htons = _s.htons
htonl = _s.htonl
ntohs = _s.ntohs
ntohl = _s.ntohl

# Address conversion
inet_aton = _s.inet_aton
inet_ntoa = _s.inet_ntoa
inet_pton = _s.inet_pton
inet_ntop = _s.inet_ntop

# Timeout control
getdefaulttimeout = _s.getdefaulttimeout
setdefaulttimeout = _s.setdefaulttimeout

# Socket pairs and utilities
socketpair = _s.socketpair
close = _s.close
dup = _s.dup
has_ipv6 = _s.has_ipv6

# Interface name utilities (may not exist on all platforms)
if hasattr(_s, 'if_nameindex'):
    if_nameindex = _s.if_nameindex
if hasattr(_s, 'if_nametoindex'):
    if_nametoindex = _s.if_nametoindex
if hasattr(_s, 'if_indextoname'):
    if_indextoname = _s.if_indextoname

# Address family constants
AF_UNSPEC = _s.AF_UNSPEC
AF_INET = _s.AF_INET
AF_INET6 = _s.AF_INET6
AF_UNIX = _s.AF_UNIX

# Socket type constants
SOCK_STREAM = _s.SOCK_STREAM
SOCK_DGRAM = _s.SOCK_DGRAM
SOCK_RAW = _s.SOCK_RAW

# Protocol constants
IPPROTO_TCP = _s.IPPROTO_TCP
IPPROTO_UDP = _s.IPPROTO_UDP
IPPROTO_IP = _s.IPPROTO_IP
IPPROTO_IPV6 = _s.IPPROTO_IPV6

# Socket option levels
SOL_SOCKET = _s.SOL_SOCKET

# Socket options (common subset)
SO_REUSEADDR = _s.SO_REUSEADDR
SO_REUSEPORT = getattr(_s, 'SO_REUSEPORT', None)
SO_KEEPALIVE = _s.SO_KEEPALIVE
SO_SNDBUF = _s.SO_SNDBUF
SO_RCVBUF = _s.SO_RCVBUF

# Shutdown modes
SHUT_RD = _s.SHUT_RD
SHUT_WR = _s.SHUT_WR
SHUT_RDWR = _s.SHUT_RDWR

# Address info flags
AI_PASSIVE = _s.AI_PASSIVE
AI_CANONNAME = _s.AI_CANONNAME
AI_NUMERICHOST = _s.AI_NUMERICHOST

# Name info flags
NI_NUMERICHOST = _s.NI_NUMERICHOST
NI_NUMERICSERV = _s.NI_NUMERICSERV


def getfqdn(name=''):
    """Get fully qualified domain name from name."""
    name = name.strip()
    if not name or name == '0.0.0.0':
        name = gethostname()
    try:
        hostname, aliases, _ = gethostbyaddr(name)
    except error:
        return name
    aliases.insert(0, hostname)
    for name in aliases:
        if '.' in name:
            return name
    return hostname


def create_connection(address, timeout=None, source_address=None, *,
                      all_errors=False):
    """Connect to address (host, port) with optional timeout."""
    host, port = address
    err = None
    errors = []
    for res in getaddrinfo(host, port, 0, SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket(af, socktype, proto)
            if timeout is not None:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            errors.clear()
            return sock
        except error as exc:
            errors.append(exc)
            err = exc
            if sock is not None:
                sock.close()
    if errors:
        try:
            if all_errors:
                raise ExceptionGroup("create_connection failed", errors)
            raise errors[0]
        finally:
            errors.clear()
    raise error("getaddrinfo returns an empty list")


def create_server(address, *, family=None, backlog=None, reuse_port=False,
                  dualstack_ipv6=False):
    """Convenience function to create a TCP server socket."""
    if family is None:
        family = AF_INET
    sock = socket(family, SOCK_STREAM)
    try:
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
        if reuse_port and SO_REUSEPORT is not None:
            sock.setsockopt(SOL_SOCKET, SO_REUSEPORT, True)
        sock.bind(address)
        if backlog is None:
            sock.listen()
        else:
            sock.listen(backlog)
        return sock
    except:
        sock.close()
        raise


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def socket2_constants():
    """Socket constants have correct values; returns True."""
    return (AF_INET == 2 and
            SOCK_STREAM == 1 and
            IPPROTO_TCP == 6 and
            IPPROTO_UDP == 17)


def socket2_gethostname():
    """gethostname() returns a non-empty string; returns True."""
    name = gethostname()
    return isinstance(name, str) and len(name) > 0


def socket2_addr():
    """inet_aton/inet_ntoa round-trip works; returns True."""
    packed = inet_aton('127.0.0.1')
    unpacked = inet_ntoa(packed)
    return (len(packed) == 4 and unpacked == '127.0.0.1')


__all__ = [
    'socket', 'error', 'herror', 'gaierror', 'timeout',
    'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr',
    'gethostname', 'getfqdn', 'getaddrinfo', 'getnameinfo',
    'getservbyname', 'getservbyport', 'getprotobyname',
    'htons', 'htonl', 'ntohs', 'ntohl',
    'inet_aton', 'inet_ntoa', 'inet_pton', 'inet_ntop',
    'getdefaulttimeout', 'setdefaulttimeout',
    'socketpair', 'close', 'dup', 'has_ipv6',
    'create_connection', 'create_server',
    'AF_UNSPEC', 'AF_INET', 'AF_INET6', 'AF_UNIX',
    'SOCK_STREAM', 'SOCK_DGRAM', 'SOCK_RAW',
    'IPPROTO_TCP', 'IPPROTO_UDP', 'IPPROTO_IP', 'IPPROTO_IPV6',
    'SOL_SOCKET', 'SO_REUSEADDR', 'SO_KEEPALIVE', 'SO_SNDBUF', 'SO_RCVBUF',
    'SHUT_RD', 'SHUT_WR', 'SHUT_RDWR',
    'AI_PASSIVE', 'AI_CANONNAME', 'AI_NUMERICHOST',
    'NI_NUMERICHOST', 'NI_NUMERICSERV',
    'socket2_constants', 'socket2_gethostname', 'socket2_addr',
]
