# generation B pad functions
import hashlib


def _hash_new(digestmod, data=b""):
    if isinstance(digestmod, str):
        return hashlib.new(digestmod, data)
    return digestmod(data)


def _pad_key(key, digestmod):
    if not isinstance(key, (bytes, bytearray)):
        raise TypeError("key must be bytes or bytearray")
    probe = _hash_new(digestmod)
    block_size = probe.block_size
    raw = bytes(key)
    if len(raw) > block_size:
        hashed = _hash_new(digestmod)
        hashed.update(raw)
        raw = hashed.digest()
    return raw + b"\x00" * (block_size - len(raw))


def _sign(key, msg, digestmod):
    padded = _pad_key(key, digestmod)
    inside = bytes(value ^ 0x36 for value in padded)
    outside = bytes(value ^ 0x5C for value in padded)
    first = _hash_new(digestmod)
    first.update(inside)
    first.update(msg)
    second = _hash_new(digestmod)
    second.update(outside)
    second.update(first.digest())
    return second.digest()


class _Mac:
    def __init__(self, key, msg=None, digestmod="sha256"):
        padded = _pad_key(key, digestmod)
        self._digestmod = digestmod
        self._inside = _hash_new(digestmod)
        self._outside = _hash_new(digestmod)
        self._inside.update(bytes(value ^ 0x36 for value in padded))
        self._outside.update(bytes(value ^ 0x5C for value in padded))
        probe = _hash_new(digestmod)
        self.digest_size = probe.digest_size
        self.block_size = probe.block_size
        self.name = "hmac-" + probe.name
        if msg is not None:
            self.update(msg)

    def update(self, data):
        self._inside.update(data)

    def digest(self):
        first = self._inside.copy().digest()
        second = self._outside.copy()
        second.update(first)
        return second.digest()

    def hexdigest(self):
        return self.digest().hex()

    def copy(self):
        duplicate = object.__new__(_Mac)
        duplicate._digestmod = self._digestmod
        duplicate._inside = self._inside.copy()
        duplicate._outside = self._outside.copy()
        duplicate.digest_size = self.digest_size
        duplicate.block_size = self.block_size
        duplicate.name = self.name
        return duplicate


def new(key, msg=None, digestmod="sha256"):
    return _Mac(key, msg, digestmod)


def digest(key, msg, digestmod):
    return _sign(key, msg, digestmod)


def compare_digest(a, b):
    if isinstance(a, str) and isinstance(b, str):
        left = [ord(char) for char in a]
        right = [ord(char) for char in b]
    elif isinstance(a, bytes) and isinstance(b, bytes):
        left = a
        right = b
    else:
        raise TypeError("both arguments must be str or both must be bytes")

    difference = len(left) ^ len(right)
    extent = max(len(left), len(right))
    for index in range(extent):
        left_value = left[index] if index < len(left) else 0
        right_value = right[index] if index < len(right) else 0
        difference |= left_value ^ right_value
    return difference == 0


HMAC = _Mac
