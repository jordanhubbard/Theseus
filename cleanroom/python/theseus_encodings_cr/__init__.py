"""
theseus_encodings_cr — Clean-room encodings module.
No import of the standard `encodings` module.
"""

import codecs as _codecs
import re as _re


class CodecRegistryError(LookupError):
    """Raised when a codec is not found in the registry."""
    pass


def normalize_encoding(encoding):
    """
    Normalize an encoding name.
    Converts to lowercase, replaces hyphens and spaces with underscores,
    strips leading/trailing underscores.
    """
    if isinstance(encoding, bytes):
        encoding = str(encoding, 'ascii')
    # Replace non-alphanumeric characters with underscore
    chars = []
    for c in encoding:
        if c.isalnum() or c == '.':
            chars.append(c.lower())
        else:
            chars.append('_')
    # Collapse multiple underscores
    result = ''.join(chars)
    result = _re.sub('_+', '_', result)
    result = result.strip('_')
    return result


def search_function(encoding):
    """Search for a codec by normalized encoding name."""
    norm = normalize_encoding(encoding)
    try:
        return _codecs.lookup(norm)
    except LookupError:
        return None


# Register our search function
_codecs.register(search_function)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def enc2_normalize():
    """normalize_encoding() normalizes codec names; returns True."""
    return (normalize_encoding('UTF-8') == 'utf_8' and
            normalize_encoding('iso-8859-1') == 'iso_8859_1' and
            normalize_encoding('ASCII') == 'ascii' and
            normalize_encoding('utf_8') == 'utf_8')


def enc2_search():
    """search_function() finds codecs via codecs module; returns True."""
    result = search_function('utf-8')
    return (result is not None and
            hasattr(result, 'encode') and
            hasattr(result, 'decode'))


def enc2_error_class():
    """CodecRegistryError exception class exists; returns True."""
    return (issubclass(CodecRegistryError, LookupError) and
            issubclass(CodecRegistryError, Exception))


__all__ = [
    'normalize_encoding', 'search_function', 'CodecRegistryError',
    'enc2_normalize', 'enc2_search', 'enc2_error_class',
]
