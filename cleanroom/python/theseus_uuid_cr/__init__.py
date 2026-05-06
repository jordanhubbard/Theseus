"""Clean-room implementation of a UUID module (no import of uuid)."""

import os
import hashlib


class UUID(object):
    """UUID class — represents a 128-bit Universally Unique Identifier."""

    __slots__ = ('int',)

    def __init__(self, hex=None, bytes=None, int_value=None, version=None,
                 fields=None):
        # Determine the integer value from one of the input forms.
        if [hex, bytes, int_value, fields].count(None) != 3:
            raise TypeError(
                'one of the hex, bytes, int_value, or fields arguments '
                'must be given'
            )

        if hex is not None:
            s = hex.strip()
            if s.startswith('urn:'):
                s = s[4:]
            if s.startswith('uuid:'):
                s = s[5:]
            s = s.strip('{}').replace('-', '')
            if len(s) != 32:
                raise ValueError('badly formed hexadecimal UUID string')
            ival = 0
            for ch in s:
                d = ord(ch)
                if 0x30 <= d <= 0x39:
                    n = d - 0x30
                elif 0x61 <= d <= 0x66:
                    n = d - 0x61 + 10
                elif 0x41 <= d <= 0x46:
                    n = d - 0x41 + 10
                else:
                    raise ValueError('badly formed hexadecimal UUID string')
                ival = (ival << 4) | n
        elif bytes is not None:
            if len(bytes) != 16:
                raise ValueError('bytes must be 16 bytes long')
            ival = 0
            for b in bytes:
                ival = (ival << 8) | b
        elif int_value is not None:
            ival = int_value
            if ival < 0 or ival >= (1 << 128):
                raise ValueError('int is out of range (need 128-bit value)')
        else:  # fields
            if len(fields) != 6:
                raise ValueError('fields must be a 6-tuple')
            tl, tm, thv, csr, csl, node = fields
            ival = ((tl & 0xffffffff) << 96
                    | (tm & 0xffff) << 80
                    | (thv & 0xffff) << 64
                    | (csr & 0xff) << 56
                    | (csl & 0xff) << 48
                    | (node & 0xffffffffffff))

        if version is not None:
            if not 1 <= version <= 5:
                raise ValueError('illegal version number')
            # Set the variant bits (bits 62-63) to RFC 4122 (binary 10).
            ival &= ~(0xc000 << 48)
            ival |= 0x8000 << 48
            # Set the version bits (bits 76-79).
            ival &= ~(0xf000 << 64)
            ival |= version << 76

        # Use object.__setattr__ to support possible immutability later.
        object.__setattr__(self, 'int', ival)

    # ------------------------------------------------------------------
    # Representations
    # ------------------------------------------------------------------
    @property
    def bytes(self):
        out = bytearray(16)
        v = self.int
        for i in range(15, -1, -1):
            out[i] = v & 0xff
            v >>= 8
        return _bytes(out)

    @property
    def hex(self):
        # Produce a 32-character lowercase hex string without using format
        # codes that depend on imported modules.
        v = self.int
        digits = '0123456789abcdef'
        chars = [''] * 32
        for i in range(31, -1, -1):
            chars[i] = digits[v & 0xf]
            v >>= 4
        return ''.join(chars)

    @property
    def version(self):
        return (self.int >> 76) & 0xf

    @property
    def variant(self):
        # Top bits of byte 8.
        b = (self.int >> 56) & 0xff
        if not b & 0x80:
            return 'reserved NCS'
        if not b & 0x40:
            return 'specified in RFC 4122'
        if not b & 0x20:
            return 'reserved Microsoft'
        return 'reserved future'

    @property
    def fields(self):
        v = self.int
        node = v & 0xffffffffffff
        csl = (v >> 48) & 0xff
        csr = (v >> 56) & 0xff
        thv = (v >> 64) & 0xffff
        tm = (v >> 80) & 0xffff
        tl = (v >> 96) & 0xffffffff
        return (tl, tm, thv, csr, csl, node)

    @property
    def time_low(self):
        return self.fields[0]

    @property
    def time_mid(self):
        return self.fields[1]

    @property
    def time_hi_version(self):
        return self.fields[2]

    @property
    def clock_seq_hi_variant(self):
        return self.fields[3]

    @property
    def clock_seq_low(self):
        return self.fields[4]

    @property
    def node(self):
        return self.fields[5]

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------
    def __str__(self):
        h = self.hex
        return h[:8] + '-' + h[8:12] + '-' + h[12:16] + '-' + h[16:20] + '-' + h[20:]

    def __repr__(self):
        return "UUID('" + str(self) + "')"

    def __eq__(self, other):
        if isinstance(other, UUID):
            return self.int == other.int
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, UUID):
            return self.int != other.int
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

    def __hash__(self):
        return hash(self.int)

    def __int__(self):
        return self.int


def _bytes(seq):
    """Build a bytes object from an iterable of ints (helper)."""
    return bytes(bytearray(seq))


