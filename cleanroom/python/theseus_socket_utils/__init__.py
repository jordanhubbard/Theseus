"""
theseus_socket_utils - Clean-room socket address utilities.
No imports of socket or ipaddress modules.
"""


def inet_aton(ip_string: str) -> bytes:
    """
    Convert a dotted-decimal IPv4 address string to a 4-byte packed binary.

    Example:
        inet_aton('192.168.1.1') == b'\\xc0\\xa8\\x01\\x01'
    """
    parts = ip_string.split('.')
    if len(parts) != 4:
        raise OSError(f"illegal IP address string passed to inet_aton: {ip_string!r}")

    result = []
    for part in parts:
        try:
            value = int(part)
        except ValueError:
            raise OSError(f"illegal IP address string passed to inet_aton: {ip_string!r}")

        if value < 0 or value > 255:
            raise OSError(f"illegal IP address string passed to inet_aton: {ip_string!r}")

        result.append(value)

    return bytes(result)


def inet_ntoa(packed_ip: bytes) -> str:
    """
    Convert a 4-byte packed binary IPv4 address to a dotted-decimal string.

    Example:
        inet_ntoa(b'\\xc0\\xa8\\x01\\x01') == '192.168.1.1'
    """
    if len(packed_ip) != 4:
        raise OSError(
            f"packed IP wrong length for inet_ntoa: expected 4 bytes, got {len(packed_ip)}"
        )

    return '.'.join(str(b) for b in packed_ip)


def round_trip(ip_string: str) -> str:
    """
    Convert an IPv4 dotted-decimal string to packed bytes and back.

    Example:
        round_trip('192.168.1.1') == '192.168.1.1'
    """
    return inet_ntoa(inet_aton(ip_string))


def gethostbyname_mock(hostname: str) -> str:
    """
    A hardcoded mock hostname resolver (no DNS).

    Currently only supports 'localhost' -> '127.0.0.1'.
    """
    mock_hosts = {
        'localhost': '127.0.0.1',
    }

    if hostname in mock_hosts:
        return mock_hosts[hostname]

    raise OSError(f"gethostbyname_mock: unknown host {hostname!r}")


def socket_inet_aton() -> bool:
    return inet_aton('192.168.1.1') == b'\xc0\xa8\x01\x01'


def socket_inet_ntoa() -> str:
    return inet_ntoa(b'\xc0\xa8\x01\x01')


def socket_round_trip() -> bool:
    return inet_ntoa(inet_aton('10.0.0.1')) == '10.0.0.1'