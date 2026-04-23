"""
theseus_pathlib_extra_cr — Clean-room pathlib module.
No import of the standard `pathlib` module.
"""

import os as _os
import os.path as _osp
import fnmatch as _fnmatch
import re as _re
import stat as _stat


class _PureFlavour:
    sep = '/'
    altsep = None
    has_drv = False
    is_reserved = False
    pathmod = _osp

    def parse_parts(self, parts):
        parsed = []
        sep = self.sep
        altsep = self.altsep
        drv = root = ''
        it = reversed(parts)
        for part in it:
            if not part:
                continue
            if altsep:
                part = part.replace(altsep, sep)
            drv, root, rel = self.splitroot(part)
            if sep in rel:
                for x in reversed(rel.split(sep)):
                    if x and x != '.':
                        parsed.append(x)
            elif rel and rel != '.':
                parsed.append(rel)
            if drv or root:
                if not drv:
                    for part in it:
                        if not part:
                            continue
                        if altsep:
                            part = part.replace(altsep, sep)
                        drv = self.splitroot(part)[0]
                        if drv:
                            break
                break
        if drv or root:
            parsed.append(drv + root)
        parsed.reverse()
        return drv, root, parsed

    def splitroot(self, part):
        sep = self.sep
        if part and part[0] == sep:
            stripped_part = part.lstrip(sep)
            if len(part) - len(stripped_part) == 2:
                return '', sep + sep, stripped_part
            else:
                return '', sep, stripped_part
        else:
            return '', '', part

    def casefold(self, s):
        return s

    def casefold_parts(self, parts):
        return parts

    def compile_pattern(self, pattern):
        return _re.compile(_fnmatch.translate(pattern)).match

    def is_reserved(self, parts):
        return False

    def make_uri(self, path):
        return 'file://' + path.as_posix()

    def gethomedir(self, username):
        if not username:
            return _osp.expanduser('~')
        import pwd
        return pwd.getpwnam(username).pw_dir


class _WindowsFlavour(_PureFlavour):
    sep = '\\'
    altsep = '/'
    has_drv = True

    def splitroot(self, part):
        first = part[0:1]
        second = part[1:2]
        if second == self.sep and first == self.sep:
            index = part.find(self.sep, 2)
            if index != -1:
                index2 = part.find(self.sep, index + 1)
                if index2 != index + 1:
                    if index2 == -1:
                        index2 = len(part)
                    drv = part[:index2]
                    root = part[index2:index2 + 1]
                    return drv, root, part[index2 + len(root):]
            return part[:2], '', part[2:]
        if first == self.sep:
            return '', self.sep, part[1:]
        if second == ':':
            drv = part[:2]
            rest = part[2:]
            if rest[:1] == self.sep:
                return drv, self.sep, rest[1:]
            return drv, '', rest
        return '', '', part

    def casefold(self, s):
        return s.lower()

    def casefold_parts(self, parts):
        return [p.lower() for p in parts]

    def make_uri(self, path):
        drive = path.drive
        if drive[:1] == self.sep:
            return 'file:' + path.as_posix()
        return 'file:///' + path.as_posix()

    def gethomedir(self, username):
        if not username:
            return _osp.expanduser('~')
        return _osp.join(_osp.expandvars('%HOMEPATH%'))


_posix_flavour = _PureFlavour()
_windows_flavour = _WindowsFlavour()


