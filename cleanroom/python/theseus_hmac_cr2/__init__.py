"""
theseus_hmac_cr2 - Clean-room HMAC implementation per RFC 2104.

No import of `hmac` or any third-party library. Uses
`theseus_hashlib_cr` (a Theseus-verified clean-room hashlib) for
the underlying hash function.
"""

from theseus_hashlib_cr import new as _hash_new


# ---------------------------------------------------------------------------
# Constant-time comparison.
# ---------------------------------------------------------------------------
def compare_digest(a, b):
    """
    Constant-time comparison of two strings or bytes objects.

    Returns True only if a and b are equal. Implemented by XORing each
    pair of bytes and ORing the results into an accumulator: the final
    value is zero iff every byte matched.
    """
    if isinstance(a, str):
        a = a.encode('utf-8')
    elif isinstance(a, (bytearray, memoryview)):
        a = bytes(a)
    if isinstance(b, str):
        b = b.encode('utf-8')
    elif isinstance(b, (bytearray, memoryview)):
        b = bytes(b)

    if not isinstance(a, bytes) or not isinstance(b, bytes):
        raise TypeError("compare_digest requires str or bytes-like inputs")

    # Length mismatch is not equal, but still walk the shorter input so
    # the timing profile depends only on the shorter operand's length.
    if len(a) != len(b):
        diff = 1
        shorter = a if len(a) <= len(b) else b
        for byte in shorter:
            diff |= byte ^ byte
        return False

    diff = 0
    for i in range(len(a)):
        diff |= a[i] ^ b[i]

    return diff == 0


# ---------------------------------------------------------------------------
# Digest-mod helpers.
# ---------------------------------------------------------------------------
_BLOCK_SIZES = {
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


def _normalize_digestmod(digestmod):
    """Coerce digestmod to a lowercase string name."""
    if digestmod is None or digestmod == '':
        raise ValueError("digestmod must be specified")
    if callable(digestmod):
        # Allow passing a constructor function; call it once to extract the name.
        try:
            obj = digestmod()
            name = getattr(obj, 'name', None)
            if name:
                return name.lower()
        except Exception:
            pass
        name = getattr(digestmod, '__name__', '')
        return name.lower()
    if isinstance(digestmod, str):
        return digestmod.lower()
    name = getattr(digestmod, 'name', None)
    if isinstance(name, str):
        return name.lower()
    raise TypeError("digestmod must be a string or hash constructor")


def _new_hash(digestmod):
    """Build a fresh hash object using theseus_hashlib_cr."""
    return _hash_new(_normalize_digestmod(digestmod))


def _block_size_for(digestmod):
    return _BLOCK_SIZES.get(_normalize_digestmod(digestmod), 64)


# ---------------------------------------------------------------------------
# HMAC class.
# ---------------------------------------------------------------------------
class HMAC:
    """
    HMAC per RFC 2104:

        HMAC(K, m) = H((K' XOR opad) || H((K' XOR ipad) || m))

    where ipad = 0x36 repeated and opad = 0x5C repeated to the block
    size of the underlying hash function.
    """

    def __init__(self, key, msg=None, digestmod=''):
        if digestmod is None or digestmod == '':
            raise ValueError("digestmod must be specified")

        if isinstance(key, str):
            key = key.encode('utf-8')
        elif isinstance(key, (bytearray, memoryview)):
            key = bytes(key)
        if not isinstance(key, bytes):
            raise TypeError("key must be bytes-like")

        self._digestmod = digestmod
        block_size = _block_size_for(digestmod)
        self.block_size = block_size

        # If key is longer than block size, replace with H(key).
        if len(key) > block_size:
            tmp = _new_hash(digestmod)
            tmp.update(key)
            key = tmp.digest()

        # Right-pad key with zeros up to the block size.
        if len(key) < block_size:
            key = key + b'\x00' * (block_size - len(key))

        # Build XOR-padded keys.
        ipad_key = bytes(b ^ 0x36 for b in key)
        opad_key = bytes(b ^ 0x5C for b in key)

        # Prime the inner hash with K XOR ipad.
        self._inner = _new_hash(digestmod)
        self._inner.update(ipad_key)

        # Stash the opad-keyed prefix for digest time.
        self._opad_key = opad_key

        # Record the digest size by peeking at a fresh outer hash.
        outer_probe = _new_hash(digestmod)
        self.digest_size = getattr(outer_probe, 'digest_size', None)
        self.name = "hmac-" + _normalize_digestmod(digestmod)

        if msg is not None:
            self.update(msg)

    def update(self, msg):
        """Feed `msg` into the inner hash."""
        if isinstance(msg, str):
            msg = msg.encode('utf-8')
        elif isinstance(msg, (bytearray, memoryview)):
            msg = bytes(msg)
        self._inner.update(msg)
        return self

    def digest(self):
        """Return the HMAC value as raw bytes."""
        inner_copy = self._inner.copy()
        inner_digest = inner_copy.digest()

        outer = _new_hash(self._digestmod)
        outer.update(self._opad_key)
        outer.update(inner_digest)
        return outer.digest()

    def hexdigest(self):
        """Return the HMAC value as a lowercase hex string."""
        raw = self.digest()
        hex_chars = "0123456789abcdef"
        out = []
        for byte in raw:
            out.append(hex_chars[(byte >> 4) & 0xF])
            out.append(hex_chars[byte & 0xF])
        return ''.join(out)

    def copy(self):
        """Return a deep copy of this HMAC object."""
        clone = HMAC.__new__(HMAC)
        clone._digestmod = self._digestmod
        clone.block_size = self.block_size
        clone._opad_key = self._opad_key
        clone._inner = self._inner.copy()
        clone.digest_size = self.digest_size
        clone.name = self.name
        return clone


def new(key, msg=None, digestmod=''):
    """
    Create a fresh HMAC object.

    key: bytes-like — the secret key.
    msg: bytes-like or None — optional initial message.
    digestmod: str — hash algorithm name (e.g. 'sha256').
    """
    return HMAC(key, msg=msg, digestmod=digestmod)


def digest(key, msg, digest):
    """
    One-shot HMAC: compute HMAC(key, msg) and return the raw bytes.
    """
    return HMAC(key, msg=msg, digestmod=digest).digest()


# ---------------------------------------------------------------------------
# Invariants.
# ---------------------------------------------------------------------------
def hmac2_compare_equal():
    """compare_digest of two equal strings is True."""
    return compare_digest('abc', 'abc')


def hmac2_compare_unequal():
    """compare_digest of two different strings is False."""
    return compare_digest('abc', 'def')


def hmac2_new_len():
    """new(b'key', b'msg', 'sha256').hexdigest() has length 64."""
    return len(new(b'key', b'msg', 'sha256').hexdigest())


__all__ = [
    "compare_digest",
    "new",
    "digest",
    "HMAC",
    "hmac2_compare_equal",
    "hmac2_compare_unequal",
    "hmac2_new_len",
]