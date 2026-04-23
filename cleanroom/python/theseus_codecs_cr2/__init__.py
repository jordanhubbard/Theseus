"""
theseus_codecs_cr2 - Clean-room implementation of codec utilities.
No import of the 'codecs' module allowed.
"""


class CodecInfo:
    """Holds information about a codec."""

    def __init__(self, name, encode_func, decode_func):
        self.name = name
        self._encode = encode_func
        self._decode = decode_func

    def __repr__(self):
        return f"CodecInfo(name={self.name!r})"


# ---------------------------------------------------------------------------
# Internal encoding/decoding helpers
# ---------------------------------------------------------------------------

def _normalize_encoding(encoding):
    """Normalize encoding name to canonical form."""
    enc = encoding.lower().replace('_', '-').strip()
    # Map common aliases
    aliases = {
        'utf8': 'utf-8',
        'utf-8': 'utf-8',
        'ascii': 'ascii',
        'us-ascii': 'ascii',
        'latin-1': 'latin-1',
        'latin1': 'latin-1',
        'iso-8859-1': 'latin-1',
        'iso8859-1': 'latin-1',
        'iso_8859-1': 'latin-1',
        '8859': 'latin-1',
    }
    return aliases.get(enc, enc)


# --- UTF-8 ---

def _utf8_encode_char(code_point):
    """Encode a single Unicode code point to UTF-8 bytes."""
    if code_point < 0:
        raise ValueError(f"Invalid code point: {code_point}")
    elif code_point <= 0x7F:
        return bytes([code_point])
    elif code_point <= 0x7FF:
        b1 = 0xC0 | (code_point >> 6)
        b2 = 0x80 | (code_point & 0x3F)
        return bytes([b1, b2])
    elif code_point <= 0xFFFF:
        if 0xD800 <= code_point <= 0xDFFF:
            raise UnicodeEncodeError('utf-8', chr(code_point), 0, 1,
                                     'surrogates not allowed')
        b1 = 0xE0 | (code_point >> 12)
        b2 = 0x80 | ((code_point >> 6) & 0x3F)
        b3 = 0x80 | (code_point & 0x3F)
        return bytes([b1, b2, b3])
    elif code_point <= 0x10FFFF:
        b1 = 0xF0 | (code_point >> 18)
        b2 = 0x80 | ((code_point >> 12) & 0x3F)
        b3 = 0x80 | ((code_point >> 6) & 0x3F)
        b4 = 0x80 | (code_point & 0x3F)
        return bytes([b1, b2, b3, b4])
    else:
        raise ValueError(f"Code point out of range: {code_point}")


def _utf8_encode(text, errors='strict'):
    """Encode a string to UTF-8 bytes. Returns (bytes, length_consumed)."""
    result = bytearray()
    for i, ch in enumerate(text):
        cp = ord(ch)
        try:
            result.extend(_utf8_encode_char(cp))
        except (UnicodeEncodeError, ValueError):
            if errors == 'strict':
                raise UnicodeEncodeError('utf-8', text, i, i + 1,
                                         f'character {ch!r} cannot be encoded')
            elif errors == 'ignore':
                continue
            elif errors == 'replace':
                result.extend(b'?')
            else:
                raise LookupError(f"unknown error handler name '{errors}'")
    return (bytes(result), len(text))


