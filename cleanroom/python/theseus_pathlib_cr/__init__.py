"""Clean-room pathlib implementation for Theseus.

Provides PurePath, PurePosixPath, PureWindowsPath, Path, PosixPath, WindowsPath
without importing the standard library pathlib module.
"""

import os as _os
import sys as _sys
import re as _re
import stat as _stat


# ---------------------------------------------------------------------------
# Flavour helpers
# ---------------------------------------------------------------------------

class _PosixFlavour:
    sep = '/'
    altsep = ''
    has_drv = False
    pathmod = _os.path
    is_supported = (_os.name != 'nt')

    def splitroot(self, part):
        # Return (drv, root, rel)
        if part and part[0] == '/':
            stripped = part.lstrip('/')
            # POSIX: //foo is implementation-defined; ///foo is just /foo
            if len(part) - len(stripped) == 2:
                return '', '//', stripped
            return '', '/', stripped
        return '', '', part

    def casefold(self, s):
        return s

    def casefold_parts(self, parts):
        return parts

    def join(self, parts):
        return '/'.join(parts)

    def make_uri(self, path):
        bpath = bytes(str(path), 'utf-8')
        return 'file://' + _quote_from_bytes(bpath)


class _WindowsFlavour:
    sep = '\\'
    altsep = '/'
    has_drv = True
    pathmod = _os.path
    is_supported = (_os.name == 'nt')

    drive_letters = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    ext_namespace_prefix = '\\\\?\\'

    def splitroot(self, part):
        first = part[:1]
        second = part[1:2]
        # UNC: \\host\share\... or //host/share/...
        if (first == second == self.sep) or (first in (self.sep, self.altsep) and second in (self.sep, self.altsep)):
            # Possibly UNC
            normp = part.replace(self.altsep, self.sep)
            index = normp.find(self.sep, 2)
            if index != -1:
                index2 = normp.find(self.sep, index + 1)
                if index2 != index + 1:
                    if index2 == -1:
                        index2 = len(part)
                    drv = part[:index2]
                    root = self.sep
                    return drv, root, part[index2 + 1:]
            return '', '', part
        if second == ':' and first in self.drive_letters:
            drv = part[:2]
            third = part[2:3]
            if third in (self.sep, self.altsep):
                return drv, self.sep, part[3:]
            return drv, '', part[2:]
        if first in (self.sep, self.altsep):
            return '', self.sep, part[1:]
        return '', '', part

    def casefold(self, s):
        return s.lower()

    def casefold_parts(self, parts):
        return [p.lower() for p in parts]

    def join(self, parts):
        return '\\'.join(parts)


