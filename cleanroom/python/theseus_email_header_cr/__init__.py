"""
theseus_email_header_cr — Clean-room email.header module.
No import of the standard `email.header` module.
"""

import re as _re
import base64 as _base64
import quopri as _quopri

USASCII = 'us-ascii'
UTF8 = 'utf-8'
EMPTYSTRING = ''
NL = '\n'
SPACE = ' '
SPACE8 = ' ' * 8
MAXLINELEN = 76

ecre = _re.compile(r'''
  =\?                   # literal =?
  (?P<charset>[^?]*?)   # non-greedy up to the next ? is the charset
  \?                    # literal ?
  (?P<encoding>[qQbB])  # either q or b, case-insensitive
  \?                    # literal ?
  (?P<atom>.*?)         # non-greedy up to the next ?= is the encoded string
  \?=                   # literal ?=
  ''', _re.VERBOSE | _re.MULTILINE)


class Header:
    """An email header that can encode Unicode strings."""

    def __init__(self, s=None, charset=None, maxlinelen=None, header_name=None,
                 continuation_ws=' ', errors='strict'):
        if charset is None:
            charset = USASCII
        self._charset = charset
        self._continuation_ws = continuation_ws
        self._chunks = []
        if s is not None:
            self.append(s, charset, errors)
        if maxlinelen is None:
            maxlinelen = MAXLINELEN
        self._maxlinelen = maxlinelen
        if header_name is not None:
            self._headerlen = len(header_name) + 2
        else:
            self._headerlen = 0

    def __str__(self):
        return self._str(EMPTYSTRING)

    def _str(self, uchunks):
        if not self._chunks:
            return EMPTYSTRING
        parts = []
        for chunk, charset in self._chunks:
            if isinstance(chunk, bytes):
                try:
                    chunk = chunk.decode(charset or 'ascii', errors='replace')
                except (LookupError, UnicodeDecodeError):
                    chunk = chunk.decode('ascii', errors='replace')
            parts.append(chunk)
        return SPACE.join(parts)

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def append(self, s, charset=None, errors='strict'):
        if charset is None:
            charset = self._charset
        self._chunks.append((s, charset))

    def encode(self, splitchars=';, \t', maxlinelen=None, linesep='\n'):
        chunks = []
        for string, charset in self._chunks:
            if isinstance(string, bytes):
                try:
                    string = string.decode(charset or 'ascii', errors='replace')
                except (LookupError, UnicodeDecodeError):
                    string = string.decode('ascii', errors='replace')
            cs = (charset or USASCII).lower()
            if cs == 'us-ascii':
                try:
                    string.encode('ascii')
                    chunks.append(string)
                    continue
                except (UnicodeEncodeError, UnicodeDecodeError):
                    cs = 'utf-8'
            try:
                raw = string.encode(cs)
            except (LookupError, UnicodeEncodeError):
                cs = 'utf-8'
                raw = string.encode(cs)
            encoded = _base64.b64encode(raw).decode('ascii')
            chunks.append('=?%s?b?%s?=' % (cs, encoded))
        return self._continuation_ws.join(chunks)


def decode_header(header):
    """Decode a message header value without converting the character set.

    Returns a list of (string, charset) pairs.
    """
    if hasattr(header, '_chunks'):
        # Already a Header instance — recompose pairs.
        results = []
        for s, charset in header._chunks:
            if isinstance(s, str):
                try:
                    s.encode('ascii')
                    results.append((s, None))
                except (UnicodeEncodeError, UnicodeDecodeError):
                    results.append((s.encode(charset or 'utf-8', errors='replace'),
                                    charset or 'utf-8'))
            else:
                results.append((s, charset))
        return results

    if not header:
        return [(header, None)]

    # If no encoded words, return the entire header as plain ASCII
    words = ecre.split(header)
    if len(words) == 1:
        return [(header, None)]

    decoded_words = []
    i = 0
    while i < len(words):
        word = words[i]
        # Even-indexed items are literal strings between encoded words
        if word:
            decoded_words.append((word, None))
        i += 1
        if i >= len(words):
            break
        charset = words[i].lower() if words[i] else words[i]
        i += 1
        if i >= len(words):
            break
        encoding = words[i].lower()
        i += 1
        if i >= len(words):
            break
        atom = words[i]
        i += 1
        if encoding == 'b':
            # Base64 — pad if necessary
            pad = (-len(atom)) % 4
            try:
                decoded = _base64.b64decode(atom + ('=' * pad))
            except Exception:
                decoded = atom.encode('ascii', errors='replace')
        elif encoding == 'q':
            # Quoted-printable; underscores are spaces
            atom = atom.replace('_', ' ')
            try:
                decoded = _quopri.decodestring(atom.encode('ascii', errors='replace'))
            except Exception:
                decoded = atom.encode('ascii', errors='replace')
        else:
            decoded = atom.encode('ascii', errors='replace')
        decoded_words.append((decoded, charset))

    # Coalesce adjacent encoded chunks that share a charset
    collapsed = []
    for piece, cs in decoded_words:
        if collapsed and cs is not None and collapsed[-1][1] == cs and isinstance(piece, bytes):
            prev_piece, prev_cs = collapsed.pop()
            if isinstance(prev_piece, bytes):
                collapsed.append((prev_piece + piece, cs))
                continue
            collapsed.append((prev_piece, prev_cs))
        collapsed.append((piece, cs))
    return collapsed


def make_header(decoded_seq, maxlinelen=None, header_name=None, continuation_ws=' '):
    """Create a Header from a sequence of pairs as returned by decode_header()."""
    h = Header(maxlinelen=maxlinelen, header_name=header_name,
               continuation_ws=continuation_ws)
    for s, charset in decoded_seq:
        if charset is not None:
            if isinstance(s, bytes):
                try:
                    s = s.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    s = s.decode('ascii', errors='replace')
        else:
            if isinstance(s, bytes):
                s = s.decode('ascii', errors='replace')
        h.append(s, charset if charset is not None else USASCII)
    return h


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailhdr2_header():
    """Header class can be instantiated; returns True."""
    h = Header('Test Subject')
    return isinstance(h, Header) and 'Test Subject' in str(h)


def emailhdr2_decode():
    """decode_header() returns list of (decoded_string, charset) tuples; returns True."""
    result = decode_header('Hello World')
    if not (isinstance(result, list) and len(result) > 0 and isinstance(result[0], tuple)):
        return False
    # Also exercise an encoded-word form
    encoded = decode_header('=?utf-8?b?SGVsbG8=?=')
    return (isinstance(encoded, list) and
            len(encoded) > 0 and
            isinstance(encoded[0], tuple))


def emailhdr2_make():
    """make_header() creates a Header from decoded sequence; returns True."""
    decoded = decode_header('Test')
    h = make_header(decoded)
    return isinstance(h, Header) and 'Test' in str(h)


__all__ = [
    'Header', 'decode_header', 'make_header',
    'USASCII', 'UTF8', 'EMPTYSTRING', 'MAXLINELEN',
    'emailhdr2_header', 'emailhdr2_decode', 'emailhdr2_make',
]