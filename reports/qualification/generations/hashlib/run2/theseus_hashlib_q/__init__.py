# generation B new tuple state

_MASK = 0xFFFFFFFF

_K = (
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5,
    0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
    0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
    0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
    0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC,
    0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
    0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7,
    0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
    0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
    0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
    0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3,
    0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
    0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5,
    0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
    0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
    0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
)


def _right_rotate(value, count):
    return ((value >> count) | (value << (32 - count))) & _MASK


class _SHA256:
    name = "sha256"
    digest_size = 32
    block_size = 64

    def __init__(self, data=b""):
        self._state = (
            0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
            0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19,
        )
        self._buffer = b""
        self._length = 0
        if data:
            self.update(data)
        elif not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("a bytes-like object is required")

    def compress(self, block):
        words = [
            int.from_bytes(block[offset:offset + 4], "big")
            for offset in range(0, 64, 4)
        ]
        for index in range(16, 64):
            x = words[index - 15]
            y = words[index - 2]
            small_zero = (
                _right_rotate(x, 7) ^ _right_rotate(x, 18) ^ (x >> 3)
            )
            small_one = (
                _right_rotate(y, 17) ^ _right_rotate(y, 19) ^ (y >> 10)
            )
            words.append(
                (words[index - 16] + small_zero + words[index - 7] + small_one)
                & _MASK
            )

        a, b, c, d, e, f, g, h = self._state
        for index in range(64):
            big_one = (
                _right_rotate(e, 6)
                ^ _right_rotate(e, 11)
                ^ _right_rotate(e, 25)
            )
            choice = (e & f) ^ ((~e) & g)
            temporary_one = (
                h + big_one + choice + _K[index] + words[index]
            ) & _MASK
            big_zero = (
                _right_rotate(a, 2)
                ^ _right_rotate(a, 13)
                ^ _right_rotate(a, 22)
            )
            majority = (a & b) ^ (a & c) ^ (b & c)
            temporary_two = (big_zero + majority) & _MASK
            h, g, f, e, d, c, b, a = (
                g,
                f,
                e,
                (d + temporary_one) & _MASK,
                c,
                b,
                a,
                (temporary_one + temporary_two) & _MASK,
            )

        return tuple(
            (old + new) & _MASK
            for old, new in zip(self._state, (a, b, c, d, e, f, g, h))
        )

    def update(self, data):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("a bytes-like object is required")
        data = bytes(data)
        self._length += len(data)
        pending = self._buffer + data
        complete = len(pending) - (len(pending) % self.block_size)
        for offset in range(0, complete, self.block_size):
            self._state = self.compress(pending[offset:offset + self.block_size])
        self._buffer = pending[complete:]
        return None

    def copy(self):
        duplicate = object.__new__(_SHA256)
        duplicate._state = self._state
        duplicate._buffer = self._buffer
        duplicate._length = self._length
        return duplicate

    def digest(self):
        duplicate = self.copy()
        bit_length = (duplicate._length * 8) & 0xFFFFFFFFFFFFFFFF
        padding_size = (56 - ((duplicate._length + 1) % 64)) % 64
        final_blocks = (
            duplicate._buffer
            + b"\x80"
            + (b"\x00" * padding_size)
            + bit_length.to_bytes(8, "big")
        )
        for offset in range(0, len(final_blocks), self.block_size):
            duplicate._state = duplicate.compress(
                final_blocks[offset:offset + self.block_size]
            )
        return b"".join(word.to_bytes(4, "big") for word in duplicate._state)

    def hexdigest(self):
        return self.digest().hex()


def sha256(data=b""):
    return _SHA256(data)


__all__ = ["sha256"]
