# Clean-room base64 / base32 implementation for theseus_base64_cr.
# Does NOT import the standard library `base64` module.

_B64_STD_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_B64_URL_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_B32_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _build_decode_table(alphabet):
    table = [-1] * 256
    for i, ch in enumerate(alphabet):
        table[ch] = i
    return table


_B64_STD_DECODE = _build_decode_table(_B64_STD_ALPHABET)
_B64_URL_DECODE = _build_decode_table(_B64_URL_ALPHABET)
_B32_DECODE = _build_decode_table(_B32_ALPHABET)


def _to_bytes(s):
    if isinstance(s, str):
        return s.encode("ascii")
    if isinstance(s, (bytes, bytearray, memoryview)):
        return bytes(s)
    raise TypeError("expected bytes-like object or str")


def _b64_encode_with_alphabet(data, alphabet):
    data = _to_bytes(data)
    out = bytearray()
    n = len(data)
    i = 0
    # process full 3-byte groups
    while i + 3 <= n:
        b0 = data[i]
        b1 = data[i + 1]
        b2 = data[i + 2]
        out.append(alphabet[(b0 >> 2) & 0x3F])
        out.append(alphabet[((b0 << 4) & 0x30) | ((b1 >> 4) & 0x0F)])
        out.append(alphabet[((b1 << 2) & 0x3C) | ((b2 >> 6) & 0x03)])
        out.append(alphabet[b2 & 0x3F])
        i += 3
    rem = n - i
    if rem == 1:
        b0 = data[i]
        out.append(alphabet[(b0 >> 2) & 0x3F])
        out.append(alphabet[(b0 << 4) & 0x30])
        out.append(ord("="))
        out.append(ord("="))
    elif rem == 2:
        b0 = data[i]
        b1 = data[i + 1]
        out.append(alphabet[(b0 >> 2) & 0x3F])
        out.append(alphabet[((b0 << 4) & 0x30) | ((b1 >> 4) & 0x0F)])
        out.append(alphabet[(b1 << 2) & 0x3C])
        out.append(ord("="))
    return bytes(out)


def _b64_decode_with_table(data, table):
    data = _to_bytes(data)
    # Strip ASCII whitespace
    cleaned = bytearray()
    for ch in data:
        if ch in (0x20, 0x09, 0x0A, 0x0D, 0x0B, 0x0C):
            continue
        cleaned.append(ch)
    if len(cleaned) % 4 != 0:
        raise ValueError("Invalid base64-encoded data: length not a multiple of 4")
    out = bytearray()
    i = 0
    n = len(cleaned)
    while i < n:
        c0 = cleaned[i]
        c1 = cleaned[i + 1]
        c2 = cleaned[i + 2]
        c3 = cleaned[i + 3]
        i += 4

        if c0 == 0x3D or c1 == 0x3D:
            raise ValueError("Invalid base64-encoded data: misplaced padding")

        v0 = table[c0]
        v1 = table[c1]
        if v0 < 0 or v1 < 0:
            raise ValueError("Invalid base64-encoded data: non-alphabet character")

        if c2 == 0x3D:
            if c3 != 0x3D:
                raise ValueError("Invalid base64-encoded data: padding mismatch")
            if i != n:
                raise ValueError("Invalid base64-encoded data: padding before end")
            out.append(((v0 << 2) | (v1 >> 4)) & 0xFF)
        elif c3 == 0x3D:
            v2 = table[c2]
            if v2 < 0:
                raise ValueError("Invalid base64-encoded data: non-alphabet character")
            if i != n:
                raise ValueError("Invalid base64-encoded data: padding before end")
            out.append(((v0 << 2) | (v1 >> 4)) & 0xFF)
            out.append(((v1 << 4) | (v2 >> 2)) & 0xFF)
        else:
            v2 = table[c2]
            v3 = table[c3]
            if v2 < 0 or v3 < 0:
                raise ValueError("Invalid base64-encoded data: non-alphabet character")
            out.append(((v0 << 2) | (v1 >> 4)) & 0xFF)
            out.append(((v1 << 4) | (v2 >> 2)) & 0xFF)
            out.append(((v2 << 6) | v3) & 0xFF)
    return bytes(out)


def b64encode(s):
    """Encode bytes-like object using standard Base64 and return bytes."""
    return _b64_encode_with_alphabet(s, _B64_STD_ALPHABET)


def b64decode(s):
    """Decode standard Base64 input and return bytes."""
    return _b64_decode_with_table(s, _B64_STD_DECODE)


def urlsafe_b64encode(s):
    """Encode bytes-like object using URL-safe Base64 and return bytes."""
    return _b64_encode_with_alphabet(s, _B64_URL_ALPHABET)


def urlsafe_b64decode(s):
    """Decode URL-safe Base64 input and return bytes."""
    return _b64_decode_with_table(s, _B64_URL_DECODE)


