"""
theseus_base64_cr4 - Clean-room base64 implementation without importing base64.
"""

# Standard base64 alphabet
_B64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_B64_URLSAFE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

# Base32 alphabet
_B32_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def b64encode(s: bytes) -> bytes:
    """Encode bytes to standard base64."""
    if not isinstance(s, (bytes, bytearray)):
        raise TypeError("expected bytes-like object")
    
    result = []
    alphabet = _B64_CHARS
    
    # Process 3 bytes at a time
    for i in range(0, len(s), 3):
        chunk = s[i:i+3]
        n = len(chunk)
        
        if n == 3:
            b0, b1, b2 = chunk[0], chunk[1], chunk[2]
            result.append(alphabet[(b0 >> 2) & 0x3F])
            result.append(alphabet[((b0 & 0x03) << 4) | ((b1 >> 4) & 0x0F)])
            result.append(alphabet[((b1 & 0x0F) << 2) | ((b2 >> 6) & 0x03)])
            result.append(alphabet[b2 & 0x3F])
        elif n == 2:
            b0, b1 = chunk[0], chunk[1]
            result.append(alphabet[(b0 >> 2) & 0x3F])
            result.append(alphabet[((b0 & 0x03) << 4) | ((b1 >> 4) & 0x0F)])
            result.append(alphabet[((b1 & 0x0F) << 2)])
            result.append('=')
        elif n == 1:
            b0 = chunk[0]
            result.append(alphabet[(b0 >> 2) & 0x3F])
            result.append(alphabet[((b0 & 0x03) << 4)])
            result.append('=')
            result.append('=')
    
    return ''.join(result).encode('ascii')


def b64decode(s) -> bytes:
    """Decode standard base64 bytes."""
    if isinstance(s, (bytes, bytearray)):
        s = s.decode('ascii')
    elif not isinstance(s, str):
        raise TypeError("expected str, bytes or bytearray")
    
    # Strip whitespace
    s = s.strip()
    
    # Build decode table
    decode_table = {c: i for i, c in enumerate(_B64_CHARS)}
    
    # Validate and decode
    result = []
    
    # Pad to multiple of 4
    padding = len(s) % 4
    if padding == 2:
        s += '=='
    elif padding == 3:
        s += '='
    elif padding == 1:
        raise ValueError("Invalid base64 string")
    
    for i in range(0, len(s), 4):
        chunk = s[i:i+4]
        
        c0, c1, c2, c3 = chunk[0], chunk[1], chunk[2], chunk[3]
        
        if c0 not in decode_table or c1 not in decode_table:
            raise ValueError(f"Invalid base64 character")
        
        v0 = decode_table[c0]
        v1 = decode_table[c1]
        
        result.append((v0 << 2) | (v1 >> 4))
        
        if c2 != '=':
            if c2 not in decode_table:
                raise ValueError(f"Invalid base64 character")
            v2 = decode_table[c2]
            result.append(((v1 & 0x0F) << 4) | (v2 >> 2))
            
            if c3 != '=':
                if c3 not in decode_table:
                    raise ValueError(f"Invalid base64 character")
                v3 = decode_table[c3]
                result.append(((v2 & 0x03) << 6) | v3)
    
    return bytes(result)


def urlsafe_b64encode(s: bytes) -> bytes:
    """Encode bytes using URL-safe base64 alphabet (- and _ instead of + and /)."""
    encoded = b64encode(s).decode('ascii')
    encoded = encoded.replace('+', '-').replace('/', '_')
    return encoded.encode('ascii')


def urlsafe_b64decode(s) -> bytes:
    """Decode URL-safe base64 bytes."""
    if isinstance(s, (bytes, bytearray)):
        s = s.decode('ascii')
    elif not isinstance(s, str):
        raise TypeError("expected str, bytes or bytearray")
    
    # Replace URL-safe chars with standard base64 chars
    s = s.replace('-', '+').replace('_', '/')
    return b64decode(s)


