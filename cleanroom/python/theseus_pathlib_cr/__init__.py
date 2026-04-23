"""
theseus_pathlib_cr — Clean-room pathlib module.
No import of the standard `pathlib` module.
Pure-Python path implementation using os and os.path.
"""

import os as _os
import os.path as _osp
import sys as _sys
import stat as _stat_mod
import fnmatch as _fnmatch


_WINDOWS = _sys.platform == 'win32'
_SEP = '\\' if _WINDOWS else '/'


class _Flavour:
    sep = _SEP
    altsep = None
    has_drv = _WINDOWS

    def parse_parts(self, parts):
        parsed = []
        drv = root = ''
        for p in reversed(parts):
            p = str(p)
            if not p:
                continue
            drv2, root2, rel = self._split_root(p)
            if root2:
                if not drv:
                    drv = drv2
                root = root2
                parsed.append(drv + root + rel)
                break
            parsed.append(rel)
        parsed.reverse()
        return drv, root, parsed

    def _split_root(self, path):
        if _WINDOWS:
            if len(path) >= 2 and path[1] == ':':
                drv = path[:2]
                path = path[2:]
                if path and path[0] in '/\\':
                    root = path[0]
                    path = path[1:]
                else:
                    root = ''
                return drv, root, path
            if path and path[0] in '/\\':
                if len(path) >= 2 and path[1] in '/\\':
                    # UNC path
                    idx = path.find(path[2:3], 2)
                    if idx == -1:
                        return '', path[:2], path[2:]
                    return '', path[:idx + 1], path[idx + 1:]
                return '', path[0], path[1:]
            return '', '', path
        else:
            if path and path[0] == '/':
                return '', '/', path[1:]
            return '', '', path

    def join(self, paths):
        return _osp.join(*paths) if paths else ''

    def normcase(self, s):
        return s.lower() if _WINDOWS else s


_flavour = _Flavour()