def b32encode(s):
    """Encode bytes-like object using Base32 and return bytes."""
    data = _to_bytes(s)
    out = bytearray()
    n = len(data)
    i = 0
    # Process full 5-byte groups -> 8 chars
    while i + 5 <= n:
        b0 = data[i]
        b1 = data[i + 1]
        b2 = data[i + 2]
        b3 = data[i + 3]
        b4 = data[i + 4]
        out.append(_B32_ALPHABET[(b0 >> 3) & 0x1F])
        out.append(_B32_ALPHABET[((b0 << 2) & 0x1C) | ((b1 >> 6) & 0x03)])
        out.append(_B32_ALPHABET[(b1 >> 1) & 0x1F])
        out.append(_B32_ALPHABET[((b1 << 4) & 0x10) | ((b2 >> 4) & 0x0F)])
        out.append(_B32_ALPHABET[((b2 << 1) & 0x1E) | ((b3 >> 7) & 0x01)])
        out.append(_B32_ALPHABET[(b3 >> 2) & 0x1F])
        out.append(_B32_ALPHABET[((b3 << 3) & 0x18) | ((b4 >> 5) & 0x07)])
        out.append(_B32_ALPHABET[b4 & 0x1F])
        i += 5
    rem = n - i
    if rem > 0:
        # Pad input with zero bytes to reach 5
        chunk = bytearray(data[i:]) + bytearray(5 - rem)
        b0, b1, b2, b3, b4 = chunk[0], chunk[1], chunk[2], chunk[3], chunk[4]
        chars = [
            _B32_ALPHABET[(b0 >> 3) & 0x1F],
            _B32_ALPHABET[((b0 << 2) & 0x1C) | ((b1 >> 6) & 0x03)],
            _B32_ALPHABET[(b1 >> 1) & 0x1F],
            _B32_ALPHABET[((b1 << 4) & 0x10) | ((b2 >> 4) & 0x0F)],
            _B32_ALPHABET[((b2 << 1) & 0x1E) | ((b3 >> 7) & 0x01)],
            _B32_ALPHABET[(b3 >> 2) & 0x1F],
            _B32_ALPHABET[((b3 << 3) & 0x18) | ((b4 >> 5) & 0x07)],
            _B32_ALPHABET[b4 & 0x1F],
        ]
        # Number of valid (non-pad) characters depending on rem
        if rem == 1:
            valid = 2
        elif rem == 2:
            valid = 4
        elif rem == 3:
            valid = 5
        elif rem == 4:
            valid = 7
        else:
            valid = 8
        for j in range(valid):
            out.append(chars[j])
        for _ in range(8 - valid):
            out.append(ord("="))
    return bytes(out)


def b32decode(s, casefold=False):
    """Decode Base32-encoded input and return bytes."""
    data = _to_bytes(s)
    if len(data) % 8 != 0:
        raise ValueError("Invalid base32-encoded data: length not a multiple of 8")
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        block = data[i:i + 8]
        i += 8
        # Find padding count at end of this block
        pad_count = 0
        for j in range(7, -1, -1):
            if block[j] == 0x3D:
                pad_count += 1
            else:
                break
        if pad_count not in (0, 1, 3, 4, 6):
            raise ValueError("Invalid base32-encoded data: invalid padding")
        if pad_count > 0 and i != n:
            raise ValueError("Invalid base32-encoded data: padding before end")

        vals = [0] * 8
        for j in range(8 - pad_count):
            ch = block[j]
            if casefold and 0x61 <= ch <= 0x7A:
                ch = ch - 32
            v = _B32_DECODE[ch]
            if v < 0:
                raise ValueError("Invalid base32-encoded data: non-alphabet character")
            vals[j] = v

        # Reconstruct up to 5 bytes from 8 5-bit groups
        b0 = ((vals[0] << 3) | (vals[1] >> 2)) & 0xFF
        b1 = ((vals[1] << 6) | (vals[2] << 1) | (vals[3] >> 4)) & 0xFF
        b2 = ((vals[3] << 4) | (vals[4] >> 1)) & 0xFF
        b3 = ((vals[4] << 7) | (vals[5] << 2) | (vals[6] >> 3)) & 0xFF
        b4 = ((vals[6] << 5) | vals[7]) & 0xFF

        if pad_count == 0:
            out.extend([b0, b1, b2, b3, b4])
        elif pad_count == 1:
            out.extend([b0, b1, b2, b3])
        elif pad_count == 3:
            out.extend([b0, b1, b2])
        elif pad_count == 4:
            out.extend([b0, b1])
        elif pad_count == 6:
            out.append(b0)
    return bytes(out)


# ---------------------------------------------------------------------------
# Invariant helpers
# ---------------------------------------------------------------------------

def base64_2_encode():
    """Encode the literal bytes b'hello' and return the base64 string 'aGVsbG8='."""
    return b64encode(b"hello").decode("ascii")


def base64_2_decode():
    """Decode 'aGVsbG8=' and return the resulting string 'hello'."""
    return b64decode(b"aGVsbG8=").decode("ascii")


def base64_2_round_trip():
    """Round-trip a sample payload through encode/decode and confirm equality."""
    sample = b"hello"
    return b64decode(b64encode(sample)) == sample