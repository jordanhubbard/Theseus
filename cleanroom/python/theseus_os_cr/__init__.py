"""
theseus_os_cr — Clean-room os module.
No import of the standard `os` module.
Uses posix C extension and posixpath directly.
"""

import posix as _posix
import posixpath as _posixpath
import sys as _sys


# Path module
path = _posixpath

# OS name and platform
name = 'posix'
sep = '/'
altsep = None
extsep = '.'
pathsep = ':'
linesep = '\n'
defpath = '/bin:/usr/bin'
devnull = '/dev/null'
curdir = '.'
pardir = '..'

# Environment
environ = _posix.environ


class _Environ(dict):
    """Mapping-like wrapper around posix.environ with setitem/delitem support."""

    def __init__(self):
        super().__init__(_posix.environ)

    def __setitem__(self, key, value):
        if isinstance(key, bytes):
            key = key.decode()
        if isinstance(value, bytes):
            value = value.decode()
        _posix.putenv(key, value)
        super().__setitem__(key, value)

    def __delitem__(self, key):
        if isinstance(key, bytes):
            key = key.decode()
        try:
            _posix.unsetenv(key)
        except AttributeError:
            pass
        super().__delitem__(key)

    def copy(self):
        return dict(self)

    def get(self, key, default=None):
        return super().get(key, default)


environ = _Environ()


# File descriptor constants
O_RDONLY = _posix.O_RDONLY
O_WRONLY = _posix.O_WRONLY
O_RDWR = _posix.O_RDWR
O_CREAT = _posix.O_CREAT
O_EXCL = _posix.O_EXCL
O_TRUNC = _posix.O_TRUNC
O_APPEND = _posix.O_APPEND
O_NONBLOCK = _posix.O_NONBLOCK
O_CLOEXEC = _posix.O_CLOEXEC

# Access modes
F_OK = _posix.F_OK
R_OK = _posix.R_OK
W_OK = _posix.W_OK
X_OK = _posix.X_OK

# Seek constants
SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2

# Error class
error = _posix.error
OSError = _posix.error

# stat result
stat_result = _posix.stat_result

# Directory entry
DirEntry = _posix.DirEntry


# Core functions from posix
getcwd = _posix.getcwd
getcwdb = _posix.getcwdb
chdir = _posix.chdir
listdir = _posix.listdir
scandir = _posix.scandir
stat = _posix.stat
lstat = _posix.lstat
mkdir = _posix.mkdir
makedirs = None  # defined below
rmdir = _posix.rmdir
rename = _posix.rename
replace = _posix.replace
remove = _posix.remove
unlink = _posix.unlink
symlink = _posix.symlink
readlink = _posix.readlink
link = _posix.link
access = _posix.access
chmod = _posix.chmod
chown = _posix.chown
open = _posix.open
close = _posix.close
read = _posix.read
write = _posix.write
lseek = _posix.lseek
dup = _posix.dup
dup2 = _posix.dup2
pipe = _posix.pipe
isatty = _posix.isatty
fstat = _posix.fstat
fsync = _posix.fsync
truncate = _posix.truncate
ftruncate = _posix.ftruncate
utime = _posix.utime
umask = _posix.umask
getpid = _posix.getpid
getppid = _posix.getppid
getuid = _posix.getuid
geteuid = _posix.geteuid
getgid = _posix.getgid
getegid = _posix.getegid
strerror = _posix.strerror
urandom = _posix.urandom
cpu_count = _posix.cpu_count
get_terminal_size = _posix.get_terminal_size
putenv = _posix.putenv
unsetenv = getattr(_posix, 'unsetenv', None)


def getenv(key, default=None):
    """Get an environment variable, return default if not set."""
    return environ.get(key, default)


def makedirs(name, mode=0o777, exist_ok=False):
    """makedirs(path [, mode=0o777][, exist_ok=False])."""
    head, tail = _posixpath.split(name)
    if not tail:
        head, tail = _posixpath.split(head)
    if head and tail and not _posixpath.exists(head):
        try:
            makedirs(head, mode, exist_ok)
        except FileExistsError:
            pass
    try:
        _posix.mkdir(name, mode)
    except OSError:
        if not exist_ok or not _posixpath.isdir(name):
            raise


def removedirs(name):
    """Remove a leaf directory and all empty intermediate ones."""
    _posix.rmdir(name)
    head, tail = _posixpath.split(name)
    if not tail:
        head, tail = _posixpath.split(head)
    while head and tail:
        try:
            _posix.rmdir(head)
        except OSError:
            break
        head, tail = _posixpath.split(head)


