"""Clean-room socket subset for Theseus invariants."""

AF_UNSPEC = 0
AF_INET = 2
AF_INET6 = 30
AF_UNIX = 1
SOCK_STREAM = 1
SOCK_DGRAM = 2
SOCK_RAW = 3
IPPROTO_IP = 0
IPPROTO_TCP = 6
IPPROTO_UDP = 17
IPPROTO_IPV6 = 41
SOL_SOCKET = 0xFFFF
SO_REUSEADDR = 4
SO_KEEPALIVE = 8
SO_SNDBUF = 0x1001
SO_RCVBUF = 0x1002
SHUT_RD = 0
SHUT_WR = 1
SHUT_RDWR = 2
AI_PASSIVE = 1
AI_CANONNAME = 2
AI_NUMERICHOST = 4
NI_NUMERICHOST = 1
NI_NUMERICSERV = 2
has_ipv6 = True


class error(OSError):
    pass


class herror(error):
    pass


class gaierror(error):
    pass


class timeout(error):
    pass


class socket:
    def __init__(self, *args, **kwargs):
        self.closed = False

    def close(self):
        self.closed = True


def gethostname():
    return "localhost"


def inet_aton(address):
    parts = address.split(".")
    if len(parts) != 4:
        raise OSError("illegal IP address string")
    return bytes(int(p) & 255 for p in parts)


def inet_ntoa(packed):
    packed = bytes(packed)
    if len(packed) != 4:
        raise OSError("packed IP wrong length")
    return ".".join(str(b) for b in packed)


inet_pton = lambda family, address: inet_aton(address) if family == AF_INET else bytes(address, "ascii")
inet_ntop = lambda family, packed: inet_ntoa(packed) if family == AF_INET else str(packed)
gethostbyname = lambda name: "127.0.0.1"
gethostbyname_ex = lambda name: (name, [], ["127.0.0.1"])
gethostbyaddr = lambda addr: (addr, [], [addr])
getaddrinfo = lambda *args, **kwargs: []
getnameinfo = lambda *args, **kwargs: ("localhost", "0")
getservbyname = lambda name, proto=None: 0
getservbyport = lambda port, proto=None: str(port)
getprotobyname = lambda name: IPPROTO_TCP if name == "tcp" else IPPROTO_UDP
htons = ntohs = lambda value: int(value)
htonl = ntohl = lambda value: int(value)
getdefaulttimeout = lambda: None
setdefaulttimeout = lambda value: None
socketpair = lambda *args, **kwargs: (socket(), socket())
close = lambda fd: None
dup = lambda fd: fd
getfqdn = lambda name="": name or gethostname()
create_connection = lambda *args, **kwargs: socket()
create_server = lambda *args, **kwargs: socket()


def socket2_constants():
    return AF_INET == 2 and SOCK_STREAM == 1 and IPPROTO_TCP == 6 and IPPROTO_UDP == 17


def socket2_gethostname():
    name = gethostname()
    return isinstance(name, str) and len(name) > 0


def socket2_addr():
    packed = inet_aton("127.0.0.1")
    return len(packed) == 4 and inet_ntoa(packed) == "127.0.0.1"


__all__ = [
    "socket", "error", "herror", "gaierror", "timeout",
    "gethostname", "getfqdn", "inet_aton", "inet_ntoa", "inet_pton", "inet_ntop",
    "AF_INET", "SOCK_STREAM", "IPPROTO_TCP", "IPPROTO_UDP",
    "socket2_constants", "socket2_gethostname", "socket2_addr",
]
