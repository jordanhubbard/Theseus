"""Clean-room subset of hashlib used by Theseus invariants.

This module reimplements the parts of :mod:`hashlib` that the Theseus
invariants exercise — most importantly a *real* SHA-256 — without
importing :mod:`hashlib` or any third-party library.  The other digest
names (md5, sha1, …) are exposed for API compatibility but produce a
deterministic non-cryptographic stub digest; they are not exercised by
any invariant in this package.
"""

# ---------------------------------------------------------------------------
# Algorithm registry (kept here so it is the single source of truth for
# `algorithms_available`, `algorithms_guaranteed`, and `new()`).
# ---------------------------------------------------------------------------
algorithms_guaranteed = frozenset([
    "md5", "sha1", "sha224", "sha256", "sha384", "sha512",
    "sha3_224", "sha3_256", "sha3_384", "sha3_512", "blake2b", "blake2s",
])
algorithms_available = algorithms_guaranteed


class UnsupportedDigestmodError(ValueError):
    """Raised when an unknown digest name is requested."""


# ---------------------------------------------------------------------------
# SHA-256 — full from-scratch implementation.
# ---------------------------------------------------------------------------
# Round constants: first 32 bits of the fractional parts of the cube roots of
# the first 64 primes (2..311).
_SHA256_K = (
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
)

# Initial hash state: first 32 bits of the fractional parts of the square
# roots of the first 8 primes (2..19).
_SHA256_H0 = (
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
)

_MASK32 = 0xFFFFFFFF


def _rotr32(x, n):
    return ((x >> n) | (x << (32 - n))) & _MASK32


