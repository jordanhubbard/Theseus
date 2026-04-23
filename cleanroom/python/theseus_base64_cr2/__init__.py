"""
theseus_base64_cr2 - Clean-room implementation of Base32 and URL-safe Base64 encoding/decoding.
"""

# Base32 alphabet: A-Z + 2-7
_B32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
_B32_DECODE_MAP = {ch: i for i, ch in enumerate(_B32_ALPHABET)}

# Standard Base64 alphabet
_B64_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
# URL-safe Base64 alphabet (replace + with - and / with _)
_B64_URLSAFE_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
_B64_URLSAFE_DECODE_MAP = {ch: i for i, ch in enumerate(_B64_URLSAFE_ALPHABET)}


def b32encode(b: bytes) -> str:
    """Encode bytes as Base32 (uppercase A-Z + 2-7)."""
    if not isinstance(b, (bytes, bytearray)):
        raise TypeError("b must be bytes or bytearray")
    
    # Convert bytes to a big integer bit stream
    bits = 0
    bit_count = 0
    result = []
    
    for byte in b:
        bits = (bits << 8) | byte
        bit_count += 8
        
        while bit_count >= 5:
            bit_count -= 5
            index = (bits >> bit_count) & 0x1F
            result.append(_B32_ALPHABET[index])
    
    # Handle remaining bits (pad with zeros)
    if bit_count > 0:
        index = (bits << (5 - bit_count)) & 0x1F
        result.append(_B32_ALPHABET[index])
    
    # Add padding to make length a multiple of 8
    encoded = ''.join(result)
    padding_needed = (8 - len(encoded) % 8) % 8
    encoded += '=' * padding_needed
    
    return encoded


def b32decode(s: str) -> bytes:
    """Decode Base32 string back to bytes."""
    if isinstance(s, bytes):
        s = s.decode('ascii')
    
    # Remove padding
    s = s.upper().rstrip('=')
    
    bits = 0
    bit_count = 0
    result = []
    
    for ch in s:
        if ch not in _B32_DECODE_MAP:
            raise ValueError(f"Invalid Base32 character: {ch!r}")
        bits = (bits << 5) | _B32_DECODE_MAP[ch]
        bit_count += 5
        
        if bit_count >= 8:
            bit_count -= 8
            result.append((bits >> bit_count) & 0xFF)
    
    return bytes(result)


def urlsafe_b64encode(b: bytes) -> str:
    """Base64 encode with - and _ instead of + and /."""
    if not isinstance(b, (bytes, bytearray)):
        raise TypeError("b must be bytes or bytearray")
    
    bits = 0
    bit_count = 0
    result = []
    
    for byte in b:
        bits = (bits << 8) | byte
        bit_count += 8
        
        while bit_count >= 6:
            bit_count -= 6
            index = (bits >> bit_count) & 0x3F
            result.append(_B64_URLSAFE_ALPHABET[index])
    
    # Handle remaining bits
    if bit_count > 0:
        index = (bits << (6 - bit_count)) & 0x3F
        result.append(_B64_URLSAFE_ALPHABET[index])
    
    # Add padding to make length a multiple of 4
    encoded = ''.join(result)
    padding_needed = (4 - len(encoded) % 4) % 4
    encoded += '=' * padding_needed
    
    return encoded


def urlsafe_b64decode(s: str) -> bytes:
    """Decode URL-safe Base64 string."""
    if isinstance(s, bytes):
        s = s.decode('ascii')
    
    # Remove padding
    s = s.rstrip('=')
    
    bits = 0
    bit_count = 0
    result = []
    
    for ch in s:
        if ch not in _B64_URLSAFE_DECODE_MAP:
            raise ValueError(f"Invalid URL-safe Base64 character: {ch!r}")
        bits = (bits << 6) | _B64_URLSAFE_DECODE_MAP[ch]
        bit_count += 6
        
        if bit_count >= 8:
            bit_count -= 8
            result.append((bits >> bit_count) & 0xFF)
    
    return bytes(result)


def base64_cr2_b32_roundtrip() -> bool:
    """Test that b32decode(b32encode(b'hello')) == b'hello'."""
    return b32decode(b32encode(b'hello')) == b'hello'


def base64_cr2_urlsafe_encode() -> bool:
    """Test that urlsafe_b64encode(b'\\xfb\\xff') contains only [A-Za-z0-9_-]."""
    import re
    encoded = urlsafe_b64encode(b'\xfb\xff')
    return bool(re.match(r'^[A-Za-z0-9_\-=]*$', encoded))


def base64_cr2_urlsafe_roundtrip() -> bool:
    """Test that urlsafe_b64decode(urlsafe_b64encode(b'test')) == b'test'."""
    return urlsafe_b64decode(urlsafe_b64encode(b'test')) == b'test'