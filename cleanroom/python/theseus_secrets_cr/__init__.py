"""
theseus_secrets_cr - Clean-room cryptographically suitable random values.
Implements token_bytes, token_hex, token_urlsafe, and choice without
importing secrets, random, or os modules.
"""


def token_bytes(n):
    """Return n cryptographically random bytes."""
    with open('/dev/urandom', 'rb') as f:
        return f.read(n)


def token_hex(n):
    """Return 2n hex characters of random data."""
    return token_bytes(n).hex()


def token_urlsafe(n):
    """Return URL-safe base64 token of n random bytes."""
    data = token_bytes(n)
    url_safe_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    
    result = []
    for i in range(0, len(data), 3):
        chunk = data[i:i+3]
        if len(chunk) == 3:
            b0, b1, b2 = chunk[0], chunk[1], chunk[2]
            result.append(url_safe_chars[(b0 >> 2) & 0x3F])
            result.append(url_safe_chars[((b0 & 0x03) << 4) | ((b1 >> 4) & 0x0F)])
            result.append(url_safe_chars[((b1 & 0x0F) << 2) | ((b2 >> 6) & 0x03)])
            result.append(url_safe_chars[b2 & 0x3F])
        elif len(chunk) == 2:
            b0, b1 = chunk[0], chunk[1]
            result.append(url_safe_chars[(b0 >> 2) & 0x3F])
            result.append(url_safe_chars[((b0 & 0x03) << 4) | ((b1 >> 4) & 0x0F)])
            result.append(url_safe_chars[((b1 & 0x0F) << 2)])
        elif len(chunk) == 1:
            b0 = chunk[0]
            result.append(url_safe_chars[(b0 >> 2) & 0x3F])
            result.append(url_safe_chars[((b0 & 0x03) << 4)])
    
    return ''.join(result)


def choice(seq):
    """Return a random element from a non-empty sequence."""
    if not seq:
        raise IndexError("Cannot choose from an empty sequence")
    n = len(seq)
    num_bytes = (n.bit_length() + 7) // 8
    if num_bytes == 0:
        num_bytes = 1
    
    max_val = (1 << (num_bytes * 8))
    limit = max_val - (max_val % n)
    
    while True:
        rand_bytes = token_bytes(num_bytes)
        val = int.from_bytes(rand_bytes, 'big')
        if val < limit:
            return seq[val % n]


def token_bytes_len(n):
    """Return the length of token_bytes(n) output, which should be n."""
    return len(token_bytes(n))


def token_hex_len(n):
    """Return the length of token_hex(n) output, which should be 2*n."""
    return len(token_hex(n))


def token_hex_is_hex(n):
    """Return True if token_hex(n) output consists only of hex characters."""
    result = token_hex(n)
    hex_chars = set('0123456789abcdefABCDEF')
    return all(c in hex_chars for c in result)


# Also keep the old names as aliases for backward compatibility
def secrets_token_bytes_len():
    return len(token_bytes(16))

def secrets_token_hex_len():
    return len(token_hex(16))

def secrets_token_hex_is_hex():
    result = token_hex(8)
    hex_chars = set('0123456789abcdefABCDEF')
    return all(c in hex_chars for c in result)