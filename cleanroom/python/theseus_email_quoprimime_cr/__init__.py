"""Clean-room implementation of email.quoprimime.

Implements RFC 2045 quoted-printable encoding (for message bodies) and
RFC 2047 'Q' encoding (for message headers), plus the corresponding
decoder.  No third-party imports.  The original email.quoprimime is
not imported.
"""

import re

CRLF = '\r\n'
NL = '\n'
EMPTYSTRING = ''
HEX = '0123456789ABCDEFabcdef'

# ---------------------------------------------------------------------------
# Character-level encoding tables.
# ---------------------------------------------------------------------------

# Header (RFC 2047 'Q') map: every byte maps to either its literal char
# (if it is "safe" in a header) or to its '=XX' escape.  Spaces are
# encoded specially as '_'.
_QUOPRI_HEADER_MAP = {c: '=%02X' % c for c in range(256)}
for _c in range(33, 127):
    if _c not in (ord('='), ord('?'), ord('_')):
        _QUOPRI_HEADER_MAP[_c] = chr(_c)
_QUOPRI_HEADER_MAP[ord(' ')] = '_'

# Body (RFC 2045) map: every byte maps to either its literal char (if it
# is printable ASCII other than '='), tab, space, or newline characters,
# or to its '=XX' escape otherwise.
_QUOPRI_BODY_MAP = {c: '=%02X' % c for c in range(256)}
for _c in range(33, 127):
    if _c != ord('='):
        _QUOPRI_BODY_MAP[_c] = chr(_c)
_QUOPRI_BODY_MAP[ord('\t')] = '\t'
_QUOPRI_BODY_MAP[ord(' ')] = ' '
_QUOPRI_BODY_MAP[ord('\n')] = '\n'
_QUOPRI_BODY_MAP[ord('\r')] = '\r'


# ---------------------------------------------------------------------------
# Public helpers (mirroring the email.quoprimime API).
# ---------------------------------------------------------------------------

def header_check(octet):
    """Return True if *octet* is encoded as ``=XX`` in a header.

    Spaces are encoded as ``_`` (not ``=20``) and so return False here:
    the function reports specifically whether the octet becomes a
    hexadecimal ``=XX`` escape, mirroring the map's output.
    """
    return _QUOPRI_HEADER_MAP[octet].startswith('=')


def body_check(octet):
    """Return True if *octet* is encoded as ``=XX`` in a body."""
    return _QUOPRI_BODY_MAP[octet].startswith('=')


def header_length(bytearray):
    """Length the byte sequence will occupy after header QP encoding."""
    return sum(len(_QUOPRI_HEADER_MAP[b]) for b in bytearray)


def body_length(bytearray):
    """Length the byte sequence will occupy after body QP encoding."""
    return sum(len(_QUOPRI_BODY_MAP[b]) for b in bytearray)


def unquote(s):
    """Decode a single ``=XX`` escape sequence (length-3 string)."""
    return chr(int(s[1:3], 16))


def quote(c):
    """Encode a single character as ``=XX``."""
    return '=%02X' % ord(c)


# ---------------------------------------------------------------------------
# Header encoding (RFC 2047 'Q').
# ---------------------------------------------------------------------------

def header_encode(header_bytes, charset='iso-8859-1'):
    """Encode *header_bytes* using RFC 2047 'Q' encoding."""
    if not header_bytes:
        return ''
    encoded = ''.join(_QUOPRI_HEADER_MAP[b] for b in header_bytes)
    return '=?%s?q?%s?=' % (charset, encoded)


# ---------------------------------------------------------------------------
# Body encoding (RFC 2045 quoted-printable).
# ---------------------------------------------------------------------------

def _encode_body_chars(body):
    """Apply per-character body encoding without line wrapping."""
    out = []
    for ch in body:
        c = ord(ch)
        if c < 256:
            out.append(_QUOPRI_BODY_MAP[c])
        else:
            # Non-Latin-1 character; pass through unchanged.  Real-world
            # callers should hand us a Latin-1 / bytes-decoded string.
            out.append(ch)
    return ''.join(out)


def body_encode(body, maxlinelen=76, eol=NL):
    """Encode *body* using quoted-printable, wrapping at *maxlinelen*.

    Soft line breaks are inserted as ``=`` followed by *eol*.  Trailing
    whitespace on each physical line (including each wrapped chunk) is
    encoded so it survives transport.
    """
    if not body:
        return body

    body = _encode_body_chars(body)

    soft_break = '=' + eol
    # Leave one column for the trailing '=' on a soft break.
    maxlinelen1 = maxlinelen - 1
    if maxlinelen1 < 1:
        maxlinelen1 = 1

    out_lines = []
    lines = body.split('\n')

    for idx, line in enumerate(lines):
        # Strip a trailing CR if the source used CRLF separators.
        if line.endswith('\r'):
            line = line[:-1]

        out_parts = []
        start = 0
        # Wrap long physical lines into chunks <= maxlinelen1 chars.
        while start + maxlinelen1 < len(line):
            stop = start + maxlinelen1
            # Don't split a '=XX' triple across a soft break.
            if stop - 2 >= start and line[stop - 2] == '=':
                stop -= 2
            elif stop - 1 >= start and line[stop - 1] == '=':
                stop -= 1
            chunk = line[start:stop]
            # Trailing whitespace on a wrapped chunk must be encoded.
            if chunk and chunk[-1] in ' \t':
                chunk = chunk[:-1] + quote(chunk[-1])
            out_parts.append(chunk + soft_break)
            start = stop

        last_chunk = line[start:]
        # Trailing whitespace on a non-final line must be encoded so it
        # is not stripped by transports.
        if idx < len(lines) - 1 and last_chunk and last_chunk[-1] in ' \t':
            last_chunk = last_chunk[:-1] + quote(last_chunk[-1])
        out_parts.append(last_chunk)

        out_lines.append(''.join(out_parts))

    return eol.join(out_lines)


