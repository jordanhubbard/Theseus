"""
theseus_ntpath_cr — Clean-room ntpath module.
No import of the standard `ntpath` module.
"""

import os as _os
import stat as _stat
import sys as _sys

sep = '\\'
altsep = '/'
extsep = '.'
pathsep = ';'
defpath = r'.;C:\bin'
devnull = 'nul'
curdir = '.'
pardir = '..'


def normcase(s):
    """Normalize case of pathname; lowercase on Windows."""
    return s.replace('/', '\\').lower()


def isabs(s):
    """Test whether a path is absolute."""
    s = s[:3]
    s = s.replace('/', '\\')
    if len(s) >= 2 and s[1] == ':':
        if len(s) >= 3 and s[2] == '\\':
            return True
        return False
    if s[:2] == '\\\\':
        return True
    if s[:1] == '\\':
        return True
    return False


def join(path, *paths):
    """Join path components, inserting sep as needed."""
    result = path
    for p in paths:
        if isabs(p):
            result = p
        elif result and result[-1] not in (sep, altsep, ':'):
            result = result + sep + p
        else:
            result = result + p
    return result


def split(p):
    """Split a pathname into (drive+directory, filename)."""
    seps = sep + (altsep or '')
    i = len(p)
    while i > 0 and p[i-1] not in seps:
        i -= 1
    head, tail = p[:i], p[i:]
    # Strip trailing seps from head, unless it's the root
    while head and head[-1] in seps and head not in ('/', '\\', '//'):
        drive, _ = splitdrive(head)
        if drive and len(head) == len(drive) + 1:
            break
        head = head[:-1]
    return head, tail


def splitdrive(p):
    """Split a pathname into drive specification and the rest of the path."""
    if len(p) >= 2:
        if p[0] in sep + altsep and p[1] in sep + altsep:
            # UNC path
            index = p.find(sep, 2)
            if index < 0:
                index = p.find(altsep, 2)
            if index < 0:
                return p[:0], p
            index2 = p.find(sep, index + 1)
            if index2 < 0:
                index2 = p.find(altsep, index + 1)
            if index2 < 0:
                return p, p[:0]
            return p[:index2], p[index2:]
        if p[1] == ':':
            return p[:2], p[2:]
    return p[:0], p


def splitext(p):
    """Split the extension from a pathname."""
    i = p.rfind('.')
    if i <= max(p.rfind('/'), p.rfind('\\')):
        return p, ''
    return p[:i], p[i:]


def basename(p):
    """Return the final component of a pathname."""
    return split(p)[1]


def dirname(p):
    """Return the directory component of a pathname."""
    return split(p)[0]


def commonprefix(m):
    """Given a list of pathnames, return the longest common leading component."""
    if not m:
        return ''
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


def expanduser(path):
    """Expand ~ and ~user constructs."""
    if not path.startswith('~'):
        return path
    i = 1
    while i < len(path) and path[i] not in (sep, altsep or sep):
        i += 1
    if i == 1:
        userhome = _os.environ.get('USERPROFILE') or _os.environ.get('HOME') or '~'
    else:
        userhome = _os.path.join(_os.path.dirname(_os.environ.get('USERPROFILE', '~')),
                                  path[1:i])
    return userhome + path[i:]


def expandvars(path):
    """Expand shell variables of the form $var and ${var}."""
    if '$' not in path and '%' not in path:
        return path
    import re as _re
    def replace_var(m):
        name = m.group(1) or m.group(2)
        return _os.environ.get(name, m.group(0))
    path = _re.sub(r'%([^%]+)%', replace_var, path)
    path = _re.sub(r'\$(?:\{([^}]+)\}|(\w+))', replace_var, path)
    return path


def normpath(path):
    """Normalize path, eliminating double slashes, etc."""
    path = path.replace(altsep, sep)
    prefix, path = splitdrive(path)
    # Collapse slashes
    parts = path.split(sep)
    comps = []
    for part in parts:
        if not part or part == '.':
            if not comps and not prefix:
                comps.append('')
        elif part == '..':
            if comps and comps[-1] != '..':
                comps.pop()
            elif not comps or comps[0] != '':
                comps.append('..')
        else:
            comps.append(part)
    if comps == ['']:
        comps = []
    path = sep.join(comps)
    if prefix:
        path = prefix + sep + path if path else prefix + sep
    elif not path:
        path = '.'
    return path


