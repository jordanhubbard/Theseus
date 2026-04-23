"""
theseus_uuid_cr — Clean-room uuid module.
No import of the standard `uuid` module.
Pure-Python UUID implementation.
"""

import os as _os
import hashlib as _hl
import struct as _st
import time as _time


# Standard namespace UUIDs
NAMESPACE_DNS = None   # filled below
NAMESPACE_URL = None
NAMESPACE_OID = None
NAMESPACE_X500 = None

RESERVED_NCS = 'reserved for NCS compatibility'
RFC_4122 = 'specified in RFC 4122'
RESERVED_MICROSOFT = 'reserved for Microsoft compatibility'
RESERVED_FUTURE = 'reserved for future definition'


class UUID:
    """Represents a UUID."""

    __slots__ = ('int', 'is_safe', '__weakref__')

    def __init__(self, hex=None, bytes=None, bytes_le=None, fields=None, int=None,
                 version=None, *, is_safe=False):
        if [hex, bytes, bytes_le, fields, int].count(None) != 4:
            raise TypeError('need one of hex, bytes, bytes_le, fields, or int')
        if hex is not None:
            hex = hex.replace('urn:', '').replace('uuid:', '')
            hex = hex.strip('{}').replace('-', '')
            if len(hex) != 32:
                raise ValueError('badly formed hexadecimal UUID string')
            int = int_type(hex, 16)
        elif bytes_le is not None:
            if len(bytes_le) != 16:
                raise ValueError('bytes_le is not a 16-char string')
            (tl, tm, thv, csher, noder) = _st.unpack_from('<IHH8s', bytes_le)
            int = ((tl << 96) | (tm << 80) | (thv << 64) |
                   int_type.from_bytes(csher, 'big') << 48 |
                   int_type.from_bytes(noder, 'big'))
        elif bytes is not None:
            if len(bytes) != 16:
                raise ValueError('bytes is not a 16-char string')
            int = int_type.from_bytes(bytes, 'big')
        elif fields is not None:
            if len(fields) != 6:
                raise ValueError('fields is not a 6-tuple')
            (tl, tm, thv, cs_hi, cs_lo, node) = fields
            int = ((tl << 96) | (tm << 80) | (thv << 64) |
                   (cs_hi << 56) | (cs_lo << 48) | node)
        if version is not None:
            if not 1 <= version <= 5:
                raise ValueError('illegal version number')
            int &= ~(0xc000 << 48)
            int |= 0x8000 << 48
            int &= ~(0xf000 << 64)
            int |= version << 76
        object.__setattr__(self, 'int', int)
        object.__setattr__(self, 'is_safe', is_safe)

    def __setattr__(self, name, value):
        raise TypeError('UUID objects are immutable')

    def __delattr__(self, name):
        raise TypeError('UUID objects are immutable')

    def __str__(self):
        hex = '%032x' % self.int
        return '%s-%s-%s-%s-%s' % (hex[:8], hex[8:12], hex[12:16], hex[16:20], hex[20:32])

    def __repr__(self):
        return f"UUID('{self}')"

    def __hash__(self):
        return hash(self.int)

    def __eq__(self, other):
        if isinstance(other, UUID):
            return self.int == other.int
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, UUID):
            return self.int < other.int
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, UUID):
            return self.int > other.int
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, UUID):
            return self.int <= other.int
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, UUID):
            return self.int >= other.int
        return NotImplemented

    @property
    def bytes(self):
        return self.int.to_bytes(16, 'big')

    @property
    def bytes_le(self):
        b = self.bytes
        return b[3::-1] + b[5:3:-1] + b[7:5:-1] + b[8:]

    @property
    def fields(self):
        return (self.time_low, self.time_mid, self.time_hi_version,
                self.clock_seq_hi_variant, self.clock_seq_low, self.node)

    @property
    def time_low(self):
        return self.int >> 96

    @property
    def time_mid(self):
        return (self.int >> 80) & 0xffff

    @property
    def time_hi_version(self):
        return (self.int >> 64) & 0xffff

    @property
    def clock_seq_hi_variant(self):
        return (self.int >> 56) & 0xff

    @property
    def clock_seq_low(self):
        return (self.int >> 48) & 0xff

    @property
    def time(self):
        return (((self.time_hi_version & 0x0fff) << 48) |
                (self.time_mid << 32) | self.time_low)

    @property
    def clock_seq(self):
        return (((self.clock_seq_hi_variant & 0x3f) << 8) |
                self.clock_seq_low)

    @property
    def node(self):
        return self.int & 0xffffffffffff

    @property
    def hex(self):
        return '%032x' % self.int

    @property
    def urn(self):
        return 'urn:uuid:' + str(self)

    @property
    def variant(self):
        if not self.int & (0x8000 << 48):
            return RESERVED_NCS
        elif not self.int & (0x4000 << 48):
            return RFC_4122
        elif not self.int & (0x2000 << 48):
            return RESERVED_MICROSOFT
        else:
            return RESERVED_FUTURE

    @property
    def version(self):
        if self.variant == RFC_4122:
            return int((self.int >> 76) & 0xf)


