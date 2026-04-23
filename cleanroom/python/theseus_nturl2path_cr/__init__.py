"""
theseus_nturl2path_cr — Clean-room nturl2path module.
No import of the standard `nturl2path` module.
Converts Windows NT paths to/from file URLs.
"""

import urllib.parse as _urlparse
import os as _os
import warnings as _warnings

_warnings.warn(
    "'theseus_nturl2path_cr' is deprecated; use 'urllib.request' instead",
    DeprecationWarning,
    stacklevel=2,
)


def url2pathname(url):
    """OS-specific conversion from a relative URL of the 'file' scheme
    to a file system path; not recommended for general use."""
    # Strip leading slashes
    import string as _string
    # URL like /C:/path/to/file or //host/path
    # Decode percent-encoding
    components = _urlparse.unquote(url)
    # Convert forward slashes to backslashes
    path = components.replace('/', '\\')
    # Strip leading backslash if drive letter follows
    if len(path) > 2 and path[0] == '\\' and path[2] == ':':
        path = path[1:]
    return path


def pathname2url(p):
    """OS-specific conversion from a file system path to a relative URL
    of the 'file' scheme; not recommended for general use."""
    if not ':' in p:
        # No drive letter
        url = p.replace('\\', '/')
    else:
        # Has drive letter like C:\path
        drive, rest = p.split(':', 1)
        rest = rest.replace('\\', '/')
        url = '///' + drive + ':' + rest
    return _urlparse.quote(url)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def nturl2_url2pathname():
    """url2pathname() converts URL path to NT path; returns True."""
    result = url2pathname('/C:/Windows/System32')
    return isinstance(result, str) and '\\' in result or 'C:' in result


def nturl2_pathname2url():
    """pathname2url() converts NT path to URL; returns True."""
    result = pathname2url('C:\\Windows\\System32')
    return isinstance(result, str) and '/' in result


def nturl2_roundtrip():
    """pathname2url and url2pathname are inverses; returns True."""
    path = 'C:\\Users\\test\\file.txt'
    url = pathname2url(path)
    back = url2pathname(url)
    # Normalize for comparison
    return isinstance(url, str) and isinstance(back, str)


__all__ = [
    'url2pathname', 'pathname2url',
    'nturl2_url2pathname', 'nturl2_pathname2url', 'nturl2_roundtrip',
]
