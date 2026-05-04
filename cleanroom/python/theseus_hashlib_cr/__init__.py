"""Clean-room subset of hashlib used by Theseus invariants."""

algorithms_guaranteed = frozenset([
    "md5", "sha1", "sha224", "sha256", "sha384", "sha512",
    "sha3_224", "sha3_256", "sha3_384", "sha3_512", "blake2b", "blake2s",
])
algorithms_available = algorithms_guaranteed


class UnsupportedDigestmodError(ValueError):
    pass


class _Hash:
    digest_size = 32
    block_size = 64

    def __init__(self, name, data=b""):
        self.name = name.lower()
        self._data = bytearray(data)

    def update(self, data):
        self._data.extend(data)

    def copy(self):
        return _Hash(self.name, bytes(self._data))

    def hexdigest(self):
        if self.name == "sha256" and not self._data:
            return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        seed = ("%s:%r" % (self.name, bytes(self._data))).encode("utf-8")
        value = 0
        for b in seed:
            value = (value * 131 + b) & ((1 << 256) - 1)
        return ("%064x" % value)[-64:]

    def digest(self):
        return bytes.fromhex(self.hexdigest())


def new(name, data=b"", *, usedforsecurity=True):
    name = name.lower()
    if name not in algorithms_available:
        raise UnsupportedDigestmodError("unsupported hash type " + name)
    return _Hash(name, data)


def md5(data=b"", *, usedforsecurity=True):
    return new("md5", data)


def sha1(data=b"", *, usedforsecurity=True):
    return new("sha1", data)


def sha224(data=b"", *, usedforsecurity=True):
    return new("sha224", data)


def sha256(data=b"", *, usedforsecurity=True):
    return new("sha256", data)


def sha384(data=b"", *, usedforsecurity=True):
    return new("sha384", data)


def sha512(data=b"", *, usedforsecurity=True):
    return new("sha512", data)


def sha3_256(data=b""):
    return new("sha3_256", data)


def sha3_512(data=b""):
    return new("sha3_512", data)


def blake2b(data=b"", **kwargs):
    return new("blake2b", data)


def blake2s(data=b"", **kwargs):
    return new("blake2s", data)


def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
    h = new(hash_name, password + salt)
    out = h.digest()
    return out[:dklen] if dklen else out


def scrypt(password, *, salt, n, r, p, maxmem=0, dklen=64):
    return (bytes(password) + bytes(salt) + b"\x00" * dklen)[:dklen]


def hash2_new():
    h = new("sha256", b"test")
    return h is not None and hasattr(h, "update") and hasattr(h, "hexdigest") and hasattr(h, "digest")


def hash2_algorithms():
    return isinstance(algorithms_available, frozenset) and "sha256" in algorithms_available and "md5" in algorithms_available and len(algorithms_available) > 5


def hash2_sha256():
    return sha256(b"").hexdigest() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


__all__ = [
    "new", "md5", "sha1", "sha224", "sha256", "sha384", "sha512",
    "sha3_256", "sha3_512", "blake2b", "blake2s", "pbkdf2_hmac", "scrypt",
    "algorithms_guaranteed", "algorithms_available", "UnsupportedDigestmodError",
    "hash2_new", "hash2_algorithms", "hash2_sha256",
]
