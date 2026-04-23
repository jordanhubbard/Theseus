"""
theseus_uuid_cr2 - Clean-room UUID implementation (no import of uuid module).
"""

import os
import time
import hashlib
import struct


class UUID:
    """
    Represents a UUID (Universally Unique Identifier) as a 128-bit value.
    """

    def __init__(self, hex=None, bytes=None, bytes_le=None, fields=None, int=None, version=None):
        if [hex, bytes, bytes_le, fields, int].count(None) != 4:
            raise TypeError('One argument must be given')

        if hex is not None:
            hex = hex.replace('-', '').lower()
            if len(hex) != 32:
                raise ValueError('badly formed hexadecimal UUID string')
            int = builtins_int(hex, 16)

        elif bytes is not None:
            if len(bytes) != 16:
                raise ValueError('bytes must be a 16-byte string')
            int = builtins_int.from_bytes(bytes, 'big')

        elif bytes_le is not None:
            if len(bytes_le) != 16:
                raise ValueError('bytes_le must be a 16-byte string')
            # bytes_le has little-endian time_low, time_mid, time_hi_version
            # then big-endian clock_seq and node
            b = bytes_le
            # Rearrange: first 4 bytes LE, next 2 bytes LE, next 2 bytes LE, rest BE
            reordered = b[3::-1] + b[5:3:-1] + b[7:5:-1] + b[8:]
            int = builtins_int.from_bytes(reordered, 'big')

        elif fields is not None:
            if len(fields) != 6:
                raise ValueError('fields must be a 6-tuple')
            time_low, time_mid, time_hi_version, clock_seq_hi_variant, clock_seq_low, node = fields
            if not 0 <= time_low <= 0xFFFFFFFF:
                raise ValueError('field 1 out of range (need a 32-bit value)')
            if not 0 <= time_mid <= 0xFFFF:
                raise ValueError('field 2 out of range (need a 16-bit value)')
            if not 0 <= time_hi_version <= 0xFFFF:
                raise ValueError('field 3 out of range (need a 16-bit value)')
            if not 0 <= clock_seq_hi_variant <= 0xFF:
                raise ValueError('field 4 out of range (need an 8-bit value)')
            if not 0 <= clock_seq_low <= 0xFF:
                raise ValueError('field 5 out of range (need an 8-bit value)')
            if not 0 <= node <= 0xFFFFFFFFFFFF:
                raise ValueError('field 6 out of range (need a 48-bit value)')
            clock_seq = (clock_seq_hi_variant << 8) | clock_seq_low
            int = ((time_low << 96) | (time_mid << 80) | (time_hi_version << 64) |
                   (clock_seq << 48) | node)

        if int is not None:
            if not 0 <= int <= (2**128 - 1):
                raise ValueError('int is out of range (need a 128-bit value)')

        if version is not None:
            if not 1 <= version <= 5:
                raise ValueError('illegal version number')
            # Set variant bits (RFC 4122)
            int &= ~(0xC000 << 48)
            int |= 0x8000 << 48
            # Set version bits
            int &= ~(0xF000 << 64)
            int |= version << 76

        self.__dict__['int'] = int

    def __eq__(self, other):
        if isinstance(other, UUID):
            return self.int == other.int
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, UUID):
            return self.int < other.int
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, UUID):
            return self.int <= other.int
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, UUID):
            return self.int > other.int
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, UUID):
            return self.int >= other.int
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, UUID):
            return self.int != other.int
        return NotImplemented

    def __hash__(self):
        return hash(self.int)

    def __repr__(self):
        return f'UUID({str(self)!r})'

    def __str__(self):
        hex_str = self.hex
        return f'{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:]}'

    def __setattr__(self, name, value):
        raise TypeError('UUID objects are immutable')

    @property
    def hex(self):
        return '%032x' % self.int

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
        return (self.int >> 80) & 0xFFFF

    @property
    def time_hi_version(self):
        return (self.int >> 64) & 0xFFFF

    @property
    def clock_seq_hi_variant(self):
        return (self.int >> 56) & 0xFF

    @property
    def clock_seq_low(self):
        return (self.int >> 48) & 0xFF

    @property
    def clock_seq(self):
        return ((self.clock_seq_hi_variant & 0x3F) << 8) | self.clock_seq_low

    @property
    def node(self):
        return self.int & 0xFFFFFFFFFFFF

    @property
    def time(self):
        return (((self.time_hi_version & 0x0FFF) << 48) |
                (self.time_mid << 32) | self.time_low)

    @property
    def version(self):
        # Version is bits 76-79 of the integer
        if (self.int >> 62) & 0x3 == 0x2:  # Check variant is RFC 4122
            return (self.int >> 76) & 0xF
        raise ValueError('UUID is not a valid RFC 4122 UUID')

    @property
    def variant(self):
        if not self.int >> 127:
            return RESERVED_NCS
        elif (self.int >> 126) & 0x3 == 0x2:
            return RFC_4122
        elif (self.int >> 125) & 0x7 == 0x6:
            return RESERVED_MICROSOFT
        else:
            return RESERVED_FUTURE