def _quote_from_bytes(b):
    safe = set(b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~/')
    out = []
    for byte in b:
        if byte in safe:
            out.append(chr(byte))
        else:
            out.append('%%%02X' % byte)
    return ''.join(out)


# ---------------------------------------------------------------------------
# PurePath
# ---------------------------------------------------------------------------

class PurePath:
    """Pure path manipulation class. Subclassed by PurePosixPath and PureWindowsPath."""

    _flavour = None  # set on subclasses

    def __new__(cls, *args):
        if cls is PurePath:
            cls = PureWindowsPath if _os.name == 'nt' else PurePosixPath
        return cls._from_parts(args)

    @classmethod
    def _from_parts(cls, args):
        self = object.__new__(cls)
        drv, root, parts = self._parse_args(args)
        self._drv = drv
        self._root = root
        self._parts = parts
        self._str_cache = None
        return self

    @classmethod
    def _parse_args(cls, args):
        # Collect all string parts
        parts = []
        for a in args:
            if isinstance(a, PurePath):
                parts.extend(a._parts_with_root())
            elif isinstance(a, str):
                parts.append(a)
            elif hasattr(a, '__fspath__'):
                p = a.__fspath__()
                if isinstance(p, bytes):
                    raise TypeError("argument should be a str or os.PathLike object, not bytes")
                parts.append(p)
            else:
                raise TypeError("argument should be a str or os.PathLike object, not %r" % type(a).__name__)
        return cls._parse_parts(parts)

    @classmethod
    def _parse_parts(cls, parts):
        flavour = cls._flavour
        sep = flavour.sep
        altsep = flavour.altsep
        drv = ''
        root = ''
        parsed = []
        for raw in parts:
            if not raw:
                continue
            if altsep:
                raw = raw.replace(altsep, sep)
            d, r, rel = flavour.splitroot(raw)
            if sep in rel:
                for x in rel.split(sep):
                    if x and x != '.':
                        parsed.append(x)
            else:
                if rel and rel != '.':
                    parsed.append(rel)
            if d:
                drv = d
                if r:
                    root = r
                # Once we hit an absolute drive, reset prior parsed in some flavours
                # but we'll keep as is for simplicity
            elif r:
                root = r
        # Construct final list with drv+root prefix
        final = []
        if drv or root:
            final.append(drv + root)
        final.extend(parsed)
        return drv, root, final

    def _parts_with_root(self):
        return list(self._parts)

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
        return tuple(self._parts)

    @property
    def name(self):
        if not self._parts:
            return ''
        if (self._drv or self._root) and len(self._parts) == 1:
            return ''
        return self._parts[-1]

    @property
    def suffix(self):
        name = self.name
        i = name.rfind('.')
        if 0 < i < len(name) - 1:
            return name[i:]
        # handle leading dots: '.bashrc' has no suffix, '..ext' edge
        if i > 0:
            return name[i:]
        return ''

    @property
    def suffixes(self):
        name = self.name
        if name.endswith('.'):
            return []
        name = name.lstrip('.')
        return ['.' + s for s in name.split('.')[1:]]

    @property
    def stem(self):
        name = self.name
        i = name.rfind('.')
        if 0 < i < len(name):
            return name[:i]
        return name

    @property
    def parent(self):
        drv = self._drv
        root = self._root
        parts = list(self._parts)
        if len(parts) == 1 and (drv or root):
            return self
        if not parts:
            return self
        new_parts = parts[:-1]
        return self._from_parsed_parts(drv, root, new_parts)

    @property
    def parents(self):
        return _PathParents(self)

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts):
        self = object.__new__(cls)
        self._drv = drv
        self._root = root
        self._parts = parts
        self._str_cache = None
        return self

    def __str__(self):
        if self._str_cache is None:
            if not self._parts:
                self._str_cache = '.'
            else:
                sep = self._flavour.sep
                first = self._parts[0]
                rest = self._parts[1:]
                if self._drv or self._root:
                    self._str_cache = first + sep.join(rest)
                else:
                    self._str_cache = sep.join(self._parts)
        return self._str_cache

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, str(self))

    def __fspath__(self):
        return str(self)

    def __bytes__(self):
        return _os.fsencode(str(self))

    def __hash__(self):
        return hash((type(self._flavour), self._flavour.casefold(str(self))))

    def __eq__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        if self._flavour is not other._flavour:
            return False
        return self._flavour.casefold(str(self)) == self._flavour.casefold(str(other))

    def __lt__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._flavour.casefold(str(self)) < self._flavour.casefold(str(other))

    def __le__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._flavour.casefold(str(self)) <= self._flavour.casefold(str(other))

    def __gt__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._flavour.casefold(str(self)) > self._flavour.casefold(str(other))

    def __ge__(self, other):
        if not isinstance(other, PurePath) or self._flavour is not other._flavour:
            return NotImplemented
        return self._flavour.casefold(str(self)) >= self._flavour.casefold(str(other))

    def __truediv__(self, other):
        return self.joinpath(other)

    def __rtruediv__(self, other):
        return type(self)(other, self)

    def joinpath(self, *args):
        return type(self)(self, *args)

    def is_absolute(self):
        if not self._root:
            return False
        if self._flavour.has_drv and not self._drv:
            return False
        return True

    def is_reserved(self):
        return False

    def as_posix(self):
        flavour = self._flavour
        return str(self).replace(flavour.sep, '/')

    def as_uri(self):
        if not self.is_absolute():
            raise ValueError("relative path can't be expressed as a file URI")
        return 'file://' + _quote_from_bytes(bytes(str(self), 'utf-8'))

    def with_name(self, name):
        if not self.name:
            raise ValueError("%r has an empty name" % self)
        if not name or name[-1:] in (self._flavour.sep, self._flavour.altsep) or name in ('.', '..'):
            raise ValueError("Invalid name %r" % name)
        new_parts = list(self._parts[:-1]) + [name]
        return self._from_parsed_parts(self._drv, self._root, new_parts)

    def with_suffix(self, suffix):
        if self._flavour.sep in suffix or (self._flavour.altsep and self._flavour.altsep in suffix):
            raise ValueError("Invalid suffix %r" % suffix)
        if suffix and not suffix.startswith('.') or suffix == '.':
            raise ValueError("Invalid suffix %r" % suffix)
        name = self.name
        if not name:
            raise ValueError("%r has an empty name" % self)
        old_suffix = self.suffix
        if not old_suffix:
            new_name = name + suffix
        else:
            new_name = name[:-len(old_suffix)] + suffix
        return self.with_name(new_name)

    def relative_to(self, *other):
        if not other:
            raise TypeError("need at least one argument")
        other_path = type(self)(*other)
        cf = self._flavour.casefold_parts
        my_parts = cf(self._parts)
        other_parts = cf(other_path._parts)
        n = len(other_parts)
        if my_parts[:n] != other_parts or self._drv.lower() != other_path._drv.lower():
            raise ValueError("%r is not in the subpath of %r" % (str(self), str(other_path)))
        rest = self._parts[n:]
        return self._from_parsed_parts('', '', list(rest))

    def match(self, pattern):
        if not pattern:
            raise ValueError("empty pattern")
        pat = type(self)(pattern)
        pat_parts = pat._parts
        if not pat_parts:
            raise ValueError("empty pattern")
        cf = self._flavour.casefold
        path_parts = [cf(p) for p in self._parts]
        pat_parts_cf = [cf(p) for p in pat_parts]
        if pat.is_absolute():
            if len(path_parts) != len(pat_parts_cf):
                return False
            for pp, ppat in zip(path_parts, pat_parts_cf):
                if not _fnmatch_case(pp, ppat):
                    return False
            return True
        if len(pat_parts_cf) > len(path_parts):
            return False
        for pp, ppat in zip(reversed(path_parts), reversed(pat_parts_cf)):
            if not _fnmatch_case(pp, ppat):
                return False
        return True


