# generation A in-place rounds

__all__ = ["sha256"]

_K = (
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

_INIT = (
    0x6a09e667,
    0xbb67ae85,
    0x3c6ef372,
    0xa54ff53a,
    0x510e527f,
    0x9b05688c,
    0x1f83d9ab,
    0x5be0cd19,
)


def _rotr(x, n):
    return ((x >> n) | ((x << (32 - n)) & 0xFFFFFFFF)) & 0xFFFFFFFF


def _sha256_rounds(state, block):
    """Expand block and run 64 rounds; mutate state in place."""
    w = [0] * 64
    for i in range(16):
        j = i * 4
        w[i] = (
            (block[j] << 24)
            | (block[j + 1] << 16)
            | (block[j + 2] << 8)
            | block[j + 3]
        ) & 0xFFFFFFFF

    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF

    a = state[0]
    b = state[1]
    c = state[2]
    d = state[3]
    e = state[4]
    f = state[5]
    g = state[6]
    h = state[7]

    for i in range(64):
        s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        ch = (e & f) ^ ((~e & 0xFFFFFFFF) & g)
        t1 = (h + s1 + ch + _K[i] + w[i]) & 0xFFFFFFFF
        s0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (s0 + maj) & 0xFFFFFFFF
        h = g
        g = f
        f = e
        e = (d + t1) & 0xFFFFFFFF
        d = c
        c = b
        b = a
        a = (t1 + t2) & 0xFFFFFFFF

    state[0] = (state[0] + a) & 0xFFFFFFFF
    state[1] = (state[1] + b) & 0xFFFFFFFF
    state[2] = (state[2] + c) & 0xFFFFFFFF
    state[3] = (state[3] + d) & 0xFFFFFFFF
    state[4] = (state[4] + e) & 0xFFFFFFFF
    state[5] = (state[5] + f) & 0xFFFFFFFF
    state[6] = (state[6] + g) & 0xFFFFFFFF
    state[7] = (state[7] + h) & 0xFFFFFFFF


def _state_to_digest(state):
    out = bytearray(32)
    for i in range(8):
        word = state[i]
        out[i * 4] = (word >> 24) & 0xFF
        out[i * 4 + 1] = (word >> 16) & 0xFF
        out[i * 4 + 2] = (word >> 8) & 0xFF
        out[i * 4 + 3] = word & 0xFF
    return bytes(out)


class _SHA256(object):
    name = "sha256"
    digest_size = 32
    block_size = 64

    def __init__(self, data=None):
        self._state = list(_INIT)
        self._buffer = bytearray()
        self._total_len = 0
        if data:
            self.update(data)

    def update(self, data):
        if not data:
            return self
        if isinstance(data, memoryview):
            data = data.tobytes()
        elif not isinstance(data, (bytes, bytearray)):
            data = memoryview(data).tobytes()
        self._total_len += len(data)
        self._buffer.extend(data)
        while len(self._buffer) >= 64:
            block = bytes(self._buffer[:64])
            del self._buffer[:64]
            _sha256_rounds(self._state, block)
        return self

    def _finalize_state(self):
        state = list(self._state)
        buf = bytearray(self._buffer)
        bit_len = self._total_len * 8
        buf.append(0x80)
        while (len(buf) % 64) != 56:
            buf.append(0)
        buf.extend(
            [
                (bit_len >> 56) & 0xFF,
                (bit_len >> 48) & 0xFF,
                (bit_len >> 40) & 0xFF,
                (bit_len >> 32) & 0xFF,
                (bit_len >> 24) & 0xFF,
                (bit_len >> 16) & 0xFF,
                (bit_len >> 8) & 0xFF,
                bit_len & 0xFF,
            ]
        )
        for off in range(0, len(buf), 64):
            _sha256_rounds(state, bytes(buf[off : off + 64]))
        return state

    def digest(self):
        return _state_to_digest(self._finalize_state())

    def hexdigest(self):
        return self.digest().hex()

    def copy(self):
        other = _SHA256()
        other._state = list(self._state)
        other._buffer = bytearray(self._buffer)
        other._total_len = self._total_len
        return other


def sha256(data=None):
    if data is None:
        data = b""
    return _SHA256(data)