class PurePath:
    """Base class for pure path objects (no I/O)."""
    _flavour = _posix_flavour
    __slots__ = ('_drv', '_root', '_parts', '_str', '_hash')

    def __new__(cls, *args):
        obj = object.__new__(cls)
        drv, root, parts = obj._flavour.parse_parts(args)
        obj._drv = drv
        obj._root = root
        obj._parts = parts
        return obj

    def __str__(self):
        try:
            return self._str
        except AttributeError:
            self._str = self._format_parsed_parts(self._drv, self._root, self._parts) or '.'
            return self._str

    @classmethod
    def _format_parsed_parts(cls, drv, root, parts):
        if drv or root:
            return drv + root + cls._flavour.sep.join(parts[1:])
        else:
            return cls._flavour.sep.join(parts)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __bytes__(self):
        return str(self).encode()

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(tuple(self._flavour.casefold_parts(self._parts)))
            return self._hash

    def __eq__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        return (self._flavour.casefold_parts(self._parts) ==
                other._flavour.casefold_parts(other._parts) and
                self._flavour is other._flavour)

    def __lt__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._parts < other._parts

    def __le__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._parts <= other._parts

    def __gt__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._parts > other._parts

    def __ge__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._parts >= other._parts

    def __truediv__(self, key):
        return self._make_child((str(key),))

    def __rtruediv__(self, key):
        return self._from_parsed_parts('', '', [str(key)])._make_child(self._parts)

    def _make_child(self, args):
        drv, root, parts = self._flavour.parse_parts(args)
        drv, root, parts = self._flavour.parse_parts([str(self)] + list(args))
        return self._from_parsed_parts(drv, root, parts)

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts):
        obj = object.__new__(cls)
        obj._drv = drv
        obj._root = root
        obj._parts = parts
        return obj

    @property
    def parts(self):
        if self._drv or self._root:
            return tuple([self._drv + self._root] + self._parts[1:])
        else:
            return tuple(self._parts)

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
    def parents(self):
        return _PathParents(self)

    @property
    def parent(self):
        drv = self._drv
        root = self._root
        parts = self._parts
        if len(parts) == 1 and (drv or root):
            return self
        if len(parts) > 1:
            return self._from_parsed_parts(drv, root, parts[:-1])
        return self._from_parsed_parts(drv, root, [])

    @property
    def name(self):
        parts = self._parts
        if len(parts) == (1 if (self._drv or self._root) else 0):
            return ''
        return parts[-1]

    @property
    def suffix(self):
        name = self.name
        i = name.rfind('.')
        if 0 < i < len(name) - 1:
            return name[i:]
        return ''

    @property
    def suffixes(self):
        name = self.name
        if name.endswith('.'):
            return []
        name = name.lstrip('.')
        return ['.' + suffix for suffix in name.split('.')[1:]]

    @property
    def stem(self):
        name = self.name
        suffix = self.suffix
        if suffix:
            return name[:-len(suffix)]
        return name

    def with_name(self, name):
        if not self.name:
            raise ValueError('%r has an empty name' % self)
        parts = self._parts[:-1] + [name]
        return self._from_parsed_parts(self._drv, self._root, parts)

    def with_stem(self, stem):
        return self.with_name(stem + self.suffix)

    def with_suffix(self, suffix):
        if not suffix:
            return self.with_name(self.stem)
        return self.with_name(self.stem + suffix)

    def relative_to(self, *other):
        other_parts = self.__class__(*other)._parts
        if other_parts != self._parts[:len(other_parts)]:
            raise ValueError('%r is not relative to %r' % (self, other))
        parts = self._parts[len(other_parts):]
        return self._from_parsed_parts('', '', parts)

    def is_relative_to(self, *other):
        try:
            self.relative_to(*other)
            return True
        except ValueError:
            return False

    def is_absolute(self):
        return bool(self._root)

    def is_reserved(self):
        return self._flavour.is_reserved(self._parts)

    def match(self, pattern):
        cf = self._flavour.casefold
        pattern_parts = list(reversed(PurePath(pattern)._parts))
        if not pattern_parts:
            raise ValueError('empty pattern')
        parts = list(reversed([cf(p) for p in self._parts]))
        if len(pattern_parts) > len(parts):
            return False
        for pp, p in zip(pattern_parts, parts):
            if not _fnmatch.fnmatchcase(p, cf(pp)):
                return False
        return True

    def joinpath(self, *args):
        return self._make_child(args)

    def as_posix(self):
        return str(self).replace('\\', '/')

    def as_uri(self):
        if not self.is_absolute():
            raise ValueError('relative path cannot be expressed as a URI')
        return self._flavour.make_uri(self)


class _PathParents:
    __slots__ = ('_pathcls', '_drv', '_root', '_parts')

    def __init__(self, path):
        self._pathcls = type(path)
        self._drv = path._drv
        self._root = path._root
        self._parts = path._parts

    def __len__(self):
        if self._drv or self._root:
            return len(self._parts) - 1
        else:
            return len(self._parts)

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))
        if idx < 0 or idx >= len(self):
            raise IndexError(idx)
        return self._pathcls._from_parsed_parts(self._drv, self._root, self._parts[:-idx - 1])

    def __repr__(self):
        return '<{}.parents>'.format(self._pathcls.__name__)


class PurePosixPath(PurePath):
    """PurePath subclass for non-Windows systems."""
    _flavour = _posix_flavour
    __slots__ = ()


class PureWindowsPath(PurePath):
    """PurePath subclass for Windows systems."""
    _flavour = _windows_flavour
    __slots__ = ()