class _PathParents:
    def __init__(self, path):
        self._pathcls = type(path)
        self._drv = path._drv
        self._root = path._root
        self._parts = path._parts

    def __len__(self):
        if self._drv or self._root:
            return len(self._parts) - 1
        return len(self._parts)

    def __getitem__(self, idx):
        if idx < 0 or idx >= len(self):
            raise IndexError(idx)
        n = len(self._parts) - idx - 1
        return self._pathcls._from_parsed_parts(self._drv, self._root, self._parts[:n])


def _fnmatch_case(name, pat):
    """Case-sensitive fnmatch."""
    regex = _translate(pat)
    return _re.match(regex, name) is not None


def _translate(pat):
    """Translate a shell pattern to a regex."""
    i = 0
    n = len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i += 1
        if c == '*':
            res += '.*'
        elif c == '?':
            res += '.'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j += 1
            if j < n and pat[j] == ']':
                j += 1
            while j < n and pat[j] != ']':
                j += 1
            if j >= n:
                res += '\\['
            else:
                stuff = pat[i:j]
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res += '[' + stuff + ']'
                i = j + 1
        else:
            res += _re.escape(c)
    return r'(?s:' + res + r')\Z'


# ---------------------------------------------------------------------------
# Pure subclasses
# ---------------------------------------------------------------------------

class PurePosixPath(PurePath):
    _flavour = _PosixFlavour()
    __slots__ = ()


class PureWindowsPath(PurePath):
    _flavour = _WindowsFlavour()
    __slots__ = ()