# Variant constants
RESERVED_NCS = 'reserved for NCS compatibility'
RFC_4122 = 'specified in RFC 4122'
RESERVED_MICROSOFT = 'reserved for Microsoft compatibility'
RESERVED_FUTURE = 'reserved for future definition'

# Keep reference to built-in int before we shadow it
builtins_int = int


def uuid4():
    """Generate a random UUID (version 4)."""
    random_bytes = os.urandom(16)
    n = builtins_int.from_bytes(random_bytes, 'big')
    # Set version to 4 (bits 76-79)
    n &= ~(0xF << 76)
    n |= (4 << 76)
    # Set variant to RFC 4122 (bits 62-63 = 10)
    n &= ~(0x3 << 62)
    n |= (0x2 << 62)
    return UUID(int=n)


def uuid1(node=None, clock_seq=None):
    """Generate a UUID from a host ID, sequence number, and the current time."""
    # Get current time in 100-nanosecond intervals since Oct 15, 1582
    # Python time is in seconds since Jan 1, 1970
    # Difference between 1582-10-15 and 1970-01-01 in 100ns intervals
    _EPOCH_OFFSET = 0x01b21dd213814000  # 122192928000000000

    nanoseconds = time.time_ns()
    timestamp = nanoseconds // 100 + _EPOCH_OFFSET

    if clock_seq is None:
        clock_seq = builtins_int.from_bytes(os.urandom(2), 'big') & 0x3FFF

    if node is None:
        node = builtins_int.from_bytes(os.urandom(6), 'big') | 0x010000000000

    time_low = timestamp & 0xFFFFFFFF
    time_mid = (timestamp >> 32) & 0xFFFF
    time_hi_version = (timestamp >> 48) & 0x0FFF
    time_hi_version |= 0x1000  # version 1

    clock_seq_low = clock_seq & 0xFF
    clock_seq_hi_variant = (clock_seq >> 8) & 0x3F
    clock_seq_hi_variant |= 0x80  # RFC 4122 variant

    n = ((time_low << 96) | (time_mid << 80) | (time_hi_version << 64) |
         (clock_seq_hi_variant << 56) | (clock_seq_low << 48) | node)

    return UUID(int=n)


def _uuid_from_hash(version, namespace, name):
    """Helper to generate UUID from a hash (used by uuid3 and uuid5)."""
    if isinstance(name, str):
        name = name.encode('utf-8')

    ns_bytes = namespace.bytes

    if version == 3:
        h = hashlib.md5(ns_bytes + name).digest()
    elif version == 5:
        h = hashlib.sha1(ns_bytes + name).digest()[:16]
    else:
        raise ValueError('version must be 3 or 5')

    n = builtins_int.from_bytes(h, 'big')

    # Set version
    n &= ~(0xF << 76)
    n |= (version << 76)

    # Set variant to RFC 4122
    n &= ~(0x3 << 62)
    n |= (0x2 << 62)

    return UUID(int=n)


def uuid3(namespace, name):
    """Generate a UUID from the MD5 hash of a namespace UUID and a name."""
    return _uuid_from_hash(3, namespace, name)


def uuid5(namespace, name):
    """Generate a UUID from the SHA-1 hash of a namespace UUID and a name."""
    return _uuid_from_hash(5, namespace, name)


# Namespace UUIDs (from RFC 4122)
NAMESPACE_DNS = UUID(hex='6ba7b8109dad11d180b400c04fd430c8')
NAMESPACE_URL = UUID(hex='6ba7b8119dad11d180b400c04fd430c8')
NAMESPACE_OID = UUID(hex='6ba7b8129dad11d180b400c04fd430c8')
NAMESPACE_X500 = UUID(hex='6ba7b8149dad11d180b400c04fd430c8')


# Invariant functions

def uuid2_from_bytes():
    """UUID(bytes=b'\\x12'*16).int > 0 — returns True."""
    u = UUID(bytes=b'\x12' * 16)
    return u.int > 0


def uuid2_from_int():
    """UUID(int=0).hex == '0'*32."""
    u = UUID(int=0)
    return u.hex


def uuid2_version4_variant():
    """uuid4().version == 4."""
    u = uuid4()
    return u.version