def b32encode(s: bytes) -> bytes:
    """Encode bytes to base32."""
    if not isinstance(s, (bytes, bytearray)):
        raise TypeError("expected bytes-like object")
    
    alphabet = _B32_CHARS
    result = []
    
    # Process 5 bytes at a time -> 8 base32 chars
    for i in range(0, len(s), 5):
        chunk = s[i:i+5]
        n = len(chunk)
        
        # Pad chunk to 5 bytes
        padded = chunk + b'\x00' * (5 - n)
        b0, b1, b2, b3, b4 = padded[0], padded[1], padded[2], padded[3], padded[4]
        
        # Extract 5-bit groups
        indices = [
            (b0 >> 3) & 0x1F,
            ((b0 & 0x07) << 2) | ((b1 >> 6) & 0x03),
            (b1 >> 1) & 0x1F,
            ((b1 & 0x01) << 4) | ((b2 >> 4) & 0x0F),
            ((b2 & 0x0F) << 1) | ((b3 >> 7) & 0x01),
            (b3 >> 2) & 0x1F,
            ((b3 & 0x03) << 3) | ((b4 >> 5) & 0x07),
            b4 & 0x1F,
        ]
        
        # Determine how many output chars based on input length
        if n == 5:
            chars_used = 8
        elif n == 4:
            chars_used = 7
        elif n == 3:
            chars_used = 5
        elif n == 2:
            chars_used = 4
        elif n == 1:
            chars_used = 2
        else:
            chars_used = 0
        
        for j in range(chars_used):
            result.append(alphabet[indices[j]])
        
        # Add padding
        padding_needed = 8 - chars_used
        result.extend(['='] * padding_needed)
    
    return ''.join(result).encode('ascii')


def b32decode(s) -> bytes:
    """Decode base32 bytes."""
    if isinstance(s, (bytes, bytearray)):
        s = s.decode('ascii')
    elif not isinstance(s, str):
        raise TypeError("expected str, bytes or bytearray")
    
    s = s.strip().upper()
    
    # Build decode table
    decode_table = {c: i for i, c in enumerate(_B32_CHARS)}
    
    result = []
    
    # Pad to multiple of 8
    padding = len(s) % 8
    if padding != 0:
        s += '=' * (8 - padding)
    
    for i in range(0, len(s), 8):
        chunk = s[i:i+8]
        
        # Count padding
        pad_count = chunk.count('=')
        
        # Decode non-padding chars
        values = []
        for c in chunk:
            if c == '=':
                values.append(0)
            elif c in decode_table:
                values.append(decode_table[c])
            else:
                raise ValueError(f"Invalid base32 character: {c}")
        
        v0, v1, v2, v3, v4, v5, v6, v7 = values
        
        # Reconstruct bytes
        b0 = ((v0 << 3) | (v1 >> 2)) & 0xFF
        b1 = ((v1 << 6) | (v2 << 1) | (v3 >> 4)) & 0xFF
        b2 = ((v3 << 4) | (v4 >> 1)) & 0xFF
        b3 = ((v4 << 7) | (v5 << 2) | (v6 >> 3)) & 0xFF
        b4 = ((v6 << 5) | v7) & 0xFF
        
        if pad_count == 0:
            result.extend([b0, b1, b2, b3, b4])
        elif pad_count == 1:
            result.extend([b0, b1, b2, b3])
        elif pad_count == 3:
            result.extend([b0, b1, b2])
        elif pad_count == 4:
            result.extend([b0, b1])
        elif pad_count == 6:
            result.extend([b0])
    
    return bytes(result)


# Invariant functions (zero-arg)
def base64_4_urlsafe_encode():
    return urlsafe_b64encode(b'\xfb\xff').decode()


def base64_4_urlsafe_decode():
    return urlsafe_b64decode('-_8=') == b'\xfb\xff'


def base64_4_urlsafe_roundtrip():
    return urlsafe_b64decode(urlsafe_b64encode(b'hello')) == b'hello'