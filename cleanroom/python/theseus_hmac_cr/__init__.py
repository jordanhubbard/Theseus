"""Clean-room implementation of an HMAC module (theseus_hmac_cr).

Implements RFC 2104 HMAC from scratch using hashlib for the underlying
hash functions. Does NOT import the standard library `hmac` module.
"""

import hashlib as _hashlib


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TRANS_36 = bytes((x ^ 0x36) for x in range(256))
_TRANS_5C = bytes((x ^ 0x5C) for x in range(256))


def _resolve_digestmod(digestmod):
    """Return (constructor, name) for the given digestmod argument.

    digestmod may be:
      - a string naming a hashlib algorithm ("sha256", "md5", ...)
      - a callable returning a fresh hash object
      - a module-like object exposing .new() (e.g. hashlib.sha256)
    """
    if digestmod is None:
        raise TypeError("Missing required parameter 'digestmod'")

    if isinstance(digestmod, str):
        name = digestmod

        def cons(data=b''):
            return _hashlib.new(name, data)

        return cons, name

    if callable(digestmod):
        # Treat as a hash constructor like hashlib.sha256
        sample = digestmod()
        name = getattr(sample, 'name', 'unknown')
        return digestmod, name

    if hasattr(digestmod, 'new'):
        cons = digestmod.new
        sample = cons()
        name = getattr(sample, 'name', 'unknown')
        return cons, name

    raise TypeError("digestmod must be a string, callable, or module")


def _coerce_bytes(data, name='data'):
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    raise TypeError("%s must be bytes-like, not %s"
                    % (name, type(data).__name__))


# ---------------------------------------------------------------------------
# HMAC class
# ---------------------------------------------------------------------------

class HMAC(object):
    """RFC 2104 HMAC implementation."""

    def __init__(self, key, msg=None, digestmod=None):
        cons, name = _resolve_digestmod(digestmod)
        self._hash_cons = cons
        self._digestmod_name = name

        # Sample to discover block / digest sizes
        sample = cons()
        self.digest_size = sample.digest_size
        block_size = getattr(sample, 'block_size', 64)
        if block_size < 16:
            # Some hashes report a tiny block_size; fall back to 64 like hmac.
            block_size = 64
        self.block_size = block_size

        key = _coerce_bytes(key, 'key')

        if len(key) > block_size:
            key = cons(key).digest()
        # Right-pad with zero bytes
        key = key + b'\x00' * (block_size - len(key))

        # Pre-compute inner / outer pads
        self._inner = cons()
        self._outer = cons()
        self._inner.update(key.translate(_TRANS_36))
        self._outer.update(key.translate(_TRANS_5C))

        if msg is not None:
            self.update(msg)

    @property
    def name(self):
        return "hmac-" + self._digestmod_name

    def update(self, msg):
        msg = _coerce_bytes(msg, 'msg')
        self._inner.update(msg)

    def digest(self):
        outer = self._outer.copy()
        outer.update(self._inner.digest())
        return outer.digest()

    def hexdigest(self):
        return self.digest().hex()

    def copy(self):
        new_obj = HMAC.__new__(HMAC)
        new_obj._hash_cons = self._hash_cons
        new_obj._digestmod_name = self._digestmod_name
        new_obj.digest_size = self.digest_size
        new_obj.block_size = self.block_size
        new_obj._inner = self._inner.copy()
        new_obj._outer = self._outer.copy()
        return new_obj


# ---------------------------------------------------------------------------
# Module-level functions (stdlib hmac compatible surface)
# ---------------------------------------------------------------------------

def new(key, msg=None, digestmod=None):
    """Create a new HMAC object."""
    return HMAC(key, msg, digestmod)


def digest(key, msg, digest):
    """One-shot HMAC: returns the digest of `msg` keyed by `key`."""
    return new(key, msg, digest).digest()


def compare_digest(a, b):
    """Constant-time comparison of two strings or byte sequences."""
    # Both must be the same "kind" (str or bytes-like)
    if isinstance(a, str) and isinstance(b, str):
        try:
            a_bytes = a.encode('ascii')
            b_bytes = b.encode('ascii')
        except UnicodeEncodeError:
            raise TypeError(
                "comparing strings with non-ASCII characters is not supported"
            )
    elif isinstance(a, (bytes, bytearray, memoryview)) and \
            isinstance(b, (bytes, bytearray, memoryview)):
        a_bytes = bytes(a)
        b_bytes = bytes(b)
    else:
        raise TypeError(
            "unsupported operand types(s) or combination of types: "
            "%s and %s" % (type(a).__name__, type(b).__name__)
        )

    # Length-mismatch returns False but still does a constant-time pass
    # over the shorter input so timing does not depend on the contents.
    if len(a_bytes) != len(b_bytes):
        # Walk the shorter of the two, to avoid index errors.
        ref = a_bytes if len(a_bytes) <= len(b_bytes) else b_bytes
        result = 1
        for x in ref:
            result |= x ^ x  # constant work; preserves nonzero result
        return False

    result = 0
    for x, y in zip(a_bytes, b_bytes):
        result |= x ^ y
    return result == 0


