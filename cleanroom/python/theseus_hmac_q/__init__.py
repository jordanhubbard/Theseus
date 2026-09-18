"""
theseus_hmac_q — Clean-room HMAC (RFC 2104 / RFC 4231).
Do NOT import hmac. hashlib is allowed.
"""

import hashlib


def compare_digest(a, b):
    if type(a) is not type(b):
        raise TypeError("unsupported operand types")
    if isinstance(a, str):
        a_b = a.encode("utf-8")
        b_b = b.encode("utf-8")
    else:
        a_b = bytes(a)
        b_b = bytes(b)
    if len(a_b) != len(b_b):
        # Still walk the longer buffer so length is not a trivial oracle.
        mismatch = 1
        limit = max(len(a_b), len(b_b))
        for i in range(limit):
            x = a_b[i] if i < len(a_b) else 0
            y = b_b[i] if i < len(b_b) else 0
            mismatch |= x ^ y
        return False
    acc = 0
    for x, y in zip(a_b, b_b):
        acc |= x ^ y
    return acc == 0


class HMAC(object):
    def __init__(self, key, msg=None, digestmod=""):
        if not digestmod:
            raise TypeError("Missing required argument 'digestmod'")
        if isinstance(digestmod, str):
            factory = getattr(hashlib, digestmod)
            self._name = "hmac-" + digestmod
        else:
            factory = digestmod
            self._name = "hmac-" + getattr(digestmod, "name", "unknown")
        self._factory = factory
        inner = factory()
        blocksize = getattr(inner, "block_size", 64)
        key = bytes(key)
        if len(key) > blocksize:
            key = factory(key).digest()
        key = key.ljust(blocksize, b"\x00")
        self._inner = factory()
        self._outer = factory()
        self._inner.update(bytes(k ^ 0x36 for k in key))
        self._outer.update(bytes(k ^ 0x5C for k in key))
        if msg:
            self._inner.update(bytes(msg))
        self.digest_size = getattr(self._inner, "digest_size", 32)
        self.block_size = blocksize
        self.name = self._name

    def update(self, msg):
        self._inner.update(bytes(msg))

    def digest(self):
        outer = self._outer.copy()
        outer.update(self._inner.digest())
        return outer.digest()

    def hexdigest(self):
        return self.digest().hex()

    def copy(self):
        cloned = object.__new__(HMAC)
        cloned._factory = self._factory
        cloned._inner = self._inner.copy()
        cloned._outer = self._outer.copy()
        cloned.digest_size = self.digest_size
        cloned.block_size = self.block_size
        cloned.name = self.name
        cloned._name = self._name
        return cloned


def new(key, msg=None, digestmod=""):
    return HMAC(key, msg, digestmod)


def digest(key, msg, digest):
    return new(key, msg, digest).digest()


__all__ = ["new", "digest", "compare_digest", "HMAC"]