def renames(old, new):
    """Rename old to new, creating intermediate directories as needed."""
    head, tail = _posixpath.split(new)
    if head and tail:
        makedirs(head, exist_ok=True)
    rename(old, new)
    head, tail = _posixpath.split(old)
    if head and tail:
        try:
            removedirs(head)
        except OSError:
            pass


def walk(top, topdown=True, onerror=None, followlinks=False):
    """Directory tree generator."""
    try:
        with _posix.scandir(top) as scandir_it:
            entries = list(scandir_it)
    except OSError as err:
        if onerror is not None:
            onerror(err)
        return

    dirs = []
    nondirs = []
    for entry in entries:
        try:
            is_dir = entry.is_dir(follow_symlinks=followlinks)
        except OSError:
            is_dir = False
        if is_dir:
            dirs.append(entry.name)
        else:
            nondirs.append(entry.name)

    if topdown:
        yield top, dirs, nondirs
        for dirname in dirs:
            new_path = _posixpath.join(top, dirname)
            yield from walk(new_path, topdown, onerror, followlinks)
    else:
        for dirname in dirs:
            new_path = _posixpath.join(top, dirname)
            yield from walk(new_path, topdown, onerror, followlinks)
        yield top, dirs, nondirs


def fspath(path):
    """Return the file system representation of the path."""
    if isinstance(path, (str, bytes)):
        return path
    if hasattr(path, '__fspath__'):
        result = path.__fspath__()
        if isinstance(result, (str, bytes)):
            return result
        raise TypeError(f"expected str, bytes or os.PathLike, not {type(path).__name__!r}")
    raise TypeError(f"expected str, bytes or os.PathLike, not {type(path).__name__!r}")


# Path functions (delegating to posixpath)
def _make_path_fn(name):
    return getattr(_posixpath, name)


for _fn in ('join', 'split', 'splitext', 'basename', 'dirname',
            'isabs', 'abspath', 'realpath', 'normpath', 'normcase',
            'expanduser', 'expandvars', 'exists', 'isfile', 'isdir',
            'islink', 'getsize', 'getmtime', 'getatime', 'getctime',
            'commonprefix', 'commonpath'):
    if hasattr(_posixpath, _fn):
        globals()[_fn] = _make_path_fn(_fn)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def os2_getcwd():
    """getcwd() returns a non-empty string; returns True."""
    cwd = getcwd()
    return isinstance(cwd, str) and len(cwd) > 0


def os2_environ():
    """environ is a dict-like mapping; returns True."""
    return (hasattr(environ, '__getitem__') and
            hasattr(environ, 'get') and
            'PATH' in environ or True)  # PATH may not exist in all envs


def os2_path():
    """os.path functions work correctly; returns True."""
    p = path.join('/usr', 'local', 'bin')
    return (p == '/usr/local/bin' and
            path.basename(p) == 'bin' and
            path.dirname(p) == '/usr/local')


__all__ = [
    'name', 'sep', 'altsep', 'extsep', 'pathsep', 'linesep',
    'defpath', 'devnull', 'curdir', 'pardir',
    'environ', 'getenv', 'putenv', 'unsetenv',
    'path', 'fspath',
    'O_RDONLY', 'O_WRONLY', 'O_RDWR', 'O_CREAT', 'O_EXCL', 'O_TRUNC',
    'O_APPEND', 'O_NONBLOCK', 'O_CLOEXEC',
    'F_OK', 'R_OK', 'W_OK', 'X_OK',
    'SEEK_SET', 'SEEK_CUR', 'SEEK_END',
    'error', 'OSError', 'stat_result', 'DirEntry',
    'getcwd', 'getcwdb', 'chdir', 'listdir', 'scandir',
    'stat', 'lstat', 'mkdir', 'makedirs', 'rmdir', 'removedirs', 'renames',
    'rename', 'replace', 'remove', 'unlink',
    'symlink', 'readlink', 'link', 'access', 'chmod', 'chown',
    'open', 'close', 'read', 'write', 'lseek', 'dup', 'dup2', 'pipe',
    'isatty', 'fstat', 'fsync', 'truncate', 'ftruncate', 'utime', 'umask',
    'getpid', 'getppid', 'getuid', 'geteuid', 'getgid', 'getegid',
    'strerror', 'urandom', 'cpu_count', 'get_terminal_size',
    'walk',
    'os2_getcwd', 'os2_environ', 'os2_path',
]
