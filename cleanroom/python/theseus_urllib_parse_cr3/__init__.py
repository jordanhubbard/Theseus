"""
Clean-room implementation of urllib.parse utilities.
No import of urllib or any third-party libraries.
"""

import re

# Characters that are safe and do not need percent-encoding
# Based on RFC 3986 unreserved characters: A-Z a-z 0-9 - _ . ~
_SAFE_CHARS = frozenset(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    '0123456789'
    '-_.~'
)

_HEX_DIGITS = '0123456789ABCDEF'


def _percent_encode(char_byte):
    """Encode a single byte as %XX."""
    return '%' + _HEX_DIGITS[char_byte >> 4] + _HEX_DIGITS[char_byte & 0x0F]


def quote(string, safe='/', encoding='utf-8', errors='strict'):
    """
    Percent-encode a string. Characters in `safe` are not encoded.
    Spaces are encoded as %20.
    """
    if isinstance(string, str):
        encoded = string.encode(encoding, errors)
    else:
        encoded = string

    safe_set = _SAFE_CHARS | frozenset(safe)

    result = []
    for byte in encoded:
        char = chr(byte)
        if char in safe_set:
            result.append(char)
        else:
            result.append(_percent_encode(byte))
    return ''.join(result)


def quote_plus(string, safe='', encoding='utf-8', errors='strict'):
    """
    Percent-encode a string, encoding spaces as '+' instead of '%20'.
    """
    if isinstance(string, str):
        if ' ' in string:
            string = string.replace(' ', '+')
        return quote(string, safe=safe + '+', encoding=encoding, errors=errors)
    else:
        # bytes
        result = []
        for byte in string:
            char = chr(byte)
            if char == ' ':
                result.append('+')
            elif char in (_SAFE_CHARS | frozenset(safe)):
                result.append(char)
            else:
                result.append(_percent_encode(byte))
        return ''.join(result)


def _hex_to_int(hex_str):
    """Convert a two-character hex string to integer."""
    result = 0
    for ch in hex_str.upper():
        result *= 16
        if '0' <= ch <= '9':
            result += ord(ch) - ord('0')
        elif 'A' <= ch <= 'F':
            result += ord(ch) - ord('A') + 10
        else:
            raise ValueError(f"Invalid hex character: {ch}")
    return result


def unquote(string, encoding='utf-8', errors='replace'):
    """
    Decode a percent-encoded string. Does not handle '+' as space.
    """
    if '%' not in string:
        return string

    result = []
    i = 0
    while i < len(string):
        ch = string[i]
        if ch == '%' and i + 2 < len(string):
            hex_str = string[i+1:i+3]
            try:
                byte_val = _hex_to_int(hex_str)
                # Collect consecutive percent-encoded bytes for multi-byte chars
                byte_seq = bytearray([byte_val])
                j = i + 3
                while j < len(string) and string[j] == '%' and j + 2 < len(string):
                    hex_str2 = string[j+1:j+3]
                    try:
                        next_byte = _hex_to_int(hex_str2)
                        byte_seq.append(next_byte)
                        j += 3
                    except ValueError:
                        break
                # Try to decode the byte sequence
                try:
                    decoded = byte_seq.decode(encoding)
                    result.append(decoded)
                    i = j
                    continue
                except (UnicodeDecodeError, LookupError):
                    # Fall back: just decode the first byte
                    try:
                        result.append(bytes([byte_val]).decode(encoding, errors))
                    except Exception:
                        result.append(chr(byte_val))
                    i += 3
                    continue
            except ValueError:
                result.append(ch)
                i += 1
        else:
            result.append(ch)
            i += 1
    return ''.join(result)


def unquote_plus(string, encoding='utf-8', errors='replace'):
    """
    Decode a percent-encoded string, treating '+' as a space.
    """
    string = string.replace('+', ' ')
    return unquote(string, encoding=encoding, errors=errors)


def urlencode(query, doseq=False, safe='', encoding='utf-8', errors='strict',
              quote_via=None):
    """
    Encode a dict or sequence of two-element tuples as application/x-www-form-urlencoded.
    """
    if quote_via is None:
        quote_via = quote_plus

    if hasattr(query, 'items'):
        # dict-like
        pairs = list(query.items())
    else:
        # sequence of pairs
        pairs = list(query)

    result = []
    for k, v in pairs:
        if doseq and not isinstance(v, str) and hasattr(v, '__iter__'):
            for item in v:
                k_enc = quote_via(str(k), safe=safe, encoding=encoding, errors=errors)
                v_enc = quote_via(str(item), safe=safe, encoding=encoding, errors=errors)
                result.append(k_enc + '=' + v_enc)
        else:
            k_enc = quote_via(str(k), safe=safe, encoding=encoding, errors=errors)
            v_enc = quote_via(str(v), safe=safe, encoding=encoding, errors=errors)
            result.append(k_enc + '=' + v_enc)

    return '&'.join(result)


def urldefrag(url):
    """
    Remove the fragment from a URL, returning (url_without_fragment, fragment).
    If there is no fragment, fragment is an empty string.
    """
    if '#' in url:
        idx = url.index('#')
        return (url[:idx], url[idx+1:])
    else:
        return (url, '')


# --- Test/invariant functions ---

def urlparse3_quote_plus():
    """Returns quote_plus('hello world') which should equal 'hello+world'."""
    return quote_plus('hello world')


def urlparse3_unquote_plus():
    """Returns unquote_plus('hello+world') which should equal 'hello world'."""
    return unquote_plus('hello+world')


def urlparse3_urlencode():
    """Returns urlencode({'a': '1'}) which should equal 'a=1'."""
    return urlencode({'a': '1'})


__all__ = [
    'quote',
    'quote_plus',
    'unquote',
    'unquote_plus',
    'urlencode',
    'urldefrag',
    'urlparse3_quote_plus',
    'urlparse3_unquote_plus',
    'urlparse3_urlencode',
]