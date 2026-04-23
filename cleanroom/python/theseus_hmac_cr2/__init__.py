"""
theseus_hmac_cr2 - Clean-room HMAC implementation per RFC 2104.
No import of hmac or any third-party library.
Uses Python standard library hashlib for hashing.
"""

import hashlib as _hashlib


def compare_digest(a, b):
    """
    Constant-time comparison of two strings or bytes objects.
    Returns True only if a and b are equal.
    """
    if isinstance(a, str):
        a = a.encode('utf-8')
    if isinstance(b, str):
        b = b.encode('utf-8')
    
    if len(a) != len(b):
        # Still iterate to avoid timing leak, but result is False
        diff = 1
        for i in range(len(a)):
            diff |= a[i] ^ a[i]
        return False
    
    diff = 0
    for i in range(len(a)):
        diff |= a[i] ^ b[i]
    
    return diff == 0


def _normalize_digestmod(digestmod):
    """Normalize digestmod name to hashlib-compatible name."""
    mapping = {
        'sha256': 'sha256',
        'SHA256': 'sha256',
        'sha-256': 'sha256',
        'sha1': 'sha1',
        'SHA1': 'sha1',
        'sha-1': 'sha1',
        'md5': 'md5',
        'MD5': 'md5',
        'sha512': 'sha512',
        'SHA512': 'sha512',
        'sha-512': 'sha512',
        'sha224': 'sha224',
        'SHA224': 'sha224',
        'sha384': 'sha384',
        'SHA384': 'sha384',
    }
    return mapping.get(digestmod, digestmod)


def _get_block_size(digestmod):
    """Return the block size for the given digest algorithm."""
    normalized = _normalize_digestmod(digestmod)
    block_sizes = {
        'sha256': 64,
        'sha1': 64,
        'md5': 64,
        'sha224': 64,
        'sha512': 128,
        'sha384': 128,
    }
    return block_sizes.get(normalized, 64)


def _new_hash(digestmod):
    """Create a new hash object for the configured digestmod."""
    normalized = _normalize_digestmod(digestmod)
    return _hashlib.new(normalized)


class HMAC:
    """
    HMAC implementation per RFC 2104.
    HMAC = H((K XOR opad) || H((K XOR ipad) || msg))
    where ipad = 0x36 repeated, opad = 0x5C repeated.
    """
    
    def __init__(self, key, msg=None, digestmod=''):
        if not digestmod:
            raise ValueError("digestmod must be specified")
        
        self._digestmod = digestmod
        
        block_size = _get_block_size(digestmod)
        
        # If key is longer than block size, hash it
        if len(key) > block_size:
            h = _new_hash(digestmod)
            h.update(key)
            key = h.digest()
        
        # If key is shorter than block size, pad with zeros
        if len(key) < block_size:
            key = key + b'\x00' * (block_size - len(key))
        
        self._key = key
        self._block_size = block_size
        
        # Compute ipad and opad keys
        ipad = bytes([b ^ 0x36 for b in key])
        opad = bytes([b ^ 0x5C for b in key])
        
        # Inner hash: H((K XOR ipad) || msg)
        self._inner = _new_hash(digestmod)
        self._inner.update(ipad)
        
        self._opad = opad
        
        if msg is not None:
            self._inner.update(msg)
    
    def update(self, msg):
        """Feed data into the HMAC."""
        self._inner.update(msg)
        return self
    
    def digest(self):
        """Return the HMAC digest as bytes."""
        inner_copy = self._inner.copy()
        inner_digest = inner_copy.digest()
        
        outer = _new_hash(self._digestmod)
        outer.update(self._opad)
        outer.update(inner_digest)
        
        return outer.digest()
    
    def hexdigest(self):
        """Return the HMAC digest as a lowercase hex string."""
        raw = self.digest()
        return ''.join('{:02x}'.format(b) for b in raw)
    
    def copy(self):
        """Return a copy of this HMAC object."""
        other = HMAC.__new__(HMAC)
        other._digestmod = self._digestmod
        other._block_size = self._block_size
        other._key = self._key
        other._opad = self._opad
        other._inner = self._inner.copy()
        return other


def new(key, msg=None, digestmod=''):
    """
    Create a new HMAC object.
    
    key: bytes - the secret key
    msg: bytes - optional initial message
    digestmod: str - hash algorithm to use (e.g., 'sha256')
    
    Returns an HMAC object.
    """
    return HMAC(key, msg=msg, digestmod=digestmod)


# Invariant functions — return actual values, not booleans

def hmac2_compare_equal():
    return compare_digest('abc', 'abc')


def hmac2_compare_unequal():
    return compare_digest('abc', 'def')


def hmac2_new_len():
    return len(new(b'key', b'msg', 'sha256').hexdigest())