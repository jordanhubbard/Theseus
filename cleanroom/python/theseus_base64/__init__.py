# Clean-room Base64 implementation per RFC 4648
# No imports of base64 or binascii

_ALPHABET = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
_PAD = ord(b'=')


def b64encode(data: bytes) -> bytes:
    result = bytearray()
    n = len(data)
    i = 0
    while i < n:
        b0 = data[i]
        b1 = data[i + 1] if i + 1 < n else 0
        b2 = data[i + 2] if i + 2 < n else 0

        result.append(_ALPHABET[b0 >> 2])
        result.append(_ALPHABET[((b0 & 0x03) << 4) | (b1 >> 4)])
        if i + 1 < n:
            result.append(_ALPHABET[((b1 & 0x0F) << 2) | (b2 >> 6)])
        else:
            result.append(_PAD)
        if i + 2 < n:
            result.append(_ALPHABET[b2 & 0x3F])
        else:
            result.append(_PAD)

        i += 3

    return bytes(result)


# Build decode table
_DECODE_TABLE = [-1] * 256
for _i, _c in enumerate(_ALPHABET):
    _DECODE_TABLE[_c] = _i


def b64decode(data: bytes) -> bytes:
    # Strip whitespace
    data = bytes(b for b in data if b not in (ord(' '), ord('\t'), ord('\n'), ord('\r')))

    n = len(data)
    if n % 4 != 0:
        raise ValueError("Invalid base64 input: length not a multiple of 4")

    result = bytearray()
    i = 0
    while i < n:
        c0 = data[i]
        c1 = data[i + 1]
        c2 = data[i + 2]
        c3 = data[i + 3]

        v0 = _DECODE_TABLE[c0]
        v1 = _DECODE_TABLE[c1]
        v2 = _DECODE_TABLE[c2] if c2 != _PAD else 0
        v3 = _DECODE_TABLE[c3] if c3 != _PAD else 0

        if v0 < 0 or v1 < 0 or (c2 != _PAD and _DECODE_TABLE[c2] < 0) or (c3 != _PAD and _DECODE_TABLE[c3] < 0):
            raise ValueError("Invalid base64 character")

        result.append((v0 << 2) | (v1 >> 4))
        if c2 != _PAD:
            result.append(((v1 & 0x0F) << 4) | (v2 >> 2))
        if c3 != _PAD:
            result.append(((v2 & 0x03) << 6) | v3)

        i += 4

    return bytes(result)


def b64encode_hello() -> bool:
    """Encode the string 'hello' in base64 and verify the result is correct."""
    return b64encode(b'hello') == b'aGVsbG8='


def b64decode_hello() -> bool:
    """Decode the base64 encoding of 'hello' and verify the original bytes."""
    return b64decode(b'aGVsbG8=') == b'hello'


def b64_round_trip(data: bytes = b'hello world') -> bool:
    """Encode data to base64 then decode it, verifying round-trip correctness."""
    return b64decode(b64encode(data)) == data