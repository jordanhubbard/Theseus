"""
Clean-room HMAC-SHA256 implementation.
Does not import hmac or hashlib.
Uses theseus_hashlib for SHA-256.
"""

import theseus_hashlib


class _SHA256Hasher:
    def __init__(self):
        self._buf = bytearray()

    def update(self, data: bytes):
        self._buf.extend(data)

    def digest(self) -> bytes:
        return bytes.fromhex(theseus_hashlib.sha256(bytes(self._buf)))


def _sha256_factory():
    return _SHA256Hasher()


BLOCK_SIZE = 64  # SHA-256 block size in bytes
IPAD = 0x36
OPAD = 0x5C


class HMAC:
    """HMAC object supporting hexdigest()."""

    def __init__(self, key: bytes, msg: bytes, digestmod):
        self._digestmod = digestmod

        # If key is longer than block size, hash it
        if len(key) > BLOCK_SIZE:
            h = digestmod()
            h.update(key)
            key = h.digest()

        # Pad key to block size
        if len(key) < BLOCK_SIZE:
            key = key + b'\x00' * (BLOCK_SIZE - len(key))

        # Compute ipad and opad keys
        ipad_key = bytes(b ^ IPAD for b in key)
        opad_key = bytes(b ^ OPAD for b in key)

        # Inner hash: H(ipad_key || msg)
        inner = digestmod()
        inner.update(ipad_key)
        inner.update(msg)
        inner_digest = inner.digest()

        # Outer hash: H(opad_key || inner_digest)
        outer = digestmod()
        outer.update(opad_key)
        outer.update(inner_digest)
        self._digest = outer.digest()

    def digest(self) -> bytes:
        return self._digest

    def hexdigest(self) -> str:
        return ''.join('{:02x}'.format(b) for b in self._digest)


def new(key: bytes, msg: bytes = b'', digestmod=None) -> 'HMAC':
    """
    Create a new HMAC object.

    :param key: The secret key (bytes)
    :param msg: Initial message (bytes), default empty
    :param digestmod: Hash constructor (e.g. theseus_hashlib.sha256)
    :return: HMAC object with hexdigest() method
    """
    if digestmod is None:
        digestmod = _sha256_factory
    return HMAC(key, msg, digestmod)


def compare_digest(a, b) -> bool:
    """
    Constant-time comparison of two strings or bytes to prevent timing attacks.

    :param a: First value
    :param b: Second value
    :return: True if equal, False otherwise
    """
    if type(a) != type(b):
        raise TypeError("a and b must be of the same type")

    if isinstance(a, str):
        a_bytes = a.encode('ascii')
        b_bytes = b.encode('ascii')
    elif isinstance(a, bytes):
        a_bytes = a
        b_bytes = b
    else:
        raise TypeError("a and b must be str or bytes")

    la = len(a_bytes)
    lb = len(b_bytes)

    max_len = max(la, lb) if (la > 0 or lb > 0) else 1

    result = la ^ lb  # non-zero if lengths differ

    for i in range(max_len):
        x = a_bytes[i] if i < la else 0
        y = b_bytes[i] if i < lb else 0
        result |= x ^ y

    return result == 0


# --- Invariant verification functions ---

def hmac_new_result() -> bool:
    """
    Verify HMAC-SHA256(b'key', b'message') returns the correct digest.
    """
    h = new(b'key', b'message', _sha256_factory)
    hex_digest = h.hexdigest()
    # HMAC-SHA256(key=b'key', msg=b'message')
    # Known correct value (64 hex chars = 32 bytes)
    expected = '6e9ef29b75fffc5b7abae527d58fdadb2fe42e7219011976917343065f58ed4a'
    assert len(hex_digest) == 64, f"hexdigest length is {len(hex_digest)}, expected 64"
    return hex_digest == expected


def hmac_compare_digest_equal() -> bool:
    """compare_digest(a, a) == True"""
    a = "hello"
    return compare_digest(a, a)


def hmac_compare_digest_unequal() -> bool:
    return compare_digest("hello", "world")