# ---------------------------------------------------------------------------
# Decoding.
# ---------------------------------------------------------------------------

def decode(encoded, eol=NL):
    """Decode a quoted-printable string using *eol* as the line separator."""
    if not encoded:
        return encoded

    decoded = ''
    for line in encoded.splitlines():
        line = line.rstrip()
        if not line:
            decoded += eol
            continue

        i = 0
        n = len(line)
        soft_break = False
        while i < n:
            c = line[i]
            if c != '=':
                decoded += c
                i += 1
            elif i + 1 == n:
                # Trailing '=' is a soft line break.
                soft_break = True
                i += 1
            elif i + 2 < n and line[i + 1] in HEX and line[i + 2] in HEX:
                decoded += unquote(line[i:i + 3])
                i += 3
            else:
                # Malformed escape — preserve verbatim.
                decoded += c
                i += 1

        if not soft_break:
            decoded += eol

    # If the original input did not end with a hard line terminator we
    # must not invent one in the output either.
    if encoded[-1] not in '\r\n' and decoded.endswith(eol):
        decoded = decoded[:-len(eol)]
    return decoded


# Aliases that exist in the original module.
body_decode = decode


def header_decode(s):
    """Decode an RFC 2047 'Q'-encoded header payload (no '=?...?=' frame)."""
    s = s.replace('_', ' ')
    return re.sub(r'=[0-9A-Fa-f]{2}', lambda m: unquote(m.group(0)), s)


# ---------------------------------------------------------------------------
# Invariant test functions.
# ---------------------------------------------------------------------------

def emailqp2_header_encode():
    """Self-test for header_encode().  Returns True on success."""
    try:
        if header_encode(b'') != '':
            return False
        if header_encode(b'hello') != '=?iso-8859-1?q?hello?=':
            return False
        if header_encode(b'hello world') != '=?iso-8859-1?q?hello_world?=':
            return False
        if header_encode(b'\xe9', 'utf-8') != '=?utf-8?q?=E9?=':
            return False
        if header_encode(b'a=b?c_d') != '=?iso-8859-1?q?a=3Db=3Fc=5Fd?=':
            return False
        # Header encoding length matches the encoded string length minus
        # the wrapping '=?charset?q?...?=' chrome.
        sample = b'caf\xe9'
        enc = header_encode(sample)
        chrome = len('=?iso-8859-1?q??=')
        if header_length(sample) != len(enc) - chrome:
            return False
        # header_check agrees with the map.
        for b in range(256):
            mapped = _QUOPRI_HEADER_MAP[b]
            must_escape = header_check(b)
            if must_escape and not mapped.startswith('='):
                return False
            if not must_escape and mapped.startswith('='):
                return False
        return True
    except Exception:
        return False


def emailqp2_body_encode():
    """Self-test for body_encode().  Returns True on success."""
    try:
        if body_encode('') != '':
            return False
        if body_encode('hello') != 'hello':
            return False
        if body_encode('hello = world') != 'hello =3D world':
            return False
        # Trailing whitespace on a non-terminal line must be encoded.
        out = body_encode('hello \nworld')
        if not out.startswith('hello=20\n') or not out.endswith('world'):
            return False
        # Soft line break is introduced for over-long lines.
        wrapped = body_encode('a' * 100, maxlinelen=76)
        if '=\n' not in wrapped:
            return False
        # Re-joining the wrapped soft breaks should restore the original.
        if wrapped.replace('=\n', '') != 'a' * 100:
            return False
        # body_length agrees with the encoded length when no wrapping is
        # involved.
        sample = b'plain text'
        if body_length(sample) != len(body_encode(sample.decode('latin-1'))):
            return False
        # body_check agrees with the map.
        for b in range(256):
            mapped = _QUOPRI_BODY_MAP[b]
            if b in (ord(' '), ord('\t'), ord('\n'), ord('\r')):
                continue  # whitespace handled specially in body wrapping
            must_escape = body_check(b)
            if must_escape and not mapped.startswith('='):
                return False
            if not must_escape and mapped.startswith('='):
                return False
        return True
    except Exception:
        return False


def emailqp2_decode():
    """Self-test for decode().  Returns True on success."""
    try:
        if decode('') != '':
            return False
        if decode('hello') != 'hello':
            return False
        if decode('=3D') != '=':
            return False
        if decode('hello =3D world') != 'hello = world':
            return False
        # Soft line break is removed.
        if decode('hel=\nlo') != 'hello':
            return False
        # Lower-case hex digits accepted.
        if decode('=e9') != '\xe9':
            return False
        # Malformed escape passes through.
        if decode('=ZZ') != '=ZZ':
            return False
        # Trailing newline is preserved.
        if decode('hello\n') != 'hello\n':
            return False
        # Round-trip: encode then decode reproduces the original (when the
        # original contains no chars that require special wrapping rules).
        for original in ('hello world\n',
                         'plain text without newline',
                         'a = b\nc = d\n',
                         'caf\xe9\n'):
            if decode(body_encode(original)) != original:
                return False
        # unquote / quote round-trip.
        for ch in ('=', '?', '\xe9', '\x00', '\x7f'):
            if unquote(quote(ch)) != ch:
                return False
        # header_decode handles underscore-as-space and =XX.
        if header_decode('hello_world') != 'hello world':
            return False
        if header_decode('caf=E9') != 'caf\xe9':
            return False
        return True
    except Exception:
        return False