"""
theseus_email_quoprimime_cr — Clean-room email.quoprimime module.
No import of the standard `email.quoprimime` module.
"""

import quopri as _quopri
import re as _re

MAXLINESIZE = 76
HEX = '0123456789ABCDEF'
EMPTYSTRING = ''
NL = '\n'
NLCRE = _re.compile(r'\r\n|\r|\n')

# Characters that don't need quoting in QP
_QUOPRI_HEADER_MAP = {}
_QUOPRI_BODY_MAP = {}

for c in range(256):
    ch = chr(c)
    if ((33 <= c <= 60) or (62 <= c <= 126)) and ch != '=':
        _QUOPRI_BODY_MAP[ch] = ch
    else:
        _QUOPRI_BODY_MAP[ch] = '=%02X' % c

for c in range(256):
    ch = chr(c)
    if ((33 <= c <= 60) or (62 <= c <= 126)) and ch not in ' \t_':
        _QUOPRI_HEADER_MAP[ch] = ch
    elif ch == ' ':
        _QUOPRI_HEADER_MAP[ch] = '_'
    else:
        _QUOPRI_HEADER_MAP[ch] = '=%02X' % c


def header_quopri_check(c):
    """Return True if the character should be QP-encoded in a header."""
    return _QUOPRI_HEADER_MAP.get(c, None) != c


def body_quopri_check(c):
    """Return True if the character needs QP encoding in a body."""
    return _QUOPRI_BODY_MAP.get(c, None) != c


def header_encode(header_bytes, charset='iso-8859-1'):
    """Encode a single header line with quoted-printable."""
    if not header_bytes:
        return ''
    if isinstance(header_bytes, str):
        header_bytes = header_bytes.encode(charset)
    encoded_words = []
    s = ''.join(_QUOPRI_HEADER_MAP.get(chr(b), '=%02X' % b)
                for b in header_bytes)
    return f'=?{charset}?q?{s}?='


def body_encode(body, maxlinelen=MAXLINESIZE, eol=NL):
    """Encode the body of a message with quoted-printable."""
    if not body:
        return body
    if isinstance(body, bytes):
        body = body.decode('latin-1')

    lines = NLCRE.split(body)
    result = []
    for line in lines:
        encoded_line = []
        line_len = 0
        for c in line:
            qc = _QUOPRI_BODY_MAP.get(c, '=%02X' % ord(c))
            if line_len + len(qc) >= maxlinelen:
                encoded_line.append('=')
                result.append(''.join(encoded_line))
                encoded_line = []
                line_len = 0
            encoded_line.append(qc)
            line_len += len(qc)
        # Trailing whitespace must be encoded
        if encoded_line and encoded_line[-1][-1] in (' ', '\t'):
            last = encoded_line[-1]
            encoded_line[-1] = _QUOPRI_BODY_MAP.get(last[-1], last)
        result.append(''.join(encoded_line))
    return eol.join(result) + eol


def decode(encoded, eol=NL):
    """Decode a quoted-printable encoded string."""
    if isinstance(encoded, str):
        encoded = encoded.encode('ascii')
    decoded = _quopri.decodestring(encoded)
    return decoded.decode('latin-1')


def header_decode(s):
    """Decode a header encoded with quoted-printable."""
    s = s.replace('_', ' ')
    lines = s.split('?=')
    result = ''
    for part in lines:
        if '?q?' in part.lower() or '?Q?' in part:
            _, _, encoded = part.rpartition('?')
            decoded_bytes = _quopri.decodestring(encoded.encode('ascii'))
            result += decoded_bytes.decode('latin-1')
        else:
            result += part
    return result


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailqp2_header_encode():
    """header_encode() encodes a string in QP for headers; returns True."""
    result = header_encode(b'Hello World', 'utf-8')
    return (isinstance(result, str) and
            '=?utf-8?q?' in result and
            result.endswith('?='))


def emailqp2_body_encode():
    """body_encode() encodes a string for message bodies; returns True."""
    result = body_encode('Hello, world!')
    return isinstance(result, str) and len(result) > 0


def emailqp2_decode():
    """decode() decodes a QP encoded string; returns True."""
    encoded = b'Hello=2C=20world=21'
    decoded = decode(encoded)
    return 'Hello' in decoded


__all__ = [
    'header_encode', 'body_encode', 'decode', 'header_decode',
    'header_quopri_check', 'body_quopri_check',
    'MAXLINESIZE', 'HEX', 'EMPTYSTRING', 'NL', 'NLCRE',
    'emailqp2_header_encode', 'emailqp2_body_encode', 'emailqp2_decode',
]
