"""
theseus_base64_cr — Clean-room base64 module.
No import of the standard `base64` module.
"""

_B64_CHARS = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
_B64_URL_CHARS = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'

_B32_CHARS = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'


def _make_decode_table(chars):
    table = [-1] * 256
    for i, c in enumerate(chars):
        table[c] = i
    return table


_B64_DECODE = _make_decode_table(_B64_CHARS)
_B64_URL_DECODE = _make_decode_table(_B64_URL_CHARS)
_B32_DECODE = _make_decode_table(_B32_CHARS)


def _b64encode_impl(s, chars):
    result = bytearray()
    n = len(s)
    i = 0
    while i < n:
        b0 = s[i]
        b1 = s[i + 1] if i + 1 < n else 0
        b2 = s[i + 2] if i + 2 < n else 0
        result.append(chars[(b0 >> 2) & 0x3F])
        result.append(chars[((b0 & 3) << 4) | ((b1 >> 4) & 0xF)])
        if i + 1 < n:
            result.append(chars[((b1 & 0xF) << 2) | ((b2 >> 6) & 3)])
        else:
            result.append(ord('='))
        if i + 2 < n:
            result.append(chars[b2 & 0x3F])
        else:
            result.append(ord('='))
        i += 3
    return bytes(result)


def _b64decode_impl(s, decode_table):
    if isinstance(s, str):
        s = s.encode('ascii')
    s = s.replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'')
    # Strip padding
    n = len(s)
    pad = 0
    while n > 0 and s[n - 1] == ord('='):
        pad += 1
        n -= 1
    result = bytearray()
    i = 0
    while i + 3 < n or (i < n and pad > 0):
        c0 = decode_table[s[i]] if i < n else 0
        c1 = decode_table[s[i + 1]] if i + 1 < n else 0
        c2 = decode_table[s[i + 2]] if i + 2 < n else 0
        c3 = decode_table[s[i + 3]] if i + 3 < n else 0
        result.append((c0 << 2) | (c1 >> 4))
        if i + 2 < n or pad < 2:
            result.append(((c1 & 0xF) << 4) | (c2 >> 2))
        if i + 3 < n or pad < 1:
            result.append(((c2 & 3) << 6) | c3)
        i += 4
    return bytes(result)


def b64encode(s):
    """Encode bytes s using Base64."""
    if isinstance(s, str):
        s = s.encode('utf-8')
    return _b64encode_impl(s, _B64_CHARS)


def b64decode(s, validate=False):
    """Decode Base64-encoded bytes."""
    return _b64decode_impl(s, _B64_DECODE)


def urlsafe_b64encode(s):
    """URL-safe Base64 encode."""
    if isinstance(s, str):
        s = s.encode('utf-8')
    return _b64encode_impl(s, _B64_URL_CHARS)


def urlsafe_b64decode(s):
    """URL-safe Base64 decode."""
    if isinstance(s, str):
        s = s.encode('ascii')
    s = s.replace(b'-', b'-').replace(b'_', b'_')
    return _b64decode_impl(s, _B64_URL_DECODE)


def b32encode(s):
    """Encode bytes s using Base32."""
    if isinstance(s, str):
        s = s.encode('utf-8')
    result = bytearray()
    n = len(s)
    i = 0
    while i < n:
        block = s[i:i + 5]
        # Pad to 5 bytes
        block = block + bytes(5 - len(block))
        b0, b1, b2, b3, b4 = block
        indices = [
            (b0 >> 3) & 0x1F,
            ((b0 & 7) << 2) | ((b1 >> 6) & 3),
            (b1 >> 1) & 0x1F,
            ((b1 & 1) << 4) | ((b2 >> 4) & 0xF),
            ((b2 & 0xF) << 1) | ((b3 >> 7) & 1),
            (b3 >> 2) & 0x1F,
            ((b3 & 3) << 3) | ((b4 >> 5) & 7),
            b4 & 0x1F,
        ]
        remaining = len(s) - i
        if remaining < 5:
            pad_count = {1: 6, 2: 4, 3: 3, 4: 1}.get(remaining, 0)
            out_chars = 8 - pad_count
        else:
            out_chars = 8
            pad_count = 0
        for j in range(out_chars):
            result.append(_B32_CHARS[indices[j]])
        result.extend(b'=' * pad_count)
        i += 5
    return bytes(result)


def b32decode(s, casefold=False):
    """Decode Base32-encoded bytes."""
    if isinstance(s, str):
        s = s.encode('ascii')
    if casefold:
        s = s.upper()
    n = len(s)
    pad = 0
    while n > 0 and s[n - 1] == ord('='):
        pad += 1
        n -= 1
    result = bytearray()
    i = 0
    while i < n:
        indices = []
        for j in range(8):
            if i + j < n:
                c = s[i + j]
                v = _B32_DECODE[c]
                if v < 0:
                    raise ValueError(f"Invalid base32 character: {chr(c)!r}")
                indices.append(v)
            else:
                indices.append(0)
        remaining = n - i
        result.append((indices[0] << 3) | (indices[1] >> 2))
        if remaining > 2:
            result.append(((indices[1] & 3) << 6) | (indices[2] << 1) | (indices[3] >> 4))
        if remaining > 4:
            result.append(((indices[3] & 0xF) << 4) | (indices[4] >> 1))
        if remaining > 5:
            result.append(((indices[4] & 1) << 7) | (indices[5] << 2) | (indices[6] >> 3))
        if remaining > 7:
            result.append(((indices[6] & 7) << 5) | indices[7])
        i += 8
    return bytes(result)


def b16encode(s):
    """Encode bytes as uppercase hex."""
    if isinstance(s, str):
        s = s.encode('utf-8')
    return s.hex().upper().encode('ascii')


def b16decode(s, casefold=False):
    """Decode hex-encoded bytes."""
    if isinstance(s, (bytes, bytearray)):
        s = s.decode('ascii')
    if casefold:
        s = s.upper()
    return bytes.fromhex(s)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def base64_2_encode():
    """b64encode(b'hello') returns b'aGVsbG8='; returns the string."""
    return b64encode(b'hello').decode('ascii')


def base64_2_decode():
    """b64decode(b'aGVsbG8=') returns b'hello'; returns the string."""
    return b64decode(b'aGVsbG8=').decode('utf-8')


def base64_2_round_trip():
    """decode(encode(data)) == data; returns True."""
    data = b'\x00\xff\x80\x7f\x01\x02\x03' * 10
    return b64decode(b64encode(data)) == data


__all__ = [
    'b64encode', 'b64decode',
    'urlsafe_b64encode', 'urlsafe_b64decode',
    'b32encode', 'b32decode',
    'b16encode', 'b16decode',
    'base64_2_encode', 'base64_2_decode', 'base64_2_round_trip',
]
