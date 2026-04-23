"""
theseus_email_base64mime_cr — Clean-room email.base64mime module.
No import of the standard `email.base64mime` module.
"""

import base64 as _base64

MAXLINESIZE = 76
MAXLINESEP = 2


def header_length(bytearray):
    """Return the length of str when it is encoded with base64."""
    groups_of_3, leftover = divmod(len(bytearray), 3)
    n = groups_of_3 * 4
    if leftover:
        n += 4
    return n


def header_encode(header_bytes, charset='iso-8859-1'):
    """Encode a single header line with base64 (like =?charset?b?...?=)."""
    if not header_bytes:
        return ''
    if isinstance(header_bytes, str):
        header_bytes = header_bytes.encode(charset)
    encoded = _base64.b64encode(header_bytes).decode('ascii')
    return f'=?{charset}?b?{encoded}?='


def body_encode(s, maxlinelen=76, eol='\n'):
    """Encode the string for use as an email body (base64)."""
    if not s:
        return s
    if isinstance(s, str):
        s = s.encode('ascii')
    value = _base64.encodebytes(s).decode('ascii')
    # Remove trailing newline and re-join with eol
    lines = value.rstrip('\n').split('\n')
    return eol.join(lines) + eol


def decode(string):
    """Decode a base64 encoded string."""
    if isinstance(string, str):
        string = string.encode('ascii')
    return _base64.decodebytes(string)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailb642_header_encode():
    """header_encode() encodes a string in base64 for headers; returns True."""
    result = header_encode(b'Hello World', 'utf-8')
    return (isinstance(result, str) and
            result.startswith('=?utf-8?b?') and
            result.endswith('?='))


def emailb642_body_encode():
    """body_encode() encodes a string for message bodies; returns True."""
    result = body_encode(b'Hello, world!')
    return (isinstance(result, str) and
            len(result) > 0 and
            '\n' in result)


def emailb642_decode():
    """decode() decodes a base64 encoded string; returns True."""
    encoded = _base64.b64encode(b'Hello').decode('ascii') + '\n'
    decoded = decode(encoded)
    return decoded == b'Hello'


__all__ = [
    'header_length', 'header_encode', 'body_encode', 'decode',
    'MAXLINESIZE', 'MAXLINESEP',
    'emailb642_header_encode', 'emailb642_body_encode', 'emailb642_decode',
]
