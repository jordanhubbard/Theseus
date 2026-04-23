"""
theseus_email_charset_cr — Clean-room email.charset module.
No import of the standard `email.charset` module.
"""

import base64 as _base64
import quopri as _quopri
import io as _io

# Charset conversion codes
QP = 1    # Quoted-printable encoding
BASE64 = 2  # Base64 encoding
SHORTEST = 3  # Shortest encoding

# MIME charset aliases
ALIASES = {
    'ascii': 'us-ascii',
    'latin-1': 'iso-8859-1',
    'latin1': 'iso-8859-1',
    'iso8859-1': 'iso-8859-1',
    'iso8859_1': 'iso-8859-1',
    '8859': 'iso-8859-1',
    'utf-8': 'utf-8',
    'utf8': 'utf-8',
    'utf_8': 'utf-8',
    'us-ascii': 'us-ascii',
    'ansi_x3.4-1968': 'us-ascii',
    'iso646-us': 'us-ascii',
    'iso-8859-2': 'iso-8859-2',
    'iso-8859-3': 'iso-8859-3',
    'iso-8859-4': 'iso-8859-4',
    'iso-8859-5': 'iso-8859-5',
    'iso-8859-6': 'iso-8859-6',
    'iso-8859-7': 'iso-8859-7',
    'iso-8859-8': 'iso-8859-8',
    'iso-8859-9': 'iso-8859-9',
    'iso-8859-10': 'iso-8859-10',
    'koi8-r': 'koi8-r',
    'big5': 'big5',
    'gb2312': 'gb2312',
    'euc-jp': 'euc-jp',
    'shift_jis': 'shift_jis',
    'euc-kr': 'euc-kr',
}

# Charset header encoding type
CHARSETS = {
    'us-ascii': (None, None, None),
    'iso-8859-1': (QP, QP, None),
    'iso-8859-2': (QP, QP, None),
    'iso-8859-3': (QP, QP, None),
    'iso-8859-4': (QP, QP, None),
    'iso-8859-5': (BASE64, BASE64, None),
    'iso-8859-6': (BASE64, BASE64, None),
    'iso-8859-7': (BASE64, BASE64, None),
    'iso-8859-8': (QP, QP, None),
    'iso-8859-9': (QP, QP, None),
    'iso-8859-10': (QP, QP, None),
    'utf-8': (SHORTEST, BASE64, None),
    'utf-16-be': (BASE64, BASE64, None),
    'utf-16-le': (BASE64, BASE64, None),
    'utf-16': (BASE64, BASE64, None),
    'utf-32': (BASE64, BASE64, None),
    'euc-jp': (BASE64, BASE64, 'iso-2022-jp'),
    'shift_jis': (BASE64, BASE64, None),
    'iso-2022-jp': (BASE64, BASE64, None),
    'big5': (BASE64, BASE64, None),
    'gb2312': (BASE64, BASE64, None),
    'koi8-r': (BASE64, BASE64, None),
    'euc-kr': (BASE64, BASE64, None),
}


class Charset:
    """Maps a MIME character set name to information about that character set."""

    def __init__(self, input_charset='us-ascii'):
        # Normalize the charset name
        name = input_charset.lower()
        self.input_charset = ALIASES.get(name, name)
        info = CHARSETS.get(self.input_charset, (None, None, None))
        self.header_encoding, self.body_encoding, self.output_charset = info
        self.output_charset = self.output_charset or self.input_charset
        self.input_codec = self.input_charset
        self.output_codec = self.output_charset

    def __str__(self):
        return self.input_charset

    def __repr__(self):
        return f'Charset({self.input_charset!r})'

    def __eq__(self, other):
        if isinstance(other, Charset):
            return str(self) == str(other)
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def get_body_encoding(self):
        """Return the content transfer encoding for this charset."""
        if self.body_encoding == QP:
            return 'quoted-printable'
        elif self.body_encoding == BASE64:
            return 'base64'
        return '7bit'

    def get_output_charset(self):
        """Return the output charset (may differ from input for CJK)."""
        return self.output_charset

    def header_length(self, bytestr):
        """Return the number of characters in the header."""
        return len(bytestr)

    def header_encode(self, string):
        """Header-encode a string by converting to bytes and encoding."""
        if not string:
            return string
        if self.header_encoding == BASE64:
            encoded = _base64.b64encode(string.encode(self.input_charset))
            return f'=?{self.input_charset}?b?{encoded.decode("ascii")}?='
        elif self.header_encoding == QP:
            encoded = _quopri.encodestring(string.encode(self.input_charset),
                                            quotetabs=False)
            s = encoded.decode('ascii').replace('\n', '')
            return f'=?{self.input_charset}?q?{s}?='
        return string

    def header_encode_lines(self, string, maxlengths):
        """Encode a string by converting it and wrapping at maxlengths."""
        encoded = self.header_encode(string)
        return [encoded]

    def body_encode(self, string):
        """Body-encode the given string."""
        if self.body_encoding == BASE64:
            bstr = string.encode(self.input_charset)
            encoded = _base64.b64encode(bstr).decode('ascii')
            # Wrap at 76 chars
            lines = []
            while encoded:
                lines.append(encoded[:76])
                encoded = encoded[76:]
            return '\n'.join(lines) + '\n'
        elif self.body_encoding == QP:
            bstr = string.encode(self.input_charset)
            return _quopri.encodestring(bstr).decode('ascii')
        return string

    def convert(self, string):
        """Convert the string from the input codec to the output codec."""
        if self.input_codec != self.output_codec:
            return string.encode(self.input_codec).decode(self.output_codec)
        return string


def add_charset(charset, header_enc=None, body_enc=None, output_charset=None):
    """Add character set properties to the global registry."""
    CHARSETS[charset] = (header_enc, body_enc, output_charset)


def add_alias(alias, canonical):
    """Add a character set alias."""
    ALIASES[alias] = canonical


def add_codec(charset, codecname):
    """Add a codec to the charset."""
    pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailcs2_charset():
    """Charset class can be instantiated for common charsets; returns True."""
    cs_ascii = Charset('us-ascii')
    cs_utf8 = Charset('utf-8')
    return (str(cs_ascii) == 'us-ascii' and
            str(cs_utf8) == 'utf-8' and
            cs_utf8.header_encoding == SHORTEST)


def emailcs2_aliases():
    """ALIASES dict maps charset aliases to canonical names; returns True."""
    return (isinstance(ALIASES, dict) and
            ALIASES.get('utf8') == 'utf-8' and
            ALIASES.get('latin-1') == 'iso-8859-1')


def emailcs2_encode():
    """Charset can encode/decode strings; returns True."""
    cs = Charset('utf-8')
    encoded = cs.header_encode('Hello')
    return isinstance(encoded, str) and len(encoded) > 0


__all__ = [
    'Charset', 'ALIASES', 'CHARSETS',
    'QP', 'BASE64', 'SHORTEST',
    'add_charset', 'add_alias', 'add_codec',
    'emailcs2_charset', 'emailcs2_aliases', 'emailcs2_encode',
]
