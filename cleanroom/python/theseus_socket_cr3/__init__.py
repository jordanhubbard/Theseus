import struct
import sys


def inet_aton(ip_string: str) -> bytes:
    """Pack IPv4 address from dotted-quad string to 4-byte bytes."""
    parts = ip_string.split('.')
    if len(parts) != 4:
        raise ValueError(f"Invalid IPv4 address: {ip_string}")
    octets = []
    for part in parts:
        val = int(part)
        if val < 0 or val > 255:
            raise ValueError(f"Invalid octet value: {val}")
        octets.append(val)
    return bytes(octets)


def inet_ntoa(packed_ip: bytes) -> str:
    """Convert 4-byte packed IPv4 address to dotted-quad string."""
    if len(packed_ip) != 4:
        raise ValueError(f"Packed IP must be exactly 4 bytes, got {len(packed_ip)}")
    return '.'.join(str(b) for b in packed_ip)


def _is_big_endian() -> bool:
    """Return True if the system is big-endian."""
    return sys.byteorder == 'big'


def htons(x: int) -> int:
    """Convert 16-bit integer from host byte order to network (big-endian) byte order."""
    x = x & 0xFFFF
    if _is_big_endian():
        return x
    # Swap bytes
    return ((x & 0xFF) << 8) | ((x >> 8) & 0xFF)


def ntohs(x: int) -> int:
    """Convert 16-bit integer from network (big-endian) byte order to host byte order."""
    # ntohs is the inverse of htons; since both are symmetric swaps, it's the same operation
    x = x & 0xFFFF
    if _is_big_endian():
        return x
    return ((x & 0xFF) << 8) | ((x >> 8) & 0xFF)


def htonl(x: int) -> int:
    """Convert 32-bit integer from host byte order to network (big-endian) byte order."""
    x = x & 0xFFFFFFFF
    if _is_big_endian():
        return x
    # Swap bytes
    b0 = (x >> 24) & 0xFF
    b1 = (x >> 16) & 0xFF
    b2 = (x >> 8) & 0xFF
    b3 = x & 0xFF
    return (b3 << 24) | (b2 << 16) | (b1 << 8) | b0


def ntohl(x: int) -> int:
    """Convert 32-bit integer from network (big-endian) byte order to host byte order."""
    x = x & 0xFFFFFFFF
    if _is_big_endian():
        return x
    b0 = (x >> 24) & 0xFF
    b1 = (x >> 16) & 0xFF
    b2 = (x >> 8) & 0xFF
    b3 = x & 0xFF
    return (b3 << 24) | (b2 << 16) | (b1 << 8) | b0


# Invariant check functions

def socket3_inet_aton() -> bool:
    """inet_aton('192.168.1.1') — check first byte is 192 — returns True."""
    result = inet_aton('192.168.1.1')
    return result[0] == 192


def socket3_inet_ntoa() -> str:
    """inet_ntoa(b'\\xc0\\xa8\\x01\\x01') == '192.168.1.1'"""
    return inet_ntoa(b'\xc0\xa8\x01\x01')


def socket3_htons_roundtrip() -> int:
    """ntohs(htons(1234)) == 1234 (round-trip)."""
    return ntohs(htons(1234))