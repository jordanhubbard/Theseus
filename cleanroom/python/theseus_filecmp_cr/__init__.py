"""
theseus_filecmp_cr — Clean-room filecmp module.
No import of the standard `filecmp` module.
"""

import os


def cmp(f1, f2, shallow=True):
    """Compare two files; return True if they are equal.
    
    shallow=True: compare only os.stat() signatures (faster).
    shallow=False: compare file contents.
    """
    s1 = os.stat(f1)
    s2 = os.stat(f2)

    if s1.st_size != s2.st_size:
        return False

    if shallow:
        return (s1.st_size == s2.st_size and
                s1.st_mtime == s2.st_mtime)

    # Full content comparison
    with open(f1, 'rb') as fh1, open(f2, 'rb') as fh2:
        chunk_size = 8192
        while True:
            b1 = fh1.read(chunk_size)
            b2 = fh2.read(chunk_size)
            if b1 != b2:
                return False
            if not b1:
                return True


def cmpfiles(dir1, dir2, common, shallow=True):
    """Compare a list of files in two directories.
    
    Returns (match, mismatch, errors) — three lists of filenames.
    """
    match = []
    mismatch = []
    errors = []

    for name in common:
        f1 = os.path.join(dir1, name)
        f2 = os.path.join(dir2, name)
        try:
            if cmp(f1, f2, shallow):
                match.append(name)
            else:
                mismatch.append(name)
        except OSError:
            errors.append(name)

    return (match, mismatch, errors)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def _make_temp_file(content):
    """Create a temp file with given content, return its path."""
    import random as _random
    tmpdir = os.environ.get('TMPDIR', '/tmp')
    path = os.path.join(tmpdir, 'filecmp_%08x.tmp' % _random.randint(0, 0xFFFFFFFF))
    with open(path, 'wb') as f:
        f.write(content)
    return path


def filecmp2_equal():
    """cmp of two identical temp files returns True."""
    f1 = _make_temp_file(b'same content here')
    f2 = _make_temp_file(b'same content here')
    try:
        return cmp(f1, f2, shallow=False)
    finally:
        os.unlink(f1)
        os.unlink(f2)


def filecmp2_different():
    """cmp of two different temp files returns False."""
    f1 = _make_temp_file(b'content A')
    f2 = _make_temp_file(b'content B')
    try:
        return cmp(f1, f2, shallow=False)
    finally:
        os.unlink(f1)
        os.unlink(f2)


def filecmp2_self():
    """cmp(f, f) is always True."""
    f = _make_temp_file(b'some data')
    try:
        return cmp(f, f, shallow=False)
    finally:
        os.unlink(f)


__all__ = [
    'cmp', 'cmpfiles',
    'filecmp2_equal', 'filecmp2_different', 'filecmp2_self',
]
