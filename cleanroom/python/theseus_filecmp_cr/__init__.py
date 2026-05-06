"""Clean-room implementation of a subset of the filecmp module."""

import os
import tempfile

_BUFSIZE = 8 * 1024


def _sig(st):
    """Return a stat signature: (type, size, mtime)."""
    return (
        getattr(st, "st_mode", 0) & 0o170000,  # file type bits
        st.st_size,
        st.st_mtime,
    )


def _do_cmp(f1, f2):
    """Byte-by-byte content compare; return True if files are identical."""
    try:
        with open(f1, "rb") as fp1, open(f2, "rb") as fp2:
            while True:
                b1 = fp1.read(_BUFSIZE)
                b2 = fp2.read(_BUFSIZE)
                if b1 != b2:
                    return False
                if not b1:
                    return True
    except OSError:
        return False


def cmp(f1, f2, shallow=True):
    """Compare two files. Return True if equal, False otherwise.

    If shallow is True, files are considered equal when their os.stat()
    signatures (type, size, mtime) match. Otherwise the file contents are
    compared byte-by-byte.
    """
    try:
        s1 = os.stat(f1)
        s2 = os.stat(f2)
    except OSError:
        return False

    sig1 = _sig(s1)
    sig2 = _sig(s2)

    # Both must be regular files (or at least not directories).
    if sig1[0] != 0o100000 or sig2[0] != 0o100000:
        # If either isn't a regular file, only equal if signatures match
        if sig1 != sig2:
            return False

    if shallow and sig1 == sig2:
        return True

    if sig1[1] != sig2[1]:
        # Different sizes => not equal.
        return False

    return _do_cmp(f1, f2)


def cmpfiles(dir1, dir2, common, shallow=True):
    """Compare common files in two directories.

    Returns a tuple (match, mismatch, errors):
      match    -- list of files that compare equal
      mismatch -- list of files that differ
      errors   -- list of files that could not be compared
    """
    match = []
    mismatch = []
    errors = []
    for name in common:
        p1 = os.path.join(dir1, name)
        p2 = os.path.join(dir2, name)
        try:
            ok = cmp(p1, p2, shallow)
        except OSError:
            errors.append(name)
            continue
        # Detect IO errors: cmp returns False on stat errors silently, so
        # do an explicit accessibility check before classifying.
        if not (os.path.exists(p1) and os.path.exists(p2)):
            errors.append(name)
        elif ok:
            match.append(name)
        else:
            mismatch.append(name)
    return match, mismatch, errors


# ---------------------------------------------------------------------------
# Invariant helpers — exercise the implementation against scratch files.
# ---------------------------------------------------------------------------

def _write(path, data):
    with open(path, "wb") as fp:
        fp.write(data)


def filecmp2_equal():
    """Two files with identical content compare equal under shallow=False."""
    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "a.bin")
        b = os.path.join(tmp, "b.bin")
        payload = b"theseus filecmp clean room equality check"
        _write(a, payload)
        _write(b, payload)
        return cmp(a, b, shallow=False) is True


def filecmp2_different():
    """Two files with different content do not compare equal."""
    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "a.bin")
        b = os.path.join(tmp, "b.bin")
        _write(a, b"alpha contents")
        _write(b, b"beta contents!!")
        return cmp(a, b, shallow=False)


def filecmp2_self():
    """A file always compares equal to itself."""
    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "a.bin")
        _write(a, b"comparing a file with itself must always be true")
        return cmp(a, a, shallow=True) is True


__all__ = [
    "cmp",
    "cmpfiles",
    "filecmp2_equal",
    "filecmp2_different",
    "filecmp2_self",
]