# Use Python's int as the integer type
int_type = int


def uuid1(node=None, clock_seq=None):
    """Generate a UUID from a host ID, sequence number, and the current time."""
    # Get timestamp
    nanoseconds = _time.time_ns()
    timestamp = nanoseconds // 100 + 0x01b21dd213814000
    if clock_seq is None:
        clock_seq = int_type.from_bytes(_os.urandom(2), 'big') & 0x3fff
    if node is None:
        node = int_type.from_bytes(_os.urandom(6), 'big') | (1 << 40)
    time_low = timestamp & 0xffffffff
    time_mid = (timestamp >> 32) & 0xffff
    time_hi_version = (timestamp >> 48) & 0x0fff
    clock_seq_low = clock_seq & 0xff
    clock_seq_hi_variant = (clock_seq >> 8) & 0x3f
    return UUID(fields=(time_low, time_mid, time_hi_version,
                        clock_seq_hi_variant, clock_seq_low, node), version=1)


def uuid3(namespace, name):
    """Generate a UUID from the MD5 hash of a namespace UUID and a name."""
    if isinstance(name, str):
        name = name.encode()
    h = _hl.md5(namespace.bytes + name)
    return UUID(bytes=h.digest(), version=3)


def uuid4():
    """Generate a random UUID."""
    return UUID(bytes=_os.urandom(16), version=4)


def uuid5(namespace, name):
    """Generate a UUID from the SHA-1 hash of a namespace UUID and a name."""
    if isinstance(name, str):
        name = name.encode()
    h = _hl.sha1(namespace.bytes + name)
    return UUID(bytes=h.digest()[:16], version=5)


# Define namespace UUIDs
NAMESPACE_DNS = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_URL = UUID('6ba7b811-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_OID = UUID('6ba7b812-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_X500 = UUID('6ba7b814-9dad-11d1-80b4-00c04fd430c8')


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def uuid2_uuid4():
    """uuid4() generates random UUIDs; returns True."""
    u1 = uuid4()
    u2 = uuid4()
    return (isinstance(u1, UUID) and
            u1.version == 4 and
            u1 != u2 and
            len(str(u1)) == 36)


def uuid2_uuid5():
    """uuid5() generates name-based UUIDs; returns True."""
    u = uuid5(NAMESPACE_DNS, 'python.org')
    expected = '886313e1-3b8a-5372-9b90-0c9aee199e5d'
    return (isinstance(u, UUID) and
            u.version == 5 and
            str(u) == expected)


def uuid2_class():
    """UUID class parses hex strings correctly; returns True."""
    u = UUID('12345678-1234-5678-1234-567812345678')
    return (u.time_low == 0x12345678 and
            u.time_mid == 0x1234 and
            str(u) == '12345678-1234-5678-1234-567812345678')


__all__ = [
    'UUID', 'uuid1', 'uuid3', 'uuid4', 'uuid5',
    'NAMESPACE_DNS', 'NAMESPACE_URL', 'NAMESPACE_OID', 'NAMESPACE_X500',
    'RESERVED_NCS', 'RFC_4122', 'RESERVED_MICROSOFT', 'RESERVED_FUTURE',
    'uuid2_uuid4', 'uuid2_uuid5', 'uuid2_class',
]