class Path(PurePath):
    """Concrete path implementation with I/O."""
    __slots__ = ()

    def __new__(cls, *args, **kwargs):
        if cls is Path:
            cls = WindowsPath if _os.name == 'nt' else PosixPath
        obj = cls._from_parsed_parts(*cls._flavour.parse_parts(args))
        return obj

    def stat(self, *, follow_symlinks=True):
        if follow_symlinks:
            return _os.stat(self)
        return _os.lstat(self)

    def lstat(self):
        return self.stat(follow_symlinks=False)

    def exists(self):
        try:
            self.stat()
            return True
        except OSError:
            return False

    def is_file(self):
        try:
            return _stat.S_ISREG(self.stat().st_mode)
        except OSError:
            return False

    def is_dir(self):
        try:
            return _stat.S_ISDIR(self.stat().st_mode)
        except OSError:
            return False

    def is_symlink(self):
        try:
            return _stat.S_ISLNK(self.lstat().st_mode)
        except OSError:
            return False

    def is_absolute(self):
        return bool(self._root)

    def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        return open(str(self), mode=mode, buffering=buffering, encoding=encoding,
                    errors=errors, newline=newline)

    def read_bytes(self):
        with self.open('rb') as f:
            return f.read()

    def read_text(self, encoding=None, errors=None):
        with self.open('r', encoding=encoding, errors=errors) as f:
            return f.read()

    def write_bytes(self, data):
        with self.open('wb') as f:
            return f.write(data)

    def write_text(self, data, encoding=None, errors=None, newline=None):
        with self.open('w', encoding=encoding, errors=errors, newline=newline) as f:
            return f.write(data)

    def iterdir(self):
        for name in _os.listdir(self):
            yield self._make_child((name,))

    def glob(self, pattern):
        selector = _WildcardSelector(pattern, self._flavour)
        for path in selector.select_from(self):
            yield path

    def rglob(self, pattern):
        return self.glob('**/' + pattern)

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        try:
            _os.mkdir(str(self), mode)
        except FileNotFoundError:
            if not parents or self.parent == self:
                raise
            self.parent.mkdir(parents=True, exist_ok=True)
            self.mkdir(mode, parents=False, exist_ok=exist_ok)
        except OSError:
            if not exist_ok or not self.is_dir():
                raise

    def unlink(self, missing_ok=False):
        try:
            _os.unlink(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise

    def rmdir(self):
        _os.rmdir(str(self))

    def rename(self, target):
        _os.rename(str(self), str(target))
        return self.__class__(target)

    def replace(self, target):
        _os.replace(str(self), str(target))
        return self.__class__(target)

    def symlink_to(self, target, target_is_directory=False):
        _os.symlink(str(target), str(self), target_is_directory)

    def hardlink_to(self, target):
        _os.link(str(target), str(self))

    def touch(self, mode=0o666, exist_ok=True):
        if exist_ok:
            try:
                _os.utime(str(self), None)
            except OSError:
                pass
            else:
                return
        flags = _os.O_CREAT | _os.O_WRONLY
        if not exist_ok:
            flags |= _os.O_EXCL
        fd = _os.open(str(self), flags, mode)
        _os.close(fd)

    def resolve(self, strict=False):
        try:
            return self.__class__(_osp.realpath(str(self)))
        except OSError:
            if strict:
                raise
            return self.__class__(_osp.abspath(str(self)))

    def absolute(self):
        return self.__class__(_osp.abspath(str(self)))

    @classmethod
    def cwd(cls):
        return cls(_os.getcwd())

    @classmethod
    def home(cls):
        return cls(_osp.expanduser('~'))

    def owner(self):
        import pwd
        return pwd.getpwuid(self.stat().st_uid).pw_name

    def group(self):
        import grp
        return grp.getgrgid(self.stat().st_gid).gr_name

    def __fspath__(self):
        return str(self)


class _WildcardSelector:
    def __init__(self, pattern, flavour):
        self.pattern = pattern
        self.flavour = flavour

    def select_from(self, parent_path):
        try:
            entries = list(parent_path.iterdir())
        except PermissionError:
            return
        pat = self.pattern
        if '**' in pat:
            yield from self._rselect(parent_path, pat)
        else:
            for entry in entries:
                if _fnmatch.fnmatch(entry.name, pat):
                    yield entry

    def _rselect(self, parent, pattern):
        parts = pattern.split('**/', 1)
        pre = parts[0]
        post = parts[1] if len(parts) > 1 else ''
        try:
            for entry in parent.iterdir():
                if entry.is_dir():
                    yield from self._rselect(entry, '**/' + post if post else '**')
                if post:
                    if _fnmatch.fnmatch(entry.name, post):
                        yield entry
                else:
                    yield entry
        except PermissionError:
            pass


class PosixPath(Path, PurePosixPath):
    """Path subclass for POSIX."""
    __slots__ = ()


class WindowsPath(Path, PureWindowsPath):
    """Path subclass for Windows."""
    __slots__ = ()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pathlib2_parts():
    """PurePosixPath splits path into parts correctly; returns True."""
    p = PurePosixPath('/usr/bin/python')
    return p.parts == ('/', 'usr', 'bin', 'python')


def pathlib2_stem():
    """PurePosixPath.stem returns filename without extension; returns True."""
    p = PurePosixPath('/path/to/file.txt')
    return p.stem == 'file' and p.suffix == '.txt'


def pathlib2_joinpath():
    """PurePosixPath / operator joins paths; returns True."""
    p = PurePosixPath('/usr') / 'bin' / 'python'
    return str(p) == '/usr/bin/python'


__all__ = [
    'PurePath', 'PurePosixPath', 'PureWindowsPath',
    'Path', 'PosixPath', 'WindowsPath',
    'pathlib2_parts', 'pathlib2_stem', 'pathlib2_joinpath',
]