# ---------------------------------------------------------------------------
# Behavioral invariants
# ---------------------------------------------------------------------------

def hmac2_basic():
    """Basic HMAC construction & update/hexdigest behavior."""
    try:
        # Known vector: HMAC-SHA256("key", "The quick brown fox jumps over the lazy dog")
        h = new(b'key', None, 'sha256')
        h.update(b'The quick brown fox jumps over the lazy dog')
        expected = (
            'f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8'
        )
        if h.hexdigest() != expected:
            return False

        # name + sizes
        if h.name != 'hmac-sha256':
            return False
        if h.digest_size != 32:
            return False
        if h.block_size != 64:
            return False

        # update equivalence: piecewise == one-shot
        h1 = new(b'secret', None, 'sha256')
        h1.update(b'hello ')
        h1.update(b'world')
        h2 = new(b'secret', b'hello world', 'sha256')
        if h1.digest() != h2.digest():
            return False

        # copy() yields an independent state
        c = h2.copy()
        c.update(b'!')
        if c.digest() == h2.digest():
            return False

        # Long key (longer than block size) gets hashed
        long_key = b'A' * 200
        h3 = new(long_key, b'data', 'sha256')
        # Equivalent to keying with sha256(long_key)
        hashed_key = _hashlib.sha256(long_key).digest()
        h4 = new(hashed_key, b'data', 'sha256')
        if h3.digest() != h4.digest():
            return False

        return True
    except Exception:
        return False


def hmac2_digest():
    """Digest / one-shot digest behavior including known RFC vectors."""
    try:
        # RFC 4231 Test Case 2: HMAC-SHA-256
        key = b'Jefe'
        msg = b'what do ya want for nothing?'
        expected = bytes.fromhex(
            '5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843'
        )
        if digest(key, msg, 'sha256') != expected:
            return False

        # Empty key / empty message HMAC-SHA-256
        empty = bytes.fromhex(
            'b613679a0814d9ec772f95d778c35fc5ff1697c493715653c6c712144292c5ad'
        )
        if digest(b'', b'', 'sha256') != empty:
            return False

        # digest() agrees with HMAC().digest() and hexdigest()
        d = digest(b'k', b'm', 'sha256')
        h = new(b'k', b'm', 'sha256')
        if d != h.digest():
            return False
        if d.hex() != h.hexdigest():
            return False

        # Length matches the underlying hash digest size
        if len(digest(b'k', b'm', 'sha1')) != 20:
            return False
        if len(digest(b'k', b'm', 'sha512')) != 64:
            return False
        if len(digest(b'k', b'm', 'md5')) != 16:
            return False

        # RFC 2104 Test Case 1: HMAC-MD5 with 16x 0x0b key, "Hi There"
        md5_expected = bytes.fromhex('9294727a3638bb1c13f48ef8158bfc9d')
        if digest(b'\x0b' * 16, b'Hi There', 'md5') != md5_expected:
            return False

        # digestmod as callable also works
        d2 = digest(b'k', b'm', _hashlib.sha256)
        if d2 != d:
            return False

        return True
    except Exception:
        return False


def hmac2_compare():
    """compare_digest behaves as a constant-time equality check."""
    try:
        # Equal bytes
        if not compare_digest(b'hello', b'hello'):
            return False
        # Unequal bytes, same length
        if compare_digest(b'hello', b'world'):
            return False
        # Different lengths
        if compare_digest(b'hello', b'helloo'):
            return False
        if compare_digest(b'', b'a'):
            return False
        # Equal empty
        if not compare_digest(b'', b''):
            return False
        # Strings (ASCII)
        if not compare_digest('abc', 'abc'):
            return False
        if compare_digest('abc', 'abd'):
            return False
        # bytearray / memoryview interop
        if not compare_digest(bytearray(b'xyz'), b'xyz'):
            return False
        if not compare_digest(memoryview(b'xyz'), bytearray(b'xyz')):
            return False
        # Mixed str/bytes -> TypeError
        try:
            compare_digest('abc', b'abc')
        except TypeError:
            pass
        else:
            return False
        # Non-ASCII string -> TypeError
        try:
            compare_digest('\u00e9', '\u00e9')
        except TypeError:
            pass
        else:
            return False
        # Round-trip with HMAC digests
        a = digest(b'k', b'msg', 'sha256')
        b = digest(b'k', b'msg', 'sha256')
        c = digest(b'k', b'other', 'sha256')
        if not compare_digest(a, b):
            return False
        if compare_digest(a, c):
            return False
        return True
    except Exception:
        return False


__all__ = [
    'HMAC', 'new', 'digest', 'compare_digest',
    'hmac2_basic', 'hmac2_digest', 'hmac2_compare',
]