class PurePath:
    """Base class for manipulating paths without I/O."""

    __slots__ = ('_drv', '_root', '_parts', '_str')

    def __new__(cls, *args):
        if cls is PurePath:
            if _WINDOWS:
                cls = PureWindowsPath
            else:
                cls = PurePosixPath
        return cls._from_parts(args)

    @classmethod
    def _from_parts(cls, args):
        obj = object.__new__(cls)
        drv, root, parts = _flavour.parse_parts(args)
        obj._drv = drv
        obj._root = root
        obj._parts = parts
        obj._str = None
        return obj

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts):
        obj = object.__new__(cls)
        obj._drv = drv
        obj._root = root
        obj._parts = parts
        obj._str = None
        return obj

    def __str__(self):
        if self._str is None:
            if self._parts:
                sep = _flavour.sep
                self._str = sep.join(self._parts)
                if self._root and not self._str.startswith(self._root):
                    self._str = self._root + self._str
            else:
                self._str = self._drv + self._root or '.'
        return self._str

    def __fspath__(self):
        return str(self)

    def __repr__(self):
        return f"{type(self).__name__}({str(self)!r})"

    def __eq__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        return (self._drv == other._drv and
                self._root == other._root and
                self._parts == other._parts)

    def __hash__(self):
        return hash((self._drv, self._root, tuple(self._parts)))

    def __lt__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        return str(self) < str(other)

    def __le__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        return str(self) <= str(other)

    def __gt__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        return str(self) > str(other)

    def __ge__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        return str(self) >= str(other)

    def __truediv__(self, key):
        try:
            return type(self)(str(self), str(key))
        except TypeError:
            return NotImplemented

    def __rtruediv__(self, key):
        try:
            return type(self)(str(key), str(self))
        except TypeError:
            return NotImplemented

    @property
    def drive(self):
        return self._drv

    @property
    def root(self):
        return self._root

    @property
    def anchor(self):
        return self._drv + self._root

    @property
    def parts(self):
        path_str = str(self)
        if path_str == '.':
            return ('.',)
        sep = _flavour.sep
        if self._root:
            rest = path_str[len(self._drv + self._root):]
            components = [p for p in rest.split(sep) if p]
            return (self._root,) + tuple(components)
        components = [p for p in path_str.split(sep) if p]
        return tuple(components)

    @property
    def parent(self):
        path = str(self)
        parent = _osp.dirname(path)
        if parent == path:
            return self
        return type(self)(parent)

    @property
    def parents(self):
        path = self
        parents = []
        while True:
            parent = path.parent
            if parent == path:
                break
            parents.append(parent)
            path = parent
        return tuple(parents)

    @property
    def name(self):
        return _osp.basename(str(self))

    @property
    def suffix(self):
        name = self.name
        i = name.rfind('.')
        if i > 0:
            return name[i:]
        return ''

    @property
    def suffixes(self):
        name = self.name
        parts = name.split('.')
        if len(parts) > 1:
            return ['.' + p for p in parts[1:]]
        return []

    @property
    def stem(self):
        name = self.name
        i = name.rfind('.')
        if i > 0:
            return name[:i]
        return name

    def with_name(self, name):
        parent = str(self.parent)
        return type(self)(_osp.join(parent, name))

    def with_stem(self, stem):
        return self.with_name(stem + self.suffix)

    def with_suffix(self, suffix):
        if suffix and not suffix.startswith('.'):
            raise ValueError(f"Invalid suffix {suffix!r}")
        return self.with_name(self.stem + suffix)

    def relative_to(self, *other):
        other_path = type(self)(*other)
        self_str = str(self)
        other_str = str(other_path)
        if not self_str.startswith(other_str):
            raise ValueError(f"{self_str!r} is not relative to {other_str!r}")
        rel = self_str[len(other_str):]
        if rel.startswith(_flavour.sep):
            rel = rel[1:]
        if not rel:
            return type(self)('.')
        return type(self)(rel)

    def is_relative_to(self, *other):
        try:
            self.relative_to(*other)
            return True
        except ValueError:
            return False

    def is_absolute(self):
        return bool(self._root)

    def match(self, pattern):
        return _fnmatch.fnmatch(str(self), pattern)

    def joinpath(self, *args):
        return type(self)(str(self), *[str(a) for a in args])

    def as_posix(self):
        return str(self).replace('\\', '/')

    def as_uri(self):
        if not self.is_absolute():
            raise ValueError("relative path can't be expressed as a file URI")
        return 'file://' + self.as_posix()

    def __bytes__(self):
        return str(self).encode()


class PurePosixPath(PurePath):
    """PurePath subclass for POSIX systems."""
    __slots__ = ()


class PureWindowsPath(PurePath):
    """PurePath subclass for Windows systems."""
    __slots__ = ()


