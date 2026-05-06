"""Clean-room pathlib-like module providing PurePosixPath and PureWindowsPath.

This implementation does not import the standard pathlib module.
"""

import os as _os
import re as _re


# ---------------------------------------------------------------------------
# Flavour helpers
# ---------------------------------------------------------------------------

class _PosixFlavour:
    sep = '/'
    altsep = ''
    has_drv = False
    is_supported = True

    def splitroot(self, part):
        # Returns (drive, root, rest)
        if part and part[0] == '/':
            stripped = part.lstrip('/')
            # POSIX: exactly two leading slashes is implementation-defined
            if len(part) - len(stripped) == 2:
                return '', '//', stripped
            return '', '/', stripped
        return '', '', part

    def casefold(self, s):
        return s

    def casefold_parts(self, parts):
        return parts


class _WindowsFlavour:
    sep = '\\'
    altsep = '/'
    has_drv = True
    is_supported = True

    drive_letters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def splitroot(self, part):
        # Normalize altsep to sep for analysis
        first = part[:1]
        second = part[1:2]
        # UNC: \\server\share or //server/share
        if (first in ('\\', '/')) and (second in ('\\', '/')):
            # Find the server and share
            third = part[2:3]
            if third in ('\\', '/'):
                # \\\... triple slash - treat as just root
                return '', first * 2, part[2:].lstrip('\\/')
            # parse server
            i = 2
            while i < len(part) and part[i] not in ('\\', '/'):
                i += 1
            if i == 2:
                # no server
                return '', first * 2, part[2:].lstrip('\\/')
            server_end = i
            # skip separator
            j = server_end
            while j < len(part) and part[j] in ('\\', '/'):
                j += 1
            # parse share
            k = j
            while k < len(part) and part[k] not in ('\\', '/'):
                k += 1
            if k == j:
                # no share - just treat first two as root
                drv = part[:server_end]
                return drv, '', part[server_end:].lstrip('\\/')
            drv = part[:k]
            # Replace separators in drv with backslash
            drv = '\\\\' + part[2:server_end] + '\\' + part[j:k]
            rest = part[k:]
            if rest and rest[0] in ('\\', '/'):
                root = '\\'
                rest = rest[1:].lstrip('\\/') if False else rest.lstrip('\\/')
                # Actually we want only one root
                # rest already has separator removed; restore semantic
            else:
                root = ''
            return drv, root, rest
        # Drive letter: C: or C:\
        if len(part) >= 2 and part[0] in self.drive_letters and part[1] == ':':
            drv = part[:2]
            rest = part[2:]
            if rest and rest[0] in ('\\', '/'):
                return drv, '\\', rest[1:].lstrip('\\/') if False else rest[1:]
            return drv, '', rest
        # No drive
        if part and part[0] in ('\\', '/'):
            return '', '\\', part.lstrip('\\/')
        return '', '', part

    def casefold(self, s):
        return s.lower()

    def casefold_parts(self, parts):
        return [p.lower() for p in parts]


_posix_flavour = _PosixFlavour()
_windows_flavour = _WindowsFlavour()


# ---------------------------------------------------------------------------
# PurePath base
# ---------------------------------------------------------------------------

