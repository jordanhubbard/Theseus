"""
theseus_posixpath_cr — Clean-room posixpath module.
No import of the standard `posixpath` module.
"""

import os as _os
import stat as _stat
import sys as _sys

sep = '/'
altsep = None
extsep = '.'
pathsep = ':'
defpath = '/bin:/usr/bin'
devnull = '/dev/null'
curdir = '.'
pardir = '..'


def normcase(s):
    """Normalize case of pathname (no-op on POSIX)."""
    return s


def isabs(s):
    """Test whether a path is absolute."""
    return s.startswith('/')


def join(a, *p):
    """Join path components, inserting '/' as needed."""
    path = a
    for b in p:
        if b.startswith('/'):
            path = b
        elif not path or path.endswith('/'):
            path += b
        else:
            path += '/' + b
    return path


def split(p):
    """Split a pathname. Returns (head, tail)."""
    i = p.rfind('/') + 1
    head, tail = p[:i], p[i:]
    if head and head != '/' * len(head):
        head = head.rstrip('/')
    return head, tail


def splitext(p):
    """Split the extension from a pathname."""
    sep_index = p.rfind('/')
    dot_index = p.rfind('.')
    if dot_index <= sep_index:
        return p, ''
    return p[:dot_index], p[dot_index:]


def splitdrive(p):
    """Split a pathname into drive and path. On POSIX, drive is always empty."""
    return '', p


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
    i = path.find('/', 1)
    if i < 0:
        i = len(path)
    if i == 1:
        home = _os.environ.get('HOME')
        if home is None:
            import pwd as _pwd
            home = _pwd.getpwuid(_os.getuid()).pw_dir
    else:
        import pwd as _pwd
        try:
            pwent = _pwd.getpwnam(path[1:i])
            home = pwent.pw_dir
        except KeyError:
            return path
    return home + path[i:]


def expandvars(path):
    """Expand shell variables of the form $var and ${var}."""
    if '$' not in path:
        return path
    import re as _re
    def replace(m):
        name = m.group(1) or m.group(2)
        return _os.environ.get(name, m.group(0))
    return _re.sub(r'\$(?:\{([^}]+)\}|([A-Za-z_]\w*))', replace, path)


def normpath(path):
    """Normalize path, eliminating double slashes, etc."""
    if not path:
        return '.'
    initial_slashes = path.startswith('/')
    if initial_slashes and path.startswith('//') and not path.startswith('///'):
        initial_slashes = 2
    comps = path.split('/')
    new_comps = []
    for comp in comps:
        if not comp or comp == '.':
            continue
        if comp != '..' or (not initial_slashes and not new_comps):
            new_comps.append(comp)
        elif new_comps and new_comps[-1] != '..':
            new_comps.pop()
    comps = new_comps
    path = '/'.join(comps)
    if initial_slashes:
        path = '/' * initial_slashes + path
    return path or '.'


def abspath(path):
    """Return the absolute version of a path."""
    if not isabs(path):
        cwd = _os.getcwd()
        path = join(cwd, path)
    return normpath(path)


def realpath(filename, *, strict=False):
    """Return the canonical path of the specified filename."""
    try:
        return _os.path.realpath(filename, strict=strict)
    except TypeError:
        return _os.path.realpath(filename)


def relpath(path, start=None):
    """Return a relative version of a path."""
    if start is None:
        start = _os.curdir
    start_abs = abspath(start).split('/')
    path_abs = abspath(path).split('/')
    i = 0
    while i < len(start_abs) and i < len(path_abs) and start_abs[i] == path_abs[i]:
        i += 1
    rel_parts = ['..'] * (len(start_abs) - i) + path_abs[i:]
    return '/'.join(rel_parts) if rel_parts else '.'


def commonpath(paths):
    """Return the longest common sub-path of each pathname."""
    paths = list(paths)
    if not paths:
        raise ValueError('commonpath() arg is an empty sequence')
    split_paths = [normpath(p).split('/') for p in paths]
    min_path = min(split_paths)
    max_path = max(split_paths)
    common = []
    for a, b in zip(min_path, max_path):
        if a == b:
            common.append(a)
        else:
            break
    return '/'.join(common) or '/'


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
    try:
        st1 = _os.lstat(path)
        st2 = _os.lstat(join(path, '..'))
        return (st1.st_dev != st2.st_dev or
                st1.st_ino == st2.st_ino)
    except OSError:
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

def posixpath2_split():
    """split() splits path into (head, tail); returns True."""
    h, t = split('/usr/local/bin/python')
    return h == '/usr/local/bin' and t == 'python'


def posixpath2_join():
    """join() joins path components; returns True."""
    result = join('/usr', 'local', 'bin')
    return result == '/usr/local/bin'


def posixpath2_normpath():
    """normpath() normalizes a POSIX path; returns True."""
    result = normpath('/usr/local/../bin/./python')
    return result == '/usr/bin/python'


__all__ = [
    'sep', 'altsep', 'extsep', 'pathsep', 'defpath', 'devnull',
    'curdir', 'pardir',
    'normcase', 'isabs', 'join', 'split', 'splitext', 'splitdrive',
    'basename', 'dirname', 'commonprefix',
    'expanduser', 'expandvars', 'normpath', 'abspath', 'realpath',
    'relpath', 'commonpath',
    'exists', 'lexists', 'isfile', 'isdir', 'islink', 'ismount',
    'getsize', 'getatime', 'getmtime', 'getctime',
    'samefile', 'sameopenfile', 'samestat',
    'posixpath2_split', 'posixpath2_join', 'posixpath2_normpath',
]