class Path(PurePath):
    """Concrete path implementation with I/O operations."""

    __slots__ = ()

    def __new__(cls, *args):
        if cls is Path:
            if _WINDOWS:
                cls = WindowsPath
            else:
                cls = PosixPath
        return cls._from_parts(args)

    def stat(self, *, follow_symlinks=True):
        if follow_symlinks:
            return _os.stat(str(self))
        return _os.lstat(str(self))

    def exists(self, *, follow_symlinks=True):
        try:
            self.stat(follow_symlinks=follow_symlinks)
            return True
        except OSError:
            return False

    def is_file(self, *, follow_symlinks=True):
        try:
            st = self.stat(follow_symlinks=follow_symlinks)
            return _stat_mod.S_ISREG(st.st_mode)
        except OSError:
            return False

    def is_dir(self, *, follow_symlinks=True):
        try:
            st = self.stat(follow_symlinks=follow_symlinks)
            return _stat_mod.S_ISDIR(st.st_mode)
        except OSError:
            return False

    def is_symlink(self):
        try:
            st = _os.lstat(str(self))
            return _stat_mod.S_ISLNK(st.st_mode)
        except OSError:
            return False

    def is_absolute(self):
        return _osp.isabs(str(self))

    def resolve(self, strict=False):
        return type(self)(_osp.realpath(str(self)))

    def open(self, mode='r', buffering=-1, encoding=None, errors=None,
             newline=None):
        return open(str(self), mode=mode, buffering=buffering,
                    encoding=encoding, errors=errors, newline=newline)

    def read_bytes(self):
        with self.open('rb') as f:
            return f.read()

    def read_text(self, encoding=None, errors=None):
        with self.open(encoding=encoding, errors=errors) as f:
            return f.read()

    def write_bytes(self, data):
        with self.open('wb') as f:
            return f.write(data)

    def write_text(self, data, encoding=None, errors=None):
        with self.open('w', encoding=encoding, errors=errors) as f:
            return f.write(data)

    def iterdir(self):
        for name in _os.listdir(str(self)):
            yield type(self)(str(self), name)

    def glob(self, pattern):
        import glob as _glob_mod
        for p in _glob_mod.glob(_osp.join(str(self), pattern)):
            yield type(self)(p)

    def rglob(self, pattern):
        for p in self.glob('**/' + pattern):
            yield p

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        if parents:
            _os.makedirs(str(self), mode=mode, exist_ok=exist_ok)
        else:
            try:
                _os.mkdir(str(self), mode)
            except FileExistsError:
                if not exist_ok:
                    raise

    def rmdir(self):
        _os.rmdir(str(self))

    def unlink(self, missing_ok=False):
        try:
            _os.unlink(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    def rename(self, target):
        _os.rename(str(self), str(target))
        return type(self)(str(target))

    def replace(self, target):
        _os.replace(str(self), str(target))
        return type(self)(str(target))

    def symlink_to(self, target, target_is_directory=False):
        _os.symlink(str(target), str(self))

    def hardlink_to(self, target):
        _os.link(str(target), str(self))

    def touch(self, mode=0o666, exist_ok=True):
        if exist_ok:
            try:
                _os.utime(str(self))
                return
            except OSError:
                pass
        flags = _os.O_CREAT | _os.O_WRONLY
        if not exist_ok:
            flags |= _os.O_EXCL
        fd = _os.open(str(self), flags, mode)
        _os.close(fd)

    def samefile(self, other_path):
        st1 = self.stat()
        st2 = Path(str(other_path)).stat()
        return (st1.st_ino == st2.st_ino and st1.st_dev == st2.st_dev)

    @classmethod
    def cwd(cls):
        return cls(_os.getcwd())

    @classmethod
    def home(cls):
        return cls(_osp.expanduser('~'))


class PosixPath(Path, PurePosixPath):
    """Path subclass for POSIX systems."""
    __slots__ = ()


class WindowsPath(Path, PureWindowsPath):
    """Path subclass for Windows systems."""
    __slots__ = ()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pathlib2_pure():
    """PurePosixPath parts/name/suffix work; returns True."""
    p = PurePosixPath('/usr/local/lib/python3.py')
    return (p.name == 'python3.py' and
            p.stem == 'python3' and
            p.suffix == '.py' and
            p.parent == PurePosixPath('/usr/local/lib'))


def pathlib2_concrete():
    """Path.cwd() and .is_dir() work; returns True."""
    p = Path.cwd()
    return p.is_dir() and p.exists() and isinstance(str(p), str)


def pathlib2_parts():
    """Path division operator and parts work; returns True."""
    p = PurePosixPath('/usr') / 'local' / 'bin'
    return (str(p) == '/usr/local/bin' and
            p.parts == ('/', 'usr', 'local', 'bin'))


__all__ = [
    'PurePath', 'PurePosixPath', 'PureWindowsPath',
    'Path', 'PosixPath', 'WindowsPath',
    'pathlib2_pure', 'pathlib2_concrete', 'pathlib2_parts',
]