def _utf8_decode(data, errors='strict'):
    """Decode UTF-8 bytes to a string. Returns (str, length_consumed)."""
    if isinstance(data, memoryview):
        data = bytes(data)
    result = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        try:
            if b <= 0x7F:
                result.append(chr(b))
                i += 1
            elif b <= 0xBF:
                # Continuation byte without leading byte
                raise UnicodeDecodeError('utf-8', data, i, i + 1,
                                         'invalid start byte')
            elif b <= 0xDF:
                # 2-byte sequence
                if i + 1 >= n:
                    raise UnicodeDecodeError('utf-8', data, i, n,
                                             'unexpected end of data')
                b2 = data[i + 1]
                if not (0x80 <= b2 <= 0xBF):
                    raise UnicodeDecodeError('utf-8', data, i, i + 2,
                                             'invalid continuation byte')
                cp = ((b & 0x1F) << 6) | (b2 & 0x3F)
                if cp < 0x80:
                    raise UnicodeDecodeError('utf-8', data, i, i + 2,
                                             'overlong encoding')
                result.append(chr(cp))
                i += 2
            elif b <= 0xEF:
                # 3-byte sequence
                if i + 2 >= n:
                    raise UnicodeDecodeError('utf-8', data, i, n,
                                             'unexpected end of data')
                b2 = data[i + 1]
                b3 = data[i + 2]
                if not (0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF):
                    raise UnicodeDecodeError('utf-8', data, i, i + 3,
                                             'invalid continuation byte')
                cp = ((b & 0x0F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
                if cp < 0x800:
                    raise UnicodeDecodeError('utf-8', data, i, i + 3,
                                             'overlong encoding')
                if 0xD800 <= cp <= 0xDFFF:
                    raise UnicodeDecodeError('utf-8', data, i, i + 3,
                                             'surrogates not allowed')
                result.append(chr(cp))
                i += 3
            elif b <= 0xF7:
                # 4-byte sequence
                if i + 3 >= n:
                    raise UnicodeDecodeError('utf-8', data, i, n,
                                             'unexpected end of data')
                b2 = data[i + 1]
                b3 = data[i + 2]
                b4 = data[i + 3]
                if not (0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF
                        and 0x80 <= b4 <= 0xBF):
                    raise UnicodeDecodeError('utf-8', data, i, i + 4,
                                             'invalid continuation byte')
                cp = (((b & 0x07) << 18) | ((b2 & 0x3F) << 12)
                      | ((b3 & 0x3F) << 6) | (b4 & 0x3F))
                if cp < 0x10000:
                    raise UnicodeDecodeError('utf-8', data, i, i + 4,
                                             'overlong encoding')
                if cp > 0x10FFFF:
                    raise UnicodeDecodeError('utf-8', data, i, i + 4,
                                             'code point out of range')
                result.append(chr(cp))
                i += 4
            else:
                raise UnicodeDecodeError('utf-8', data, i, i + 1,
                                         'invalid start byte')
        except UnicodeDecodeError:
            if errors == 'strict':
                raise
            elif errors == 'ignore':
                i += 1
            elif errors == 'replace':
                result.append('\ufffd')
                i += 1
            else:
                raise LookupError(f"unknown error handler name '{errors}'")
    return (''.join(result), n)


# --- ASCII ---

def _ascii_encode(text, errors='strict'):
    """Encode a string to ASCII bytes. Returns (bytes, length_consumed)."""
    result = bytearray()
    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp > 127:
            if errors == 'strict':
                raise UnicodeEncodeError('ascii', text, i, i + 1,
                                         'ordinal not in range(128)')
            elif errors == 'ignore':
                continue
            elif errors == 'replace':
                result.append(ord('?'))
            else:
                raise LookupError(f"unknown error handler name '{errors}'")
        else:
            result.append(cp)
    return (bytes(result), len(text))


def _ascii_decode(data, errors='strict'):
    """Decode ASCII bytes to a string. Returns (str, length_consumed)."""
    if isinstance(data, memoryview):
        data = bytes(data)
    result = []
    for i, b in enumerate(data):
        if b > 127:
            if errors == 'strict':
                raise UnicodeDecodeError('ascii', data, i, i + 1,
                                         'ordinal not in range(128)')
            elif errors == 'ignore':
                continue
            elif errors == 'replace':
                result.append('\ufffd')
            else:
                raise LookupError(f"unknown error handler name '{errors}'")
        else:
            result.append(chr(b))
    return (''.join(result), len(data))


# --- Latin-1 (ISO-8859-1) ---

def _latin1_encode(text, errors='strict'):
    """Encode a string to Latin-1 bytes. Returns (bytes, length_consumed)."""
    result = bytearray()
    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp > 255:
            if errors == 'strict':
                raise UnicodeEncodeError('latin-1', text, i, i + 1,
                                         'ordinal not in range(256)')
            elif errors == 'ignore':
                continue
            elif errors == 'replace':
                result.append(ord('?'))
            else:
                raise LookupError(f"unknown error handler name '{errors}'")
        else:
            result.append(cp)
    return (bytes(result), len(text))


def _latin1_decode(data, errors='strict'):
    """Decode Latin-1 bytes to a string. Returns (str, length_consumed)."""
    if isinstance(data, memoryview):
        data = bytes(data)
    # Latin-1 is a direct mapping: byte value == Unicode code point
    result = [chr(b) for b in data]
    return (''.join(result), len(data))


# ---------------------------------------------------------------------------
# Codec registry
# ---------------------------------------------------------------------------

_CODECS = {
    'utf-8': CodecInfo('utf-8', _utf8_encode, _utf8_decode),
    'ascii': CodecInfo('ascii', _ascii_encode, _ascii_decode),
    'latin-1': CodecInfo('latin-1', _latin1_encode, _latin1_decode),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup(encoding):
    """
    Return a CodecInfo object for the given encoding name.

    Parameters
    ----------
    encoding : str
        The encoding name (e.g. 'utf-8', 'ascii', 'latin-1').

    Returns
    -------
    CodecInfo
        Object with at least a `.name` attribute.

    Raises
    ------
    LookupError
        If the encoding is not supported.
    """
    name = _normalize_encoding(encoding)
    if name not in _CODECS:
        raise LookupError(f"unknown encoding: {encoding!r}")
    return _CODECS[name]


def encode(obj, encoding='utf-8', errors='strict'):
    """
    Encode *obj* (a str) using *encoding*.

    Returns
    -------
    (bytes, int)
        A tuple of (encoded_bytes, length_consumed) where length_consumed
        is the number of characters consumed from the input string.

    Raises
    ------
    LookupError
        If the encoding is not supported.
    UnicodeEncodeError
        If encoding fails and errors='strict'.
    TypeError
        If obj is not a str.
    """
    if not isinstance(obj, str):
        raise TypeError(f"encode() argument must be str, not {type(obj).__name__!r}")
    codec = lookup(encoding)
    return codec._encode(obj, errors)


def decode(obj, encoding='utf-8', errors='strict'):
    """
    Decode *obj* (bytes or bytearray) using *encoding*.

    Returns
    -------
    (str, int)
        A tuple of (decoded_string, length_consumed) where length_consumed
        is the number of bytes consumed from the input.

    Raises
    ------
    LookupError
        If the encoding is not supported.
    UnicodeDecodeError
        If decoding fails and errors='strict'.
    TypeError
        If obj is not bytes or bytearray.
    """
    if not isinstance(obj, (bytes, bytearray, memoryview)):
        raise TypeError(
            f"decode() argument must be bytes-like, not {type(obj).__name__!r}"
        )
    codec = lookup(encoding)
    return codec._decode(obj, errors)


# ---------------------------------------------------------------------------
# Zero-arg invariant helpers (as specified)
# ---------------------------------------------------------------------------

def codecs2_lookup():
    """Return the canonical name for utf-8 via lookup()."""
    return lookup('utf-8').name


def codecs2_encode():
    """Return the length component of encode('hello', 'utf-8')."""
    _, length = encode('hello', 'utf-8')
    return length


def codecs2_decode():
    """Return the string component of decode(b'hello', 'utf-8')."""
    text, _ = decode(b'hello', 'utf-8')
    return text


__all__ = [
    'CodecInfo',
    'lookup',
    'encode',
    'decode',
    'codecs2_lookup',
    'codecs2_encode',
    'codecs2_decode',
]