class PurePath(object):
    """Base class for pure path objects."""

    _flavour = None  # set by subclasses

    def __init__(self, *args):
        parts = []
        for a in args:
            if isinstance(a, PurePath):
                # Use its string form
                parts.append(str(a))
            elif isinstance(a, str):
                parts.append(a)
            else:
                raise TypeError(
                    "argument should be a str or an os.PathLike "
                    "object, not %r" % type(a).__name__
                )
        self._raw_paths = parts
        self._parse()

    # -- Parsing ------------------------------------------------------------
    def _parse(self):
        flavour = self._flavour
        sep = flavour.sep
        altsep = flavour.altsep

        if not self._raw_paths:
            self._drv = ''
            self._root = ''
            self._parts = []
            return

        # Combine like joinpath: subsequent absolute paths replace,
        # subsequent drive paths replace drive.
        drv = ''
        root = ''
        parts = []  # list of components (no separators)

        for raw in self._raw_paths:
            if not raw:
                continue
            s = raw
            if altsep:
                s = s.replace(altsep, sep)
            d, r, rest = flavour.splitroot(s)
            if d:
                if r or not parts or flavour.casefold(d) != flavour.casefold(drv):
                    # New drive (or absolute on this drive): replace
                    drv = d
                    root = r
                    parts = []
                else:
                    # Same drive, no root: append rest
                    pass
            elif r:
                # Absolute on current drive
                root = r
                parts = []
            # split rest by sep
            if rest:
                for comp in rest.split(sep):
                    if comp and comp != '.':
                        parts.append(comp)

        self._drv = drv
        self._root = root
        self._parts = parts

    # -- String form --------------------------------------------------------
    def __str__(self):
        s = self._format_parsed_parts()
        return s or '.'

    def _format_parsed_parts(self):
        sep = self._flavour.sep
        if self._drv or self._root:
            return self._drv + self._root + sep.join(self._parts)
        return sep.join(self._parts)

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, str(self))

    def __fspath__(self):
        return str(self)

    # -- Equality / hashing -------------------------------------------------
    def _key(self):
        f = self._flavour
        return (
            f.casefold(self._drv),
            f.casefold(self._root),
            tuple(f.casefold_parts(self._parts)),
        )

    def __eq__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        if other._flavour is not self._flavour:
            return NotImplemented
        return self._key() == other._key()

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash(self._key())

    def __lt__(self, other):
        if not isinstance(other, PurePath) or other._flavour is not self._flavour:
            return NotImplemented
        return self._key() < other._key()

    def __le__(self, other):
        if not isinstance(other, PurePath) or other._flavour is not self._flavour:
            return NotImplemented
        return self._key() <= other._key()

    def __gt__(self, other):
        if not isinstance(other, PurePath) or other._flavour is not self._flavour:
            return NotImplemented
        return self._key() > other._key()

    def __ge__(self, other):
        if not isinstance(other, PurePath) or other._flavour is not self._flavour:
            return NotImplemented
        return self._key() >= other._key()

    # -- Properties ---------------------------------------------------------
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
        sep = self._flavour.sep
        result = []
        if self._drv or self._root:
            result.append(self._drv + self._root)
        result.extend(self._parts)
        return tuple(result)

    @property
    def name(self):
        if self._parts:
            return self._parts[-1]
        return ''

    @property
    def suffix(self):
        n = self.name
        i = n.rfind('.')
        if 0 < i < len(n) - 1:
            return n[i:]
        # Handle leading dot files: ".bashrc" has no suffix
        if i > 0 and i == len(n) - 1:
            return n[i:]
        return ''

    @property
    def suffixes(self):
        n = self.name
        if n.endswith('.'):
            return []
        n = n.lstrip('.')
        if not n:
            return []
        return ['.' + s for s in n.split('.')[1:]]

    @property
    def stem(self):
        n = self.name
        i = n.rfind('.')
        if 0 < i < len(n):
            # Skip leading-dot files: stem of ".bashrc" is ".bashrc"
            # (the '.' must not be the only leading dot)
            return n[:i]
        return n

    @property
    def parent(self):
        if not self._parts:
            return self
        new = object.__new__(type(self))
        new._flavour = self._flavour
        new._drv = self._drv
        new._root = self._root
        new._parts = self._parts[:-1]
        new._raw_paths = [new._format_parsed_parts() or '.']
        return new

    @property
    def parents(self):
        result = []
        cur = self
        while True:
            par = cur.parent
            if par == cur:
                break
            result.append(par)
            cur = par
        return tuple(result)

    # -- Methods ------------------------------------------------------------
    def is_absolute(self):
        if self._flavour.has_drv:
            return bool(self._drv) and bool(self._root)
        return bool(self._root)

    def joinpath(self, *args):
        return type(self)(str(self), *[str(a) if isinstance(a, PurePath) else a for a in args])

    def __truediv__(self, other):
        try:
            return self.joinpath(other)
        except TypeError:
            return NotImplemented

    def __rtruediv__(self, other):
        try:
            return type(self)(other, str(self))
        except TypeError:
            return NotImplemented

    def with_name(self, new_name):
        if not self.name:
            raise ValueError("%r has an empty name" % self)
        if not new_name or self._flavour.sep in new_name or (
            self._flavour.altsep and self._flavour.altsep in new_name
        ):
            raise ValueError("Invalid name %r" % new_name)
        new = object.__new__(type(self))
        new._flavour = self._flavour
        new._drv = self._drv
        new._root = self._root
        new._parts = self._parts[:-1] + [new_name]
        new._raw_paths = [new._format_parsed_parts()]
        return new

    def with_suffix(self, suffix):
        if self._flavour.sep in suffix or (
            self._flavour.altsep and self._flavour.altsep in suffix
        ):
            raise ValueError("Invalid suffix %r" % suffix)
        if suffix and not suffix.startswith('.') or suffix == '.':
            raise ValueError("Invalid suffix %r" % suffix)
        name = self.name
        if not name:
            raise ValueError("%r has an empty name" % self)
        i = name.rfind('.')
        if 0 < i < len(name):
            new_name = name[:i] + suffix
        else:
            new_name = name + suffix
        return self.with_name(new_name)

    def with_stem(self, stem):
        return self.with_name(stem + self.suffix)

    def as_posix(self):
        return str(self).replace(self._flavour.sep, '/')

    def relative_to(self, *other):
        # Build the other path as same type
        other_path = type(self)(*other)
        n = len(other_path._parts)
        f = self._flavour
        if (f.casefold(self._drv) != f.casefold(other_path._drv)
                or f.casefold(self._root) != f.casefold(other_path._root)
                or f.casefold_parts(self._parts[:n]) != f.casefold_parts(other_path._parts)):
            raise ValueError(
                "%r is not in the subpath of %r" % (str(self), str(other_path))
            )
        new = object.__new__(type(self))
        new._flavour = self._flavour
        new._drv = ''
        new._root = ''
        new._parts = self._parts[n:]
        new._raw_paths = [new._format_parsed_parts() or '.']
        return new

    def match(self, pattern):
        if not pattern:
            raise ValueError("empty pattern")
        pat = type(self)(pattern)
        pat_parts = pat._parts
        sep = self._flavour.sep
        if pat._drv or pat._root:
            target_parts = list(self.parts)
            pat_full = list(pat.parts)
            if len(target_parts) != len(pat_full):
                return False
            check = list(zip(pat_full, target_parts))
        else:
            target = self._parts
            if len(pat_parts) > len(target):
                return False
            check = list(zip(pat_parts, target[len(target) - len(pat_parts):]))
        f = self._flavour
        for pat_p, target_p in check:
            if not _fnmatch(f.casefold(target_p), f.casefold(pat_p)):
                return False
        return True


