"""Clean-room reimplementation of genericpath."""

import os
import stat as _stat
import tempfile


def exists(path):
    """Test whether a path exists. Returns False for broken symbolic links."""
    try:
        os.stat(path)
    except (OSError, ValueError):
        return False
    return True


def isfile(path):
    """Test whether a path is a regular file."""
    try:
        st = os.stat(path)
    except (OSError, ValueError):
        return False
    return _stat.S_ISREG(st.st_mode)


def isdir(s):
    """Return true if the pathname refers to an existing directory."""
    try:
        st = os.stat(s)
    except (OSError, ValueError):
        return False
    return _stat.S_ISDIR(st.st_mode)


def getsize(filename):
    """Return the size of a file, reported by os.stat()."""
    return os.stat(filename).st_size


def getmtime(filename):
    """Return the last modification time of a file, reported by os.stat()."""
    return os.stat(filename).st_mtime


def getatime(filename):
    """Return the last access time of a file, reported by os.stat()."""
    return os.stat(filename).st_atime


def getctime(filename):
    """Return the metadata change time of a file, reported by os.stat()."""
    return os.stat(filename).st_ctime


def commonprefix(m):
    """Given a list of pathnames, returns the longest common leading component."""
    if not m:
        return ''
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


def samestat(s1, s2):
    """Test whether two stat buffers reference the same file."""
    return (s1.st_ino == s2.st_ino and s1.st_dev == s2.st_dev)


def _splitext(p, sep, altsep, extsep):
    """Split the extension from a pathname."""
    sep_index = p.rfind(sep)
    if altsep:
        alt_index = p.rfind(altsep)
        if alt_index > sep_index:
            sep_index = alt_index

    dot_index = p.rfind(extsep)
    if dot_index > sep_index:
        filename_index = sep_index + 1
        while filename_index < dot_index:
            if p[filename_index:filename_index + 1] != extsep:
                return p[:dot_index], p[dot_index:]
            filename_index += 1
    return p, p[:0]


# ---------------------------------------------------------------------------
# Behavioral invariant entry points: each verifies a property and returns True.
# ---------------------------------------------------------------------------

def genpath2_exists():
    """exists() correctly tests file existence."""
    fd, tmp_path = tempfile.mkstemp()
    try:
        os.close(fd)
        if not exists(tmp_path):
            return False
        tmp_dir = tempfile.mkdtemp()
        try:
            if not exists(tmp_dir):
                return False
        finally:
            os.rmdir(tmp_dir)
    finally:
        os.unlink(tmp_path)

    if exists(tmp_path):
        return False

    bogus = os.path.join(tempfile.gettempdir(),
                         "theseus_genericpath_cr_nonexistent_xyz_123456")
    if exists(bogus):
        return False

    return True


def genpath2_commonprefix():
    """commonprefix() finds common path prefix."""
    if commonprefix([]) != '':
        return False
    if commonprefix(['/foo/bar']) != '/foo/bar':
        return False
    if commonprefix(['/foo/bar', '/foo/baz']) != '/foo/ba':
        return False
    if commonprefix(['/abc', '/xyz']) != '/':
        return False
    if commonprefix(['hello', 'hello']) != 'hello':
        return False
    if commonprefix(['abc', 'xyz']) != '':
        return False
    if commonprefix(['interspecies', 'interstellar', 'interstate']) != 'inters':
        return False
    return True


def genpath2_getsize():
    """getsize() returns file size."""
    payload = b"hello, theseus!"
    fd, tmp_path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(payload)
        size = getsize(tmp_path)
        if size != len(payload):
            return False
    finally:
        os.unlink(tmp_path)

    fd, tmp_path = tempfile.mkstemp()
    try:
        os.close(fd)
        if getsize(tmp_path) != 0:
            return False
    finally:
        os.unlink(tmp_path)

    return True