# ---------------------------------------------------------------------------
# Standard namespaces (RFC 4122)
# ---------------------------------------------------------------------------
NAMESPACE_DNS = UUID(hex='6ba7b810-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_URL = UUID(hex='6ba7b811-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_OID = UUID(hex='6ba7b812-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_X500 = UUID(hex='6ba7b814-9dad-11d1-80b4-00c04fd430c8')


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
def uuid4():
    """Generate a random UUID (version 4)."""
    raw = os.urandom(16)
    ival = 0
    for b in raw:
        ival = (ival << 8) | b
    return UUID(int_value=ival, version=4)


def uuid5(namespace, name):
    """Generate a UUID from the SHA-1 hash of a namespace UUID and a name."""
    if isinstance(name, str):
        name_bytes = name.encode('utf-8')
    else:
        name_bytes = name
    h = hashlib.sha1(namespace.bytes + name_bytes).digest()
    ival = 0
    for b in h[:16]:
        ival = (ival << 8) | b
    return UUID(int_value=ival, version=5)


def uuid3(namespace, name):
    """Generate a UUID from the MD5 hash of a namespace UUID and a name."""
    if isinstance(name, str):
        name_bytes = name.encode('utf-8')
    else:
        name_bytes = name
    h = hashlib.md5(namespace.bytes + name_bytes).digest()
    ival = 0
    for b in h:
        ival = (ival << 8) | b
    return UUID(int_value=ival, version=3)


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------
def uuid2_uuid4():
    """Test that uuid4() produces valid version-4 UUIDs."""
    u = uuid4()
    if not isinstance(u, UUID):
        return False
    if u.version != 4:
        return False
    # Variant must be RFC 4122 (binary 10 in the top two bits of byte 8).
    variant_bits = (u.int >> 62) & 0x3
    if variant_bits != 0x2:
        return False
    # String form must be 36 chars with dashes in the right places.
    s = str(u)
    if len(s) != 36:
        return False
    if s[8] != '-' or s[13] != '-' or s[18] != '-' or s[23] != '-':
        return False
    # Two successive uuid4 calls must (with overwhelming probability) differ.
    u2 = uuid4()
    if u == u2:
        return False
    if u.int == u2.int:
        return False
    # Round-trip via hex.
    u3 = UUID(hex=str(u))
    if u3 != u:
        return False
    # Round-trip via bytes.
    u4 = UUID(bytes=u.bytes)
    if u4 != u:
        return False
    return True


def uuid2_uuid5():
    """Test that uuid5() is deterministic and yields version-5 UUIDs."""
    a = uuid5(NAMESPACE_DNS, 'example.com')
    b = uuid5(NAMESPACE_DNS, 'example.com')
    if a != b:
        return False
    if a.version != 5:
        return False
    # Variant check.
    if ((a.int >> 62) & 0x3) != 0x2:
        return False
    # Different names must produce different UUIDs.
    c = uuid5(NAMESPACE_DNS, 'example.org')
    if a == c:
        return False
    # Different namespaces with the same name must also differ.
    d = uuid5(NAMESPACE_URL, 'example.com')
    if a == d:
        return False
    # Known answer: the Python standard library produces this for
    # uuid5(NAMESPACE_DNS, 'python.org')
    expected = '886313e1-3b8a-5372-9b90-0c9aee199e5d'
    got = str(uuid5(NAMESPACE_DNS, 'python.org'))
    if got != expected:
        return False
    return True


def uuid2_class():
    """Test the UUID class itself: parsing, formatting, comparisons."""
    sample = '12345678-1234-5678-1234-567812345678'
    u = UUID(hex=sample)
    if str(u) != sample:
        return False
    if u.hex != '12345678123456781234567812345678':
        return False
    if u.int != 0x12345678123456781234567812345678:
        return False

    # Construct from int and confirm equality.
    u2 = UUID(int_value=u.int)
    if u != u2:
        return False
    if hash(u) != hash(u2):
        return False

    # Construct from bytes and confirm equality.
    u3 = UUID(bytes=u.bytes)
    if u != u3:
        return False

    # Accept braces and urn: prefixes.
    u4 = UUID(hex='{' + sample + '}')
    if u4 != u:
        return False
    u5 = UUID(hex='urn:uuid:' + sample)
    if u5 != u:
        return False

    # Ordering must be based on the integer value.
    smaller = UUID(int_value=0)
    bigger = UUID(int_value=(1 << 128) - 1)
    if not (smaller < u < bigger):
        return False
    if not (bigger > u > smaller):
        return False

    # repr should round-trip through eval-like reconstruction.
    if repr(u) != "UUID('" + sample + "')":
        return False

    # Bad hex should raise ValueError.
    try:
        UUID(hex='not-a-uuid')
    except ValueError:
        pass
    else:
        return False

    # Bytes of wrong length should raise ValueError.
    try:
        UUID(bytes=b'\x00' * 15)
    except ValueError:
        pass
    else:
        return False

    # Must not be possible to omit all inputs.
    try:
        UUID()
    except TypeError:
        pass
    else:
        return False

    # Fields tuple sanity.
    fields = u.fields
    if len(fields) != 6:
        return False
    if fields[0] != 0x12345678:
        return False
    if fields[1] != 0x1234:
        return False

    return True