def abspath(path):
    """Return the absolute version of a path."""
    if not isabs(path):
        cwd = _os.getcwd()
        path = join(cwd, path)
    return normpath(path)


def realpath(path, *, strict=False):
    """Return the canonical path of the specified filename."""
    return abspath(path)


def relpath(path, start=None):
    """Return a relative version of a path."""
    if start is None:
        start = _os.curdir
    start_abs = abspath(normcase(start))
    path_abs = abspath(normcase(path))
    start_parts = start_abs.split(sep)
    path_parts = path_abs.split(sep)
    # Find common prefix
    i = 0
    while i < len(start_parts) and i < len(path_parts):
        if start_parts[i] != path_parts[i]:
            break
        i += 1
    rel_parts = ['..'] * (len(start_parts) - i) + path_parts[i:]
    return sep.join(rel_parts) if rel_parts else '.'


def commonpath(paths):
    """Return the longest common sub-path of each pathname."""
    paths = list(paths)
    if not paths:
        raise ValueError('commonpath() arg is an empty sequence')
    split_paths = [normpath(p).split(sep) for p in paths]
    min_path = min(split_paths)
    max_path = max(split_paths)
    for i, part in enumerate(min_path):
        if part != max_path[i]:
            return sep.join(min_path[:i]) or sep
    return sep.join(min_path)


def exists(path):
    try:
        _os.stat(path)
        return True
    except OSError:
        return False


def lexists(path):
    try:
        _os.lstat(path)
        return True
    except OSError:
        return False


def isfile(path):
    try:
        st = _os.stat(path)
        return _stat.S_ISREG(st.st_mode)
    except OSError:
        return False


def isdir(path):
    try:
        st = _os.stat(path)
        return _stat.S_ISDIR(st.st_mode)
    except OSError:
        return False


def islink(path):
    try:
        st = _os.lstat(path)
        return _stat.S_ISLNK(st.st_mode)
    except OSError:
        return False


def ismount(path):
    """Test whether a path is a mount point."""
    if isabs(path):
        drive, rest = splitdrive(path)
        if not rest or rest in (sep, altsep):
            return True
    return False


def getsize(filename):
    return _os.stat(filename).st_size


def getatime(filename):
    return _os.stat(filename).st_atime


def getmtime(filename):
    return _os.stat(filename).st_mtime


def getctime(filename):
    return _os.stat(filename).st_ctime


def samefile(f1, f2):
    st1 = _os.stat(f1)
    st2 = _os.stat(f2)
    return (st1.st_ino == st2.st_ino and st1.st_dev == st2.st_dev)


def sameopenfile(fp1, fp2):
    st1 = _os.fstat(fp1)
    st2 = _os.fstat(fp2)
    return (st1.st_ino == st2.st_ino and st1.st_dev == st2.st_dev)


def samestat(stat1, stat2):
    return (stat1.st_ino == stat2.st_ino and stat1.st_dev == stat2.st_dev)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def ntpath2_split():
    """split() splits path into (head, tail); returns True."""
    h, t = split(r'C:\Users\test\file.txt')
    return h == r'C:\Users\test' and t == 'file.txt'


def ntpath2_join():
    """join() joins path components; returns True."""
    result = join(r'C:\Users', 'test', 'file.txt')
    return result == r'C:\Users\test\file.txt'


def ntpath2_normpath():
    """normpath() normalizes a Windows path; returns True."""
    result = normpath(r'C:\Users\test\..\file.txt')
    return result == r'C:\Users\file.txt'


__all__ = [
    'sep', 'altsep', 'extsep', 'pathsep', 'defpath', 'devnull',
    'curdir', 'pardir',
    'normcase', 'isabs', 'join', 'split', 'splitdrive', 'splitext',
    'basename', 'dirname', 'commonprefix',
    'expanduser', 'expandvars', 'normpath', 'abspath', 'realpath',
    'relpath', 'commonpath',
    'exists', 'lexists', 'isfile', 'isdir', 'islink', 'ismount',
    'getsize', 'getatime', 'getmtime', 'getctime',
    'samefile', 'sameopenfile', 'samestat',
    'ntpath2_split', 'ntpath2_join', 'ntpath2_normpath',
]