def _sha256_compress(state, block):
    """Process one 64-byte block; return updated 8-tuple state."""
    w = [0] * 64
    for i in range(16):
        j = i * 4
        w[i] = (
            (block[j] << 24)
            | (block[j + 1] << 16)
            | (block[j + 2] << 8)
            | block[j + 3]
        )
    for i in range(16, 64):
        x = w[i - 15]
        s0 = _rotr32(x, 7) ^ _rotr32(x, 18) ^ (x >> 3)
        y = w[i - 2]
        s1 = _rotr32(y, 17) ^ _rotr32(y, 19) ^ (y >> 10)
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & _MASK32

    a, b, c, d, e, f, g, h = state
    for i in range(64):
        S1 = _rotr32(e, 6) ^ _rotr32(e, 11) ^ _rotr32(e, 25)
        ch = (e & f) ^ ((~e) & _MASK32 & g)
        t1 = (h + S1 + ch + _SHA256_K[i] + w[i]) & _MASK32
        S0 = _rotr32(a, 2) ^ _rotr32(a, 13) ^ _rotr32(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & _MASK32
        h = g
        g = f
        f = e
        e = (d + t1) & _MASK32
        d = c
        c = b
        b = a
        a = (t1 + t2) & _MASK32

    return (
        (state[0] + a) & _MASK32,
        (state[1] + b) & _MASK32,
        (state[2] + c) & _MASK32,
        (state[3] + d) & _MASK32,
        (state[4] + e) & _MASK32,
        (state[5] + f) & _MASK32,
        (state[6] + g) & _MASK32,
        (state[7] + h) & _MASK32,
    )


_HEX_CHARS = "0123456789abcdef"


def _bytes_to_hex(data):
    out = []
    for byte in data:
        out.append(_HEX_CHARS[(byte >> 4) & 0xF])
        out.append(_HEX_CHARS[byte & 0xF])
    return "".join(out)


class _Sha256Hash:
    """A real SHA-256 hash object with the standard hashlib interface."""

    name = "sha256"
    digest_size = 32
    block_size = 64

    def __init__(self, data=b""):
        self._state = _SHA256_H0
        self._buffer = b""
        self._length = 0  # total bytes consumed so far
        if data:
            self.update(data)

    @staticmethod
    def _coerce(data):
        if isinstance(data, (bytes, bytearray, memoryview)):
            return bytes(data)
        raise TypeError(
            "object supporting the buffer API required, got %s"
            % type(data).__name__
        )

    def update(self, data):
        data = self._coerce(data)
        if not data:
            return
        buf = self._buffer + data
        self._length += len(data)
        n = len(buf)
        full = n - (n % 64)
        state = self._state
        for off in range(0, full, 64):
            state = _sha256_compress(state, buf[off:off + 64])
        self._state = state
        self._buffer = buf[full:]

    def _final_state(self):
        # Pad without disturbing the live state so digest() can be reused.
        bit_len = (self._length * 8) & 0xFFFFFFFFFFFFFFFF
        buf = self._buffer + b"\x80"
        pad = (56 - len(buf)) % 64
        buf += b"\x00" * pad
        buf += bytes((
            (bit_len >> 56) & 0xFF,
            (bit_len >> 48) & 0xFF,
            (bit_len >> 40) & 0xFF,
            (bit_len >> 32) & 0xFF,
            (bit_len >> 24) & 0xFF,
            (bit_len >> 16) & 0xFF,
            (bit_len >> 8) & 0xFF,
            bit_len & 0xFF,
        ))
        state = self._state
        for off in range(0, len(buf), 64):
            state = _sha256_compress(state, buf[off:off + 64])
        return state

    def digest(self):
        state = self._final_state()
        out = bytearray(32)
        for i, word in enumerate(state):
            out[i * 4] = (word >> 24) & 0xFF
            out[i * 4 + 1] = (word >> 16) & 0xFF
            out[i * 4 + 2] = (word >> 8) & 0xFF
            out[i * 4 + 3] = word & 0xFF
        return bytes(out)

    def hexdigest(self):
        return _bytes_to_hex(self.digest())

    def copy(self):
        clone = _Sha256Hash.__new__(_Sha256Hash)
        clone._state = self._state
        clone._buffer = self._buffer
        clone._length = self._length
        return clone


# ---------------------------------------------------------------------------
# Stub hash for non-SHA-256 algorithms.  Not cryptographically meaningful;
# only present so that callers using `new("md5", …)` etc. don't blow up.
# ---------------------------------------------------------------------------
class _StubHash:
    block_size = 64

    _DIGEST_SIZES = {
        "md5": 16,
        "sha1": 20,
        "sha224": 28,
        "sha256": 32,
        "sha384": 48,
        "sha512": 64,
        "sha3_224": 28,
        "sha3_256": 32,
        "sha3_384": 48,
        "sha3_512": 64,
        "blake2b": 64,
        "blake2s": 32,
    }

    def __init__(self, name, data=b""):
        self.name = name.lower()
        self.digest_size = self._DIGEST_SIZES.get(self.name, 32)
        self._data = bytearray(data)

    def update(self, data):
        self._data.extend(data)

    def copy(self):
        return _StubHash(self.name, bytes(self._data))

    def hexdigest(self):
        seed = ("%s:%r" % (self.name, bytes(self._data))).encode("utf-8")
        value = 0
        modulus = 1 << (self.digest_size * 8)
        for byte in seed:
            value = (value * 131 + byte) % modulus
        width = self.digest_size * 2
        return ("%0*x" % (width, value))[-width:]

    def digest(self):
        hexd = self.hexdigest()
        out = bytearray(self.digest_size)
        for i in range(self.digest_size):
            out[i] = int(hexd[i * 2:i * 2 + 2], 16)
        return bytes(out)


# ---------------------------------------------------------------------------
# Public API: `new()` plus per-algorithm convenience functions.
# ---------------------------------------------------------------------------
def new(name, data=b"", *, usedforsecurity=True):
    if not isinstance(name, str):
        raise TypeError("name must be a string, got %s" % type(name).__name__)
    lname = name.lower()
    if lname not in algorithms_available:
        raise UnsupportedDigestmodError("unsupported hash type " + name)
    if lname == "sha256":
        return _Sha256Hash(data)
    return _StubHash(lname, data)


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


# ---------------------------------------------------------------------------
# Invariants.  Each returns True iff its slice of the API is healthy.
# ---------------------------------------------------------------------------
def hash2_new():
    """`new(...)` produces a usable hash object that round-trips through update/digest."""
    h = new("sha256", b"test")
    if h is None:
        return False
    if not (hasattr(h, "update") and hasattr(h, "hexdigest") and hasattr(h, "digest")):
        return False
    # Verify update + hexdigest still produces the canonical SHA-256("test").
    h2 = new("sha256")
    h2.update(b"te")
    h2.update(b"st")
    return h2.hexdigest() == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


def hash2_algorithms():
    """The advertised algorithm registry contains the expected canonical names."""
    if not isinstance(algorithms_available, frozenset):
        return False
    expected = {"md5", "sha1", "sha256", "sha512"}
    return expected.issubset(algorithms_available) and len(algorithms_available) > 5


def hash2_sha256():
    """SHA-256 of the empty string matches the FIPS 180-4 reference value."""
    empty = sha256(b"").hexdigest()
    if empty != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
        return False
    # And a non-empty reference: SHA-256("abc").
    abc = sha256(b"abc").hexdigest()
    return abc == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


__all__ = [
    "new", "md5", "sha1", "sha224", "sha256", "sha384", "sha512",
    "sha3_256", "sha3_512", "blake2b", "blake2s", "pbkdf2_hmac", "scrypt",
    "algorithms_guaranteed", "algorithms_available", "UnsupportedDigestmodError",
    "hash2_new", "hash2_algorithms", "hash2_sha256",
]