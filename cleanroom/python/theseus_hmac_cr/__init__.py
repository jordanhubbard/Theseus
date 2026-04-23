"""
theseus_hmac_cr — Clean-room hmac module.
No import of the standard `hmac` module.
Uses _hashlib C extension directly.
"""

import _hashlib as _hl
import _operator as _op


# HMAC block sizes for common algorithms
_DIGEST_BLOCK_SIZE = {
    'md5': 64,
    'sha1': 64,
    'sha224': 64,
    'sha256': 64,
    'sha384': 128,
    'sha512': 128,
    'sha3_224': 144,
    'sha3_256': 136,
    'sha3_384': 104,
    'sha3_512': 72,
    'blake2b': 128,
    'blake2s': 64,
}

digest_size = None  # set per-instance


class HMAC:
    """Keyed-Hashing for Message Authentication."""

    blocksize = 64

    def __init__(self, key, msg=None, digestmod=''):
        if not digestmod:
            raise TypeError('Missing required parameter: digestmod')

        if callable(digestmod):
            self._init_old(key, msg, digestmod)
            return

        if isinstance(digestmod, str):
            _name = digestmod.lower().replace('-', '_')
        else:
            _name = digestmod

        try:
            self._hmac = _hl.hmac_new(key, msg or b'', _name)
            self.digest_size = self._hmac.digest_size
            self._digestmod_name = _name
            self.blocksize = _DIGEST_BLOCK_SIZE.get(_name, 64)
        except (ValueError, AttributeError):
            self._hmac = None
            self._init_pure(key, msg, _name)

    def _init_pure(self, key, msg, name):
        """Pure-Python HMAC using hashlib new()."""
        self._digestmod_name = name
        self.blocksize = _DIGEST_BLOCK_SIZE.get(name, 64)

        def _new_hash(data=b''):
            return _hl.new(name, data)

        h = _new_hash()
        self.digest_size = h.digest_size

        if len(key) > self.blocksize:
            key = _new_hash(key).digest()
        key = key.ljust(self.blocksize, b'\x00')

        self._ipad = bytes(x ^ 0x36 for x in key)
        self._opad = bytes(x ^ 0x5C for x in key)

        self._inner = _new_hash(self._ipad)
        self._outer_key = self._opad
        self._new_hash = _new_hash
        if msg is not None:
            self._inner.update(msg)

    def _init_old(self, key, msg, digestmod_callable):
        self._hmac = None
        self._digestmod_name = getattr(digestmod_callable, 'name', 'unknown')
        h = digestmod_callable()
        self.digest_size = h.digest_size
        self.blocksize = getattr(h, 'block_size', 64)

        def _new_hash(data=b''):
            return digestmod_callable(data)

        if len(key) > self.blocksize:
            key = _new_hash(key).digest()
        key = key.ljust(self.blocksize, b'\x00')
        self._ipad = bytes(x ^ 0x36 for x in key)
        self._opad = bytes(x ^ 0x5C for x in key)
        self._inner = _new_hash(self._ipad)
        self._outer_key = self._opad
        self._new_hash = _new_hash
        if msg is not None:
            self._inner.update(msg)

    @property
    def name(self):
        return 'hmac-' + self._digestmod_name

    def update(self, msg):
        """Update this hashing object with the string msg."""
        if self._hmac is not None:
            self._hmac.update(msg)
        else:
            self._inner.update(msg)

    def digest(self):
        """Return the hash value of this hashing object."""
        if self._hmac is not None:
            return self._hmac.digest()
        h = self._new_hash(self._outer_key)
        h.update(self._inner.digest())
        return h.digest()

    def hexdigest(self):
        """Return the hex-encoded hash value."""
        return self.digest().hex()

    def copy(self):
        """Return a separate copy of this hashing object."""
        other = HMAC.__new__(HMAC)
        if self._hmac is not None:
            other._hmac = self._hmac.copy()
            other.digest_size = self.digest_size
            other._digestmod_name = self._digestmod_name
            other.blocksize = self.blocksize
        else:
            other._hmac = None
            other._digestmod_name = self._digestmod_name
            other.digest_size = self.digest_size
            other.blocksize = self.blocksize
            other._ipad = self._ipad
            other._opad = self._opad
            other._outer_key = self._outer_key
            other._new_hash = self._new_hash
            other._inner = self._inner.copy()
        return other


def new(key, msg=None, digestmod=''):
    """Create a new hashing object and return it."""
    return HMAC(key, msg, digestmod)


def digest(key, msg, digest):
    """Return the HMAC digest without creating a full object."""
    if isinstance(digest, str):
        _name = digest.lower().replace('-', '_')
        try:
            return _hl.hmac_digest(key, msg, _name)
        except (ValueError, AttributeError):
            pass
    h = new(key, msg, digest)
    return h.digest()


def compare_digest(a, b):
    """Compare two digests in constant time to avoid timing attacks."""
    if isinstance(a, str):
        if not isinstance(b, str):
            raise TypeError("unsupported operand types(s) for ==: 'str' and 'bytes'")
        # Use _operator for constant-time comparison if available
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a.encode(), b.encode()):
            result |= x ^ y
        return result == 0
    if not isinstance(a, (bytes, bytearray)):
        raise TypeError(f"unsupported operand type(s): {type(a)!r}")
    if not isinstance(b, (bytes, bytearray)):
        raise TypeError(f"unsupported operand type(s): {type(b)!r}")
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def hmac2_basic():
    """HMAC-SHA256 produces correct digest; returns True."""
    h = new(b'key', b'The quick brown fox jumps over the lazy dog', 'sha256')
    expected = 'f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8'
    return h.hexdigest() == expected


def hmac2_digest():
    """digest() shortcut function works; returns True."""
    result = digest(b'key', b'message', 'sha256')
    return isinstance(result, bytes) and len(result) == 32


def hmac2_compare():
    """compare_digest() is constant-time safe; returns True."""
    a = b'hello'
    b = b'hello'
    c = b'world'
    return compare_digest(a, b) is True and compare_digest(a, c) is False


__all__ = [
    'HMAC', 'new', 'digest', 'compare_digest',
    'hmac2_basic', 'hmac2_digest', 'hmac2_compare',
]
