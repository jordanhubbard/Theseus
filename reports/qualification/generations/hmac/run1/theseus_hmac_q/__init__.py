# generation A hmac class

import hashlib


def _digest_constructor(digestmod):
    if isinstance(digestmod, str):
        return getattr(hashlib, digestmod)
    return digestmod


class HMAC(object):
    def __init__(self, key, msg=None, digestmod="sha256"):
        self._digest_constructor = _digest_constructor(digestmod)
        hash_proto = self._digest_constructor()
        self.digest_size = hash_proto.digest_size
        block_size = hash_proto.block_size
        self.name = "hmac-" + hash_proto.name

        if isinstance(key, memoryview):
            key = key.tobytes()
        else:
            key = bytes(key)

        if len(key) > block_size:
            key = self._digest_constructor(key).digest()

        key = key + b"\x00" * (block_size - len(key))
        self._i_key_pad = bytes(b ^ 0x36 for b in key)
        self._o_key_pad = bytes(b ^ 0x5c for b in key)

        self._inner_hash = self._inner()
        if msg is not None:
            self.update(msg)

    def _inner(self):
        inner = self._digest_constructor()
        inner.update(self._i_key_pad)
        return inner

    def _outer(self):
        outer = self._digest_constructor()
        outer.update(self._o_key_pad)
        return outer

    def update(self, msg):
        if isinstance(msg, memoryview):
            msg = msg.tobytes()
        self._inner_hash.update(msg)

    def copy(self):
        duplicate = self.__class__.__new__(self.__class__)
        duplicate._digest_constructor = self._digest_constructor
        duplicate.digest_size = self.digest_size
        duplicate.name = self.name
        duplicate._i_key_pad = self._i_key_pad
        duplicate._o_key_pad = self._o_key_pad
        duplicate._inner_hash = self._inner_hash.copy()
        return duplicate

    def digest(self):
        inner_digest = self._inner_hash.digest()
        outer = self._outer()
        outer.update(inner_digest)
        return outer.digest()

    def hexdigest(self):
        return self.digest().hex()


def new(key, msg=None, digestmod="sha256"):
    return HMAC(key, msg, digestmod)


def digest(key, msg, digestmod):
    return new(key, msg, digestmod).digest()


def compare_digest(a, b):
    if isinstance(a, str):
        if not isinstance(b, str):
            raise TypeError(
                "supported types for compare_digest: str, bytes, bytearray"
            )
        if len(a) != len(b):
            return False
        result = 0
        for left, right in zip(a, b):
            result |= ord(left) ^ ord(right)
        return result == 0
    if isinstance(a, (bytes, bytearray)):
        if type(a) is not type(b):
            raise TypeError(
                "supported types for compare_digest: str, bytes, bytearray"
            )
        if len(a) != len(b):
            return False
        result = 0
        for left, right in zip(a, b):
            result |= left ^ right
        return result == 0
    raise TypeError(
        "supported types for compare_digest: str, bytes, bytearray"
    )
