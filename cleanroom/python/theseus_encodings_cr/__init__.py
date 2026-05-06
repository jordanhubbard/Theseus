"""
theseus_encodings_cr — Clean-room encodings module.

This module provides a small subset of the standard library `encodings`
package interface: a name-normalization helper, a codec search function,
and a CodecRegistryError exception class.

It is implemented from scratch and does NOT import the original
`encodings` package. The `codecs` module is used only to resolve
already-registered codecs by their normalized name.
"""

import codecs as _codecs


# ---------------------------------------------------------------------------
# Exception class
# ---------------------------------------------------------------------------

class CodecRegistryError(LookupError):
    """Raised when a codec cannot be located in the registry."""
    pass


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

def normalize_encoding(encoding):
    """
    Normalize an encoding name.

    The normalized name is lower-cased; any run of one or more
    non-alphanumeric (and non-dot) characters is replaced by a single
    underscore, except at the very start of the name (leading runs
    of punctuation are dropped).

    Examples::

        normalize_encoding('UTF-8')       -> 'utf_8'
        normalize_encoding('iso-8859-1')  -> 'iso_8859_1'
        normalize_encoding('ASCII')       -> 'ascii'
        normalize_encoding('utf_8')       -> 'utf_8'
    """
    if isinstance(encoding, (bytes, bytearray)):
        encoding = bytes(encoding).decode('ascii')

    chars = []
    punct = False
    for c in encoding:
        if c.isalnum() or c == '.':
            if punct and chars:
                chars.append('_')
            chars.append(c.lower())
            punct = False
        else:
            punct = True
    return ''.join(chars)


# ---------------------------------------------------------------------------
# Codec search
# ---------------------------------------------------------------------------

def search_function(encoding):
    """
    Search for a codec by name.

    The supplied name is normalized via `normalize_encoding`, and the
    resulting name is looked up via the standard `codecs` registry.
    On success, the corresponding `CodecInfo` is returned. On failure
    (no such codec), `None` is returned, matching the contract that
    codec search functions must satisfy.
    """
    norm = normalize_encoding(encoding)
    if not norm:
        return None
    try:
        return _codecs.lookup(norm)
    except LookupError:
        return None


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def enc2_normalize():
    """normalize_encoding() normalizes codec names; returns True."""
    return (
        normalize_encoding('UTF-8') == 'utf_8'
        and normalize_encoding('iso-8859-1') == 'iso_8859_1'
        and normalize_encoding('ASCII') == 'ascii'
        and normalize_encoding('utf_8') == 'utf_8'
        and normalize_encoding(b'UTF-8') == 'utf_8'
    )


def enc2_search():
    """search_function() finds codecs via codecs module; returns True."""
    result = search_function('utf-8')
    if result is None:
        return False
    if not (hasattr(result, 'encode') and hasattr(result, 'decode')):
        return False
    # Round-trip check on a simple ASCII string.
    encoded, _n = result.encode('hello')
    decoded, _m = result.decode(encoded)
    if decoded != 'hello':
        return False
    # Also confirm a hyphenated alias resolves the same way.
    other = search_function('UTF-8')
    return other is not None


def enc2_error_class():
    """CodecRegistryError exception class exists; returns True."""
    if not isinstance(CodecRegistryError, type):
        return False
    if not issubclass(CodecRegistryError, LookupError):
        return False
    if not issubclass(CodecRegistryError, Exception):
        return False
    # Ensure it is actually raisable / catchable.
    try:
        raise CodecRegistryError('test')
    except LookupError:
        return True
    except Exception:
        return False
    return False


__all__ = [
    'CodecRegistryError',
    'normalize_encoding',
    'search_function',
    'enc2_normalize',
    'enc2_search',
    'enc2_error_class',
]