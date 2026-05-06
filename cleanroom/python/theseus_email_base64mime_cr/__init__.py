"""Clean-room implementation of email.base64mime.

Implements base64 MIME encoding for email headers (RFC 2047) and bodies,
without importing email.base64mime or the base64 module. All base64
arithmetic is implemented from scratch using stdlib built-ins.
"""

# Base64 alphabet per RFC 4648 / RFC 2045
_B64_ALPHABET = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
_B64_DECODE_TABLE = {c: i for i, c in enumerate(_B64_ALPHABET)}
_PAD = ord('=')

NL = '\n'
EMPTYSTRING = ''
CRLF = '\r\n'


def _b64encode(data):
    """Encode bytes to base64 bytes (no trailing newline)."""
    if not data:
        return b''
    if isinstance(data, str):
        data = data.encode('latin-1')
    if not isinstance(data, (bytes, bytearray, memoryview)):
        data = bytes(data)
    out = bytearray()
    n = len(data)
    i = 0
    # Process complete 3-byte groups -> 4 base64 chars
    while i + 3 <= n:
        b1 = data[i]
        b2 = data[i + 1]
        b3 = data[i + 2]
        out.append(_B64_ALPHABET[b1 >> 2])
        out.append(_B64_ALPHABET[((b1 & 0x03) << 4) | (b2 >> 4)])
        out.append(_B64_ALPHABET[((b2 & 0x0f) << 2) | (b3 >> 6)])
        out.append(_B64_ALPHABET[b3 & 0x3f])
        i += 3
    remaining = n - i
    if remaining == 1:
        b1 = data[i]
        out.append(_B64_ALPHABET[b1 >> 2])
        out.append(_B64_ALPHABET[(b1 & 0x03) << 4])
        out.append(_PAD)
        out.append(_PAD)
    elif remaining == 2:
        b1 = data[i]
        b2 = data[i + 1]
        out.append(_B64_ALPHABET[b1 >> 2])
        out.append(_B64_ALPHABET[((b1 & 0x03) << 4) | (b2 >> 4)])
        out.append(_B64_ALPHABET[(b2 & 0x0f) << 2])
        out.append(_PAD)
    return bytes(out)


def _b64decode(data):
    """Decode base64 bytes to bytes. Lenient: ignores non-alphabet chars."""
    if isinstance(data, str):
        try:
            data = data.encode('ascii')
        except UnicodeEncodeError:
            data = data.encode('raw-unicode-escape')
    if not isinstance(data, (bytes, bytearray, memoryview)):
        data = bytes(data)

    # Filter to only valid base64 chars and padding
    cleaned = bytearray()
    for c in data:
        if c in _B64_DECODE_TABLE or c == _PAD:
            cleaned.append(c)

    if not cleaned:
        return b''

    # Pad to a multiple of 4 with '=' if necessary (lenient).
    while len(cleaned) % 4 != 0:
        cleaned.append(_PAD)

    out = bytearray()
    i = 0
    L = len(cleaned)
    while i < L:
        c1 = cleaned[i]
        c2 = cleaned[i + 1]
        c3 = cleaned[i + 2]
        c4 = cleaned[i + 3]
        i += 4

        if c1 == _PAD or c2 == _PAD:
            break

        v1 = _B64_DECODE_TABLE[c1]
        v2 = _B64_DECODE_TABLE[c2]
        out.append(((v1 << 2) | (v2 >> 4)) & 0xff)

        if c3 == _PAD:
            break
        v3 = _B64_DECODE_TABLE[c3]
        out.append((((v2 & 0x0f) << 4) | (v3 >> 2)) & 0xff)

        if c4 == _PAD:
            break
        v4 = _B64_DECODE_TABLE[c4]
        out.append((((v3 & 0x03) << 6) | v4) & 0xff)

    return bytes(out)


def header_encode(header_bytes=b'', charset='iso-8859-1'):
    """Encode a single header line with Base64 encoding in a given charset.

    Returns a string in the RFC 2047 encoded-word form:
        =?charset?b?encoded-text?=
    Returns an empty string if header_bytes is empty.
    """
    if not header_bytes:
        return ''
    if isinstance(header_bytes, str):
        header_bytes = header_bytes.encode(charset)
    encoded = _b64encode(header_bytes).decode('ascii')
    return '=?%s?b?%s?=' % (charset, encoded)


def body_encode(s=b'', maxlinelen=76, eol=NL):
    r"""Encode a string with base64.

    Each line will be wrapped at, at most, maxlinelen characters (defaults
    to 76 characters).  Each line of encoded text will end with eol, which
    defaults to "\n".  Set this to "\r\n" if you will be using the result
    of this function directly in an email.
    """
    if not s:
        return s

    encvec = []
    # max raw bytes per output line; multiple of 3 (4 base64 chars per 3 bytes)
    max_unencoded = maxlinelen * 3 // 4
    if max_unencoded < 1:
        max_unencoded = 1

    n = len(s)
    for i in range(0, n, max_unencoded):
        chunk = s[i:i + max_unencoded]
        enc = _b64encode(chunk).decode('ascii') + NL
        if enc.endswith(NL) and eol != NL:
            enc = enc[:-1] + eol
        encvec.append(enc)

    return EMPTYSTRING.join(encvec)


def decode(string='', encoding='raw-unicode-escape'):
    """Decode a raw base64 string, returning a bytes object.

    This function does not parse a full MIME header value encoded with
    base64 (like =?iso-8859-1?b?bmloISBuaWgh?=) -- please use the high
    level email.header class for that functionality.
    """
    if not string:
        return bytes()
    elif isinstance(string, str):
        return _b64decode(string.encode(encoding))
    else:
        return _b64decode(string)


# ---------------------------------------------------------------------------
# Zero-argument invariant wrappers required by Theseus.
# ---------------------------------------------------------------------------

def emailb642_header_encode():
    return header_encode(b'hello', 'utf-8') == '=?utf-8?b?aGVsbG8=?='


def emailb642_body_encode():
    return body_encode(b'hello') == 'aGVsbG8=\n'


def emailb642_decode():
    return decode('aGVsbG8=') == b'hello'


# Legacy/compat aliases sometimes used in older email module versions
header_encode_base64 = header_encode
body_encode_base64 = body_encode
decode_base64 = decode


__all__ = [
    'header_encode',
    'body_encode',
    'decode',
    'emailb642_header_encode',
    'emailb642_body_encode',
    'emailb642_decode',
]
