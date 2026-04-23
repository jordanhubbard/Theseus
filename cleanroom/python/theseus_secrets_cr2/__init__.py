import os
import math

def token_bytes(nbytes=32):
    """Return nbytes random bytes."""
    return os.urandom(nbytes)

def token_hex(nbytes=32):
    """Return a random hex string of 2*nbytes hex digits."""
    return token_bytes(nbytes).hex()

def token_urlsafe(nbytes=32):
    """Return URL-safe base64 token from nbytes of random bytes."""
    data = os.urandom(nbytes)
    # Implement base64 URL-safe encoding manually
    # Base64 alphabet (URL-safe): A-Z, a-z, 0-9, -, _
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    
    result = []
    # Process 3 bytes at a time
    i = 0
    n = len(data)
    while i < n:
        # Get up to 3 bytes
        b0 = data[i]
        b1 = data[i+1] if i+1 < n else 0
        b2 = data[i+2] if i+2 < n else 0
        
        # Encode 4 base64 characters
        result.append(alphabet[(b0 >> 2) & 0x3F])
        result.append(alphabet[((b0 & 0x03) << 4) | ((b1 >> 4) & 0x0F)])
        result.append(alphabet[((b1 & 0x0F) << 2) | ((b2 >> 6) & 0x03)])
        result.append(alphabet[b2 & 0x3F])
        
        i += 3
    
    # Calculate actual length without padding
    # For nbytes bytes: ceil(nbytes * 4 / 3) characters (no padding)
    encoded = ''.join(result)
    # Remove padding equivalent: trim to actual encoded length
    # Standard base64 length without padding
    actual_len = math.ceil(nbytes * 4 / 3)
    return encoded[:actual_len]

def compare_digest(a, b):
    """Constant-time comparison of strings or bytes."""
    if type(a) != type(b):
        raise TypeError("a and b must be the same type")
    
    if len(a) != len(b):
        return False
    
    result = 0
    if isinstance(a, bytes):
        for x, y in zip(a, b):
            result |= x ^ y
    else:
        # strings
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
    
    return result == 0

def randbits(k):
    """Return k random bits as integer using os.urandom."""
    if k <= 0:
        return 0
    nbytes = math.ceil(k / 8)
    raw = os.urandom(nbytes)
    # Convert bytes to integer
    value = int.from_bytes(raw, byteorder='big')
    # Extract only k bits (mask to k bits)
    value = value >> (nbytes * 8 - k)
    return value

# Invariant check functions
def secrets2_token_urlsafe():
    return len(token_urlsafe(16)) > 0

def secrets2_compare_digest_self():
    x = token_hex(8)
    return compare_digest(x, x) == True

def secrets2_randbits():
    return 0 <= randbits(8) <= 255