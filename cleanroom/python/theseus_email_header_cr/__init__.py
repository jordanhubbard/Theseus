"""
theseus_email_header_cr — Clean-room email.header module.
No import of the standard `email.header` module.
"""

import re as _re
import base64 as _base64

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
        return SPACE.join(chunk for chunk, charset in self._chunks)

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def append(self, s, charset=None, errors='strict'):
        if charset is None:
            charset = self._charset
        self._chunks.append((s, charset))

    def encode(self, splitchars=';, \t'):
        chunks = []
        for string, charset in self._chunks:
            if charset.lower() == 'us-ascii':
                chunks.append(string)
            else:
                encoded = _base64.b64encode(string.encode(charset)).decode('ascii')
                chunks.append('=?%s?b?%s?=' % (charset, encoded))
        return self._continuation_ws.join(chunks)


def decode_header(header):
    """Decode a message header value without converting the character set.

    Returns a list of (string, charset) pairs.
    """
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
        # Even-indexed items are literal strings
        if word:
            decoded_words.append((word, None))
        i += 1
        # After each literal, there's a charset, encoding, atom triplet
        if i < len(words):
            charset = words[i]
            i += 1
        else:
            break
        if i < len(words):
            encoding = words[i].lower()
            i += 1
        else:
            break
        if i < len(words):
            atom = words[i]
            i += 1
        else:
            break
        if encoding == 'b':
            # Base64
            try:
                decoded = _base64.b64decode(atom)
            except Exception:
                decoded = atom.encode('ascii')
        elif encoding == 'q':
            # Quoted-printable
            atom = atom.replace('_', ' ')
            import quopri as _qp
            atom_bytes = atom.encode('ascii', errors='replace')
            try:
                decoded = _qp.decodestring(atom_bytes)
            except Exception:
                decoded = atom_bytes
        else:
            decoded = atom.encode('ascii', errors='replace')
        decoded_words.append((decoded, charset))

    return decoded_words


def make_header(decoded_seq, maxlinelen=None, header_name=None, continuation_ws=' '):
    """Create a Header from a sequence of pairs as returned by decode_header()."""
    h = Header(maxlinelen=maxlinelen, header_name=header_name,
                continuation_ws=continuation_ws)
    for s, charset in decoded_seq:
        if charset is not None:
            if not isinstance(s, str):
                try:
                    s = s.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    s = s.decode('ascii', errors='replace')
        else:
            if isinstance(s, bytes):
                s = s.decode('ascii', errors='replace')
        h.append(s, charset or USASCII)
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
    return (isinstance(result, list) and
            len(result) > 0 and
            isinstance(result[0], tuple))


def emailhdr2_make():
    """make_header() creates a Header from decoded sequence; returns True."""
    decoded = decode_header('Test')
    h = make_header(decoded)
    return isinstance(h, Header)


__all__ = [
    'Header', 'decode_header', 'make_header',
    'USASCII', 'UTF8', 'EMPTYSTRING', 'MAXLINELEN',
    'emailhdr2_header', 'emailhdr2_decode', 'emailhdr2_make',
]
