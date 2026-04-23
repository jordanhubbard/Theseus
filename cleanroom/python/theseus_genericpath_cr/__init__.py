"""
theseus_genericpath_cr — Clean-room genericpath module.
No import of the standard `genericpath` module.
These are OS-independent path utility functions.
"""

import os as _os
import os.path as _osp
import stat as _stat


def exists(path):
    """Return True if path refers to an existing path or open file descriptor."""
    try:
        _os.stat(path)
    except (OSError, ValueError):
        return False
    return True


def lexists(path):
    """Return True if path refers to an existing path (including broken symlinks)."""
    try:
        _os.lstat(path)
    except (OSError, ValueError):
        return False
    return True


def isfile(path):
    """Return True if path is an existing regular file."""
    try:
        st = _os.stat(path)
    except (OSError, ValueError):
        return False
    return _stat.S_ISREG(st.st_mode)


def isdir(path):
    """Return True if path is an existing directory."""
    try:
        st = _os.stat(path)
    except (OSError, ValueError):
        return False
    return _stat.S_ISDIR(st.st_mode)


def getsize(filename):
    """Return the size, in bytes, of the file specified by filename."""
    return _os.stat(filename).st_size


def getmtime(filename):
    """Return the last modification time of the file, as a floating point number."""
    return _os.stat(filename).st_mtime


def getatime(filename):
    """Return the last access time of the file, as a floating point number."""
    return _os.stat(filename).st_atime


def getctime(filename):
    """Return the metadata change time of the file."""
    return _os.stat(filename).st_ctime


def commonprefix(m):
    """Given a list of path names, return the longest common leading component."""
    if not m:
        return ''
    if len(m) == 1:
        return m[0]
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


def commonpath(paths):
    """Given a sequence of paths, return the longest common sub-path."""
    paths = list(paths)
    if not paths:
        raise ValueError('commonpath() arg is an empty sequence')

    sep = _os.sep
    split_paths = [p.split(sep) for p in paths]

    # Find common prefix of path components
    common = split_paths[0]
    for parts in split_paths[1:]:
        common = common[:len(parts)]
        for i, (c, p) in enumerate(zip(common, parts)):
            if c != p:
                common = common[:i]
                break

    if not common:
        raise ValueError('Paths don\'t have the same drive')

    return sep.join(common)


def _check_methods(C, *methods):
    mro = C.__mro__
    for method in methods:
        for B in mro:
            if method in B.__dict__:
                if B.__dict__[method] is None:
                    return NotImplemented
                break
        else:
            return NotImplemented
    return True


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def genpath2_exists():
    """exists() correctly tests file existence; returns True."""
    import tempfile as _tf
    import os as _os2
    with _tf.NamedTemporaryFile(delete=False) as f:
        fname = f.name
    try:
        result_exists = exists(fname)
        _os2.unlink(fname)
        result_not_exists = not exists(fname)
        return result_exists and result_not_exists
    except Exception:
        try:
            _os2.unlink(fname)
        except Exception:
            pass
        return False


def genpath2_commonprefix():
    """commonprefix() finds common path prefix; returns True."""
    return (commonprefix(['/usr/lib', '/usr/local/lib', '/usr/lib64']) == '/usr/l' and
            commonprefix(['/home/user', '/home/other']) == '/home/' and
            commonprefix([]) == '')


def genpath2_getsize():
    """getsize() returns file size; returns True."""
    import tempfile as _tf
    import os as _os2
    with _tf.NamedTemporaryFile(delete=False) as f:
        f.write(b'hello world')
        fname = f.name
    try:
        size = getsize(fname)
        _os2.unlink(fname)
        return size == 11
    except Exception:
        try:
            _os2.unlink(fname)
        except Exception:
            pass
        return False


__all__ = [
    'exists', 'lexists', 'isfile', 'isdir',
    'getsize', 'getmtime', 'getatime', 'getctime',
    'commonprefix', 'commonpath',
    'genpath2_exists', 'genpath2_commonprefix', 'genpath2_getsize',
]
