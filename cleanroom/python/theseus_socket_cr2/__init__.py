# theseus_socket_cr2 - Clean-room socket constants and address utilities
# No import of socket module allowed

import struct

# POSIX socket constants
AF_INET = 2
AF_INET6 = 10
SOCK_STREAM = 1
SOCK_DGRAM = 2


def inet_aton(ip: str) -> bytes:
    """Pack IPv4 dotted-decimal string into 4-byte bytes."""
    parts = ip.split('.')
    if len(parts) != 4:
        raise OSError("illegal IP address string passed to inet_aton")
    result = []
    for part in parts:
        try:
            val = int(part)
        except ValueError:
            raise OSError("illegal IP address string passed to inet_aton")
        if val < 0 or val > 255:
            raise OSError("illegal IP address string passed to inet_aton")
        result.append(val)
    return bytes(result)


def inet_ntoa(b: bytes) -> str:
    """Unpack 4-byte bytes into dotted-decimal string."""
    if len(b) != 4:
        raise OSError("packed IP wrong length for inet_ntoa")
    return '.'.join(str(octet) for octet in b)


# Invariant test functions
def socket_cr2_af_inet() -> bool:
    """AF_INET == 2"""
    return AF_INET == 2


def socket_cr2_inet_aton() -> bool:
    """inet_aton('127.0.0.1') == b'\x7f\x00\x00\x01'"""
    return inet_aton('127.0.0.1') == b'\x7f\x00\x00\x01'


def socket_cr2_inet_ntoa() -> str:
    """inet_ntoa(b'\xc0\xa8\x01\x01') == '192.168.1.1'"""
    return inet_ntoa(b'\xc0\xa8\x01\x01')