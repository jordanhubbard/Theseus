"""
theseus_glob_cr — Clean-room glob module.
No import of the standard `glob` module.
"""

import os as _os
import re as _re
import fnmatch as _fnmatch


def _glob1(dirname, pattern, dironly):
    if not dirname:
        dirname = _os.curdir
    try:
        names = _os.listdir(dirname)
    except OSError:
        return []
    if dironly:
        names = [x for x in names if _os.path.isdir(_os.path.join(dirname, x))]
    names = [x for x in names if not x.startswith('.') or pattern.startswith('.')]
    return _fnmatch.filter(names, pattern)


def _glob0(dirname, basename, dironly):
    if not basename:
        if _os.path.isdir(dirname):
            return [basename]
    else:
        if _os.path.lexists(_os.path.join(dirname, basename)):
            return [basename]
    return []


def _iterdir(dirname, dironly):
    if not dirname:
        dirname = _os.curdir
    try:
        it = _os.scandir(dirname)
    except OSError:
        return
    try:
        for entry in it:
            try:
                if not dironly or entry.is_dir():
                    yield entry.name
            except OSError:
                pass
    finally:
        it.close()


def _rlistdir(dirname, dironly):
    names = list(_iterdir(dirname, dironly))
    for name in names:
        path = _os.path.join(dirname, name) if dirname else name
        for child in _rlistdir(path, dironly):
            yield _os.path.join(name, child)
    yield from names


def _has_magic(s):
    return any(c in s for c in '*?[')


def iglob(pathname, *, recursive=False):
    """Return an iterator which yields the paths matching a pathname pattern."""
    dirname, basename = _os.path.split(pathname)

    if not _has_magic(pathname):
        if basename:
            if _os.path.lexists(pathname):
                yield pathname
        else:
            if _os.path.isdir(dirname):
                yield pathname
        return

    if _has_magic(dirname):
        dirs = iglob(dirname, recursive=recursive)
    else:
        dirs = [dirname]

    glob_in_dir = _glob1 if _has_magic(basename) else _glob0
    dironly = not basename

    for d in dirs:
        for name in glob_in_dir(d, basename, dironly):
            yield _os.path.join(d, name) if d else name


def glob(pathname, *, recursive=False):
    """Return a list of paths matching a pathname pattern."""
    return list(iglob(pathname, recursive=recursive))


def escape(pathname):
    """Escape all special characters in pathname."""
    drive, pathname = _os.path.splitdrive(pathname)
    pathname = _re.sub(r'([*?[])', r'[\1]', pathname)
    return drive + pathname


def glob2_star():
    """glob returns a list object; returns True."""
    results = glob('*.py')
    return isinstance(results, list)


def glob2_escape():
    """escape replaces [ with [[] making it literal; returns True."""
    e = escape('[hello')
    return '[[]' in e


def glob2_iglob():
    """iglob returns a generator; returns True."""
    it = iglob('*.py')
    return hasattr(it, '__iter__') and hasattr(it, '__next__')


__all__ = [
    'glob', 'iglob', 'escape',
    'glob2_star', 'glob2_escape', 'glob2_iglob',
]