def _fnmatch(name, pat):
    """Simple fnmatch implementation for path components."""
    regex = _translate_glob(pat)
    return _re.match(regex, name) is not None


def _translate_glob(pat):
    i = 0
    n = len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i += 1
        if c == '*':
            res += '[^/]*'
        elif c == '?':
            res += '[^/]'
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
                stuff = pat[i:j].replace('\\', '\\\\')
                i = j + 1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                res += '[' + stuff + ']'
        else:
            res += _re.escape(c)
    return '(?s:' + res + ')\\Z'


# ---------------------------------------------------------------------------
# Concrete Pure types
# ---------------------------------------------------------------------------

class PurePosixPath(PurePath):
    _flavour = _posix_flavour

    def __init__(self, *args):
        super().__init__(*args)


class PureWindowsPath(PurePath):
    _flavour = _windows_flavour

    def __init__(self, *args):
        super().__init__(*args)


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def pathlib2_parts():
    """Verify .parts splits the path correctly."""
    try:
        p = PurePosixPath('/usr/bin/python3')
        if p.parts != ('/', 'usr', 'bin', 'python3'):
            return False

        p2 = PurePosixPath('foo/bar/baz')
        if p2.parts != ('foo', 'bar', 'baz'):
            return False

        p3 = PurePosixPath('a/b/c/d')
        if p3.parts != ('a', 'b', 'c', 'd'):
            return False

        p4 = PurePosixPath()
        if p4.parts != ():
            return False

        p5 = PurePosixPath('/')
        if p5.parts != ('/',):
            return False

        # Windows path parts
        w = PureWindowsPath('c:/Program Files/PSF')
        if w.parts != ('c:\\', 'Program Files', 'PSF'):
            return False

        return True
    except Exception:
        return False


def pathlib2_stem():
    """Verify .stem returns the name without the final suffix."""
    try:
        if PurePosixPath('my/library.tar.gz').stem != 'library.tar':
            return False
        if PurePosixPath('my/library.tar').stem != 'library':
            return False
        if PurePosixPath('my/library').stem != 'library':
            return False
        if PurePosixPath('foo.txt').stem != 'foo':
            return False
        if PurePosixPath('archive.tar.bz2').stem != 'archive.tar':
            return False
        # No suffix
        if PurePosixPath('README').stem != 'README':
            return False
        # Empty path
        if PurePosixPath().stem != '':
            return False
        return True
    except Exception:
        return False


def pathlib2_joinpath():
    """Verify .joinpath combines paths correctly."""
    try:
        p = PurePosixPath('/etc')
        joined = p.joinpath('passwd')
        if str(joined) != '/etc/passwd':
            return False

        p2 = PurePosixPath('foo')
        joined2 = p2.joinpath('bar', 'baz')
        if str(joined2) != 'foo/bar/baz':
            return False

        # joinpath with absolute resets
        p3 = PurePosixPath('/etc')
        joined3 = p3.joinpath('/usr/bin')
        if str(joined3) != '/usr/bin':
            return False

        # __truediv__ should also work
        p4 = PurePosixPath('/usr')
        d = p4 / 'local' / 'bin'
        if str(d) != '/usr/local/bin':
            return False

        # Windows joining
        w = PureWindowsPath('c:')
        joined4 = w.joinpath('/Program Files')
        # c: + /Program Files -> c:\Program Files
        if str(joined4) != 'c:\\Program Files':
            return False

        return True
    except Exception:
        return False


__all__ = [
    'PurePath',
    'PurePosixPath',
    'PureWindowsPath',
    'pathlib2_parts',
    'pathlib2_stem',
    'pathlib2_joinpath',
]