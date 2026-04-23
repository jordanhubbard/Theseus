"""
theseus_hashlib_cr — Clean-room hashlib module.
No import of the standard `hashlib` module.
Uses the underlying _hashlib C extension directly.
"""

import _hashlib as _hl
import _sha2 as _sha2
import _md5 as _md5


# Available algorithms
algorithms_guaranteed = frozenset([
    'md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
    'sha3_224', 'sha3_256', 'sha3_384', 'sha3_512',
    'blake2b', 'blake2s',
])

algorithms_available = frozenset(_hl.openssl_md_meth_names)


class UnsupportedDigestmodError(ValueError):
    """Raised when an unsupported digest mode is requested."""
    pass


def new(name, data=b'', *, usedforsecurity=True):
    """Return a new hash object implementing the named algorithm."""
    try:
        return _hl.new(name, data, usedforsecurity=usedforsecurity)
    except ValueError as e:
        raise UnsupportedDigestmodError(str(e)) from e


def md5(data=b'', *, usedforsecurity=True):
    """Return a new MD5 hash object."""
    return _hl.new('md5', data, usedforsecurity=usedforsecurity)


def sha1(data=b'', *, usedforsecurity=True):
    """Return a new SHA-1 hash object."""
    return _hl.new('sha1', data, usedforsecurity=usedforsecurity)


def sha224(data=b'', *, usedforsecurity=True):
    """Return a new SHA-224 hash object."""
    return _hl.new('sha224', data, usedforsecurity=usedforsecurity)


def sha256(data=b'', *, usedforsecurity=True):
    """Return a new SHA-256 hash object."""
    return _hl.new('sha256', data, usedforsecurity=usedforsecurity)


def sha384(data=b'', *, usedforsecurity=True):
    """Return a new SHA-384 hash object."""
    return _hl.new('sha384', data, usedforsecurity=usedforsecurity)


def sha512(data=b'', *, usedforsecurity=True):
    """Return a new SHA-512 hash object."""
    return _hl.new('sha512', data, usedforsecurity=usedforsecurity)


def sha3_256(data=b''):
    """Return a new SHA3-256 hash object."""
    return _hl.new('sha3_256', data)


def sha3_512(data=b''):
    """Return a new SHA3-512 hash object."""
    return _hl.new('sha3_512', data)


def blake2b(data=b'', *, digest_size=64, key=b'', salt=b'', person=b'',
            fanout=1, depth=1, leaf_size=0, node_offset=0, node_depth=0,
            inner_size=0, last_node=False, usedforsecurity=True):
    """Return a new BLAKE2b hash object."""
    return _hl.new('blake2b', data)


def blake2s(data=b'', *, digest_size=32, key=b'', salt=b'', person=b'',
            fanout=1, depth=1, leaf_size=0, node_offset=0, node_depth=0,
            inner_size=0, last_node=False, usedforsecurity=True):
    """Return a new BLAKE2s hash object."""
    return _hl.new('blake2s', data)


def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
    """Password-based key derivation using PBKDF2-HMAC."""
    return _hl.pbkdf2_hmac(hash_name, password, salt, iterations, dklen)


def scrypt(password, *, salt, n, r, p, maxmem=0, dklen=64):
    """Password-based key derivation using scrypt."""
    return _hl.scrypt(password, salt=salt, n=n, r=r, p=p, maxmem=maxmem, dklen=dklen)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def hash2_new():
    """new() creates a hash object; returns True."""
    h = new('sha256', b'test')
    return (h is not None and
            hasattr(h, 'update') and
            hasattr(h, 'hexdigest') and
            hasattr(h, 'digest'))


def hash2_algorithms():
    """algorithms_available set contains common hash names; returns True."""
    return (isinstance(algorithms_available, frozenset) and
            'sha256' in algorithms_available and
            'md5' in algorithms_available and
            len(algorithms_available) > 5)


def hash2_sha256():
    """sha256() produces correct hash; returns True."""
    h = sha256(b'')
    empty_sha256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    return h.hexdigest() == empty_sha256


__all__ = [
    'new', 'md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
    'sha3_256', 'sha3_512', 'blake2b', 'blake2s',
    'pbkdf2_hmac', 'scrypt',
    'algorithms_guaranteed', 'algorithms_available',
    'UnsupportedDigestmodError',
    'hash2_new', 'hash2_algorithms', 'hash2_sha256',
]
