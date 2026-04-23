"""
Clean-room implementation of base85 and base32 encoding/decoding.
No import of base64 or any third-party library.
"""

# ---------------------------------------------------------------------------
# Base32 (RFC 4648)
# ---------------------------------------------------------------------------

_B32_ALPHABET = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
_B32_DECODE_MAP = {c: i for i, c in enumerate(_B32_ALPHABET)}


def b32encode(s: bytes) -> bytes:
    """Encode bytes using base32 (RFC 4648 alphabet)."""
    if not isinstance(s, (bytes, bytearray)):
        raise TypeError("expected bytes-like object")

    result = []
    # Process 5 bytes at a time -> 8 base32 characters
    for i in range(0, len(s), 5):
        chunk = s[i:i + 5]
        n = len(chunk)

        # Pad chunk to 5 bytes
        padded = chunk + b'\x00' * (5 - n)

        # Convert 5 bytes to a 40-bit integer
        val = 0
        for byte in padded:
            val = (val << 8) | byte

        # Extract 8 groups of 5 bits
        chars = []
        for _ in range(8):
            chars.append(_B32_ALPHABET[val & 0x1F])
            val >>= 5
        chars.reverse()

        # Determine how many output chars are significant
        # 1 byte  -> 2 chars + 6 '='
        # 2 bytes -> 4 chars + 4 '='
        # 3 bytes -> 5 chars + 3 '='
        # 4 bytes -> 7 chars + 1 '='
        # 5 bytes -> 8 chars + 0 '='
        sig = {1: 2, 2: 4, 3: 5, 4: 7, 5: 8}[n]
        for j in range(8):
            if j < sig:
                result.append(chars[j])
            else:
                result.append(ord('='))

    return bytes(result)


def b32decode(s) -> bytes:
    """Decode base32-encoded bytes (RFC 4648).
    
    Accepts strings with or without padding, and normalizes padding
    to a multiple of 8 characters.
    """
    if isinstance(s, str):
        s = s.encode('ascii')
    if not isinstance(s, (bytes, bytearray)):
        raise TypeError("expected bytes-like object")

    s = s.upper()
    
    # Strip trailing padding
    stripped = s.rstrip(b'=')
    
    # Re-pad to a multiple of 8
    remainder = len(stripped) % 8
    if remainder == 0:
        s = stripped
    elif remainder == 1:
        # Invalid: 1 char can't represent any bytes
        raise ValueError("Invalid base32 string: invalid length")
    else:
        # Pad to next multiple of 8
        pad_needed = 8 - remainder
        s = stripped + b'=' * pad_needed

    if len(s) % 8 != 0:
        raise ValueError("Invalid base32 string: length must be a multiple of 8")

    result = []
    for i in range(0, len(s), 8):
        chunk = s[i:i + 8]

        # Count padding
        pad_count = chunk.count(ord('='))
        data_part = chunk[:8 - pad_count]
        pad_part = chunk[8 - pad_count:]
        if pad_part != b'=' * pad_count:
            raise ValueError("Invalid base32 padding")

        # Decode each character
        val = 0
        for c in data_part:
            if c not in _B32_DECODE_MAP:
                raise ValueError(f"Invalid base32 character: {chr(c)!r}")
            val = (val << 5) | _B32_DECODE_MAP[c]

        # Shift val to fill 40 bits
        val <<= (5 * pad_count)

        # pad_count -> bytes to produce:
        # 0 pad -> 5 bytes
        # 1 pad -> 4 bytes
        # 3 pad -> 3 bytes
        # 4 pad -> 2 bytes
        # 6 pad -> 1 byte
        n_bytes = {0: 5, 1: 4, 3: 3, 4: 2, 6: 1}
        if pad_count not in n_bytes:
            raise ValueError(f"Invalid base32 padding count: {pad_count}")
        nb = n_bytes[pad_count]

        # Extract nb bytes from the 40-bit value
        extracted = []
        for _ in range(5):
            extracted.append(val & 0xFF)
            val >>= 8
        extracted.reverse()
        result.extend(extracted[:nb])

    return bytes(result)


# ---------------------------------------------------------------------------
# Base85 (RFC 1924 variant)
# ---------------------------------------------------------------------------

_B85_ALPHABET = (
    b'0123456789'
    b'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    b'abcdefghijklmnopqrstuvwxyz'
    b'!#$%&()*+-;<=>?@^_`{|}~'
)

_B85_DECODE_MAP = {c: i for i, c in enumerate(_B85_ALPHABET)}


def b85encode(s: bytes) -> bytes:
    """Encode bytes using base85 (RFC 1924 variant)."""
    if not isinstance(s, (bytes, bytearray)):
        raise TypeError("expected bytes-like object")

    # Pad to multiple of 4
    padding = (4 - len(s) % 4) % 4
    s = s + b'\x00' * padding

    result = []
    for i in range(0, len(s), 4):
        chunk = s[i:i + 4]
        val = (chunk[0] << 24) | (chunk[1] << 16) | (chunk[2] << 8) | chunk[3]

        chars = []
        for _ in range(5):
            chars.append(_B85_ALPHABET[val % 85])
            val //= 85
        chars.reverse()
        result.extend(chars)

    # Remove the extra encoded chars corresponding to padding
    if padding:
        result = result[:-padding]

    return bytes(result)


def b85decode(s) -> bytes:
    """Decode base85-encoded bytes (RFC 1924 variant)."""
    if isinstance(s, str):
        s = s.encode('ascii')
    if not isinstance(s, (bytes, bytearray)):
        raise TypeError("expected bytes-like object")

    # Pad to multiple of 5
    padding = (5 - len(s) % 5) % 5
    s = s + bytes([_B85_ALPHABET[84]] * padding)  # pad with '~' (value 84)

    result = []
    for i in range(0, len(s), 5):
        chunk = s[i:i + 5]
        val = 0
        for c in chunk:
            if c not in _B85_DECODE_MAP:
                raise ValueError(f"Invalid base85 character: {chr(c)!r}")
            val = val * 85 + _B85_DECODE_MAP[c]

        if val > 0xFFFFFFFF:
            raise ValueError("Base85 chunk decodes to value > 2^32")

        result.append((val >> 24) & 0xFF)
        result.append((val >> 16) & 0xFF)
        result.append((val >> 8) & 0xFF)
        result.append(val & 0xFF)

    # Remove padding bytes
    if padding:
        result = result[:-padding]

    return bytes(result)


# ---------------------------------------------------------------------------
# Invariant test helpers
# ---------------------------------------------------------------------------

def base64_b32encode():
    """Encode b'hello world' and return as string."""
    return b32encode(b'hello world').decode('ascii')


def base64_b32decode():
    """Decode 'NBSWY3DP======' (which encodes b'hello') and return as string."""
    return b32decode(b'NBSWY3DP======').decode('ascii')


def base64_b32_roundtrip():
    return b32decode(b32encode(b'test')) == b'test'