# Set __slots__ on PurePath after subclasses are defined? We can't, so leave as-is.


# ---------------------------------------------------------------------------
# Concrete Path classes
# ---------------------------------------------------------------------------

class Path(PurePath):
    """Concrete path with filesystem operations."""

    def __new__(cls, *args):
        if cls is Path:
            cls = WindowsPath if _os.name == 'nt' else PosixPath
        self = cls._from_parts(args)
        if not self._flavour.is_supported:
            raise NotImplementedError(
                "cannot instantiate %r on your system" % (cls.__name__,))
        return self

    # ----- filesystem queries -----

    def stat(self):
        return _os.stat(str(self))

    def lstat(self):
        return _os.lstat(str(self))

    def exists(self):
        try:
            self.stat()
        except OSError:
            return False
        return True

    def is_dir(self):
        try:
            return _stat.S_ISDIR(self.stat().st_mode)
        except OSError:
            return False

    def is_file(self):
        try:
            return _stat.S_ISREG(self.stat().st_mode)
        except OSError:
            return False

    def is_symlink(self):
        try:
            return _stat.S_ISLNK(self.lstat().st_mode)
        except OSError:
            return False

    def is_socket(self):
        try:
            return _stat.S_ISSOCK(self.stat().st_mode)
        except OSError:
            return False

    def is_fifo(self):
        try:
            return _stat.S_ISFIFO(self.stat().st_mode)
        except OSError:
            return False

    def is_block_device(self):
        try:
            return _stat.S_ISBLK(self.stat().st_mode)
        except OSError:
            return False

    def is_char_device(self):
        try:
            return _stat.S_ISCHR(self.stat().st_mode)
        except OSError:
            return False

    # ----- filesystem actions -----

    def iterdir(self):
        for name in _os.listdir(str(self)):
            if name in ('.', '..'):
                continue
            yield self / name

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        try:
            _os.mkdir(str(self), mode)
        except FileNotFoundError:
            if not parents or self.parent == self:
                raise
            self.parent.mkdir(mode=mode, parents=True, exist_ok=True)
            _os.mkdir(str(self), mode)
        except FileExistsError:
            if not exist_ok or not self.is_dir():
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
        return type(self)(target)

    def replace(self, target):
        _os.replace(str(self), str(target))
        return type(self)(target)

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
        s = _os.path.realpath(str(self))
        return type(self)(s)

    def absolute(self):
        if self.is_absolute():
            return self
        return type(self)(_os.getcwd(), self)

    def cwd(cls=None):
        return Path(_os.getcwd())
    cwd = classmethod(cwd)

    def home(cls=None):
        return Path(_os.path.expanduser('~'))
    home = classmethod(home)

    def expanduser(self):
        if self._parts and self._parts[0].startswith('~'):
            expanded = _os.path.expanduser(self._parts[0])
            new_parts = [expanded] + list(self._parts[1:])
            return type(self)(*new_parts)
        return self

    def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        return open(str(self), mode, buffering, encoding, errors, newline)

    def read_bytes(self):
        with self.open('rb') as f:
            return f.read()

    def read_text(self, encoding=None, errors=None):
        with self.open('r', encoding=encoding, errors=errors) as f:
            return f.read()

    def write_bytes(self, data):
        view = memoryview(data)
        with self.open('wb') as f:
            return f.write(view)

    def write_text(self, data, encoding=None, errors=None):
        if not isinstance(data, str):
            raise TypeError("data must be str, not %s" % type(data).__name__)
        with self.open('w', encoding=encoding, errors=errors) as f:
            return f.write(data)


class PosixPath(Path, PurePosixPath):
    __slots__ = ()


class WindowsPath(Path, PureWindowsPath):
    __slots__ = ()


# ---------------------------------------------------------------------------
# Invariant verification functions
# ---------------------------------------------------------------------------

def pathlib2_pure():
    """Verify pure path operations work correctly."""
    try:
        # Construction
        p = PurePosixPath('/usr/bin/python')
        if str(p) != '/usr/bin/python':
            return False
        # Drive/root
        if p.root != '/' or p.drive != '' or p.anchor != '/':
            return False
        # Name/stem/suffix
        if p.name != 'python' or p.stem != 'python' or p.suffix != '':
            return False
        p2 = PurePosixPath('/tmp/file.tar.gz')
        if p2.name != 'file.tar.gz' or p2.suffix != '.gz' or p2.stem != 'file.tar':
            return False
        if p2.suffixes != ['.tar', '.gz']:
            return False
        # Absoluteness
        if not p.is_absolute():
            return False
        if PurePosixPath('relative/path').is_absolute():
            return False
        # Joining
        joined = PurePosixPath('/usr') / 'bin' / 'python'
        if str(joined) != '/usr/bin/python':
            return False
        # Equality
        if PurePosixPath('/a/b') != PurePosixPath('/a/b'):
            return False
        # Windows
        w = PureWindowsPath('C:\\Users\\test')
        if w.drive != 'C:' or w.root != '\\':
            return False
        if w.as_posix() != 'C:/Users/test':
            return False
        # with_name / with_suffix
        if str(PurePosixPath('/a/b.txt').with_name('c.py')) != '/a/c.py':
            return False
        if str(PurePosixPath('/a/b.txt').with_suffix('.py')) != '/a/b.py':
            return False
        # relative_to
        rel = PurePosixPath('/a/b/c').relative_to('/a')
        if str(rel) != 'b/c':
            return False
        # match
        if not PurePosixPath('a/b.py').match('*.py'):
            return False
        return True
    except Exception:
        return False


def pathlib2_concrete():
    """Verify concrete path operations work correctly."""
    try:
        cwd = Path.cwd()
        if not isinstance(cwd, Path):
            return False
        if not isinstance(cwd, PurePath):
            return False
        if not cwd.is_absolute():
            return False
        # Existence check on cwd
        if not cwd.exists():
            return False
        if not cwd.is_dir():
            return False
        # Home
        home = Path.home()
        if not isinstance(home, Path):
            return False
        # iterdir works on a real directory (cwd)
        items = list(cwd.iterdir())
        for it in items[:3]:
            if not isinstance(it, Path):
                return False
        # absolute()
        rel = Path('.')
        absp = rel.absolute()
        if not absp.is_absolute():
            return False
        # resolve()
        resolved = rel.resolve()
        if not resolved.is_absolute():
            return False
        # __fspath__
        if rel.__fspath__() != '.':
            return False
        return True
    except Exception:
        return False


def pathlib2_parts():
    """Verify the parts attribute and parent traversal work correctly."""
    try:
        p = PurePosixPath('/usr/local/bin/python')
        if p.parts != ('/', 'usr', 'local', 'bin', 'python'):
            return False
        # Parent
        if str(p.parent) != '/usr/local/bin':
            return False
        if str(p.parent.parent) != '/usr/local':
            return False
        # parents
        parents = list(p.parents)
        expected = ['/usr/local/bin', '/usr/local', '/usr', '/']
        if [str(x) for x in parents] != expected:
            return False
        # len(parents)
        if len(p.parents) != 4:
            return False
        # Relative path
        r = PurePosixPath('a/b/c')
        if r.parts != ('a', 'b', 'c'):
            return False
        rparents = [str(x) for x in r.parents]
        if rparents != ['a/b', 'a', '.']:
            return False
        # Windows parts
        w = PureWindowsPath('C:\\Users\\test\\file.txt')
        if w.parts != ('C:\\', 'Users', 'test', 'file.txt'):
            return False
        # Empty path
        e = PurePosixPath()
        if str(e) != '.':
            return False
        if e.parts != ():
            return False
        # Single component
        s = PurePosixPath('foo')
        if s.parts != ('foo',):
            return False
        if s.name != 'foo':
            return False
        return True
    except Exception:
        return False


__all__ = [
    'PurePath', 'PurePosixPath', 'PureWindowsPath',
    'Path', 'PosixPath', 'WindowsPath',
    'pathlib2_pure', 'pathlib2_concrete', 'pathlib2_parts',
]