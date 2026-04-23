"""
theseus_pathlib_cr4 - Clean-room implementation of pathlib utilities.
No imports of pathlib, os.path, or any third-party libraries.
"""


class PurePath:
    """
    Base class for pure path objects (no I/O).
    Subclasses define the separator and other OS-specific behavior.
    """
    _sep = '/'
    _altsep = None

    def __init__(self, *args):
        if not args:
            self._raw = ''
        else:
            # Join all parts together
            parts = []
            for arg in args:
                if isinstance(arg, PurePath):
                    parts.append(arg._raw)
                else:
                    parts.append(str(arg))
            self._raw = self._join_parts(parts)
        self._parts = self._parse_parts(self._raw)

    def _join_parts(self, parts):
        """Join multiple path parts into a single string."""
        if not parts:
            return ''
        result = parts[0]
        for part in parts[1:]:
            if not part:
                continue
            if self._is_absolute_str(part):
                result = part
            else:
                if result and not result.endswith(self._sep):
                    result = result + self._sep + part
                else:
                    result = result + part
        return result

    def _is_absolute_str(self, s):
        return s.startswith(self._sep)

    def _normalize(self, path_str):
        """Normalize separators and remove redundant separators."""
        sep = self._sep
        if self._altsep:
            path_str = path_str.replace(self._altsep, sep)
        # Collapse multiple separators (but preserve leading ones)
        if not path_str:
            return ''
        # Handle leading separator(s)
        leading = ''
        rest = path_str
        if path_str.startswith(sep):
            leading = sep
            rest = path_str.lstrip(sep)
        # Split and filter empty parts
        parts = [p for p in rest.split(sep) if p]
        return leading + sep.join(parts)

    def _parse_parts(self, path_str):
        """Parse path string into list of parts."""
        normalized = self._normalize(path_str)
        if not normalized:
            return []
        sep = self._sep
        if normalized.startswith(sep):
            # Absolute path
            rest = normalized[len(sep):]
            if rest:
                return [sep] + rest.split(sep)
            else:
                return [sep]
        else:
            return normalized.split(sep)

    @property
    def parts(self):
        return tuple(self._parts)

    @property
    def root(self):
        if self._parts and self._parts[0] == self._sep:
            return self._sep
        return ''

    @property
    def drive(self):
        return ''

    @property
    def anchor(self):
        return self.drive + self.root

    @property
    def parent(self):
        parts = self._parts
        if not parts:
            return self.__class__('.')
        if len(parts) == 1:
            if parts[0] == self._sep:
                return self.__class__(self._sep)
            return self.__class__('.')
        # Remove last part
        new_parts = parts[:-1]
        new_path = self._parts_to_str(new_parts)
        return self.__class__(new_path)

    @property
    def parents(self):
        result = []
        current = self.parent
        seen = set()
        while True:
            s = str(current)
            if s in seen:
                break
            seen.add(s)
            result.append(current)
            next_parent = current.parent
            if str(next_parent) == s:
                break
            current = next_parent
        return tuple(result)

    @property
    def name(self):
        parts = self._parts
        if not parts:
            return ''
        last = parts[-1]
        if last == self._sep:
            return ''
        return last

    @property
    def suffix(self):
        name = self.name
        if not name or name.startswith('.') and name.count('.') == 1:
            return ''
        idx = name.rfind('.')
        if idx <= 0:
            return ''
        return name[idx:]

    @property
    def suffixes(self):
        name = self.name
        if not name:
            return []
        # Strip leading dot for hidden files
        if name.startswith('.'):
            name = name[1:]
            parts = name.split('.')
            if len(parts) <= 1:
                return []
            return ['.' + p for p in parts[1:]]
        parts = name.split('.')
        if len(parts) <= 1:
            return []
        return ['.' + p for p in parts[1:]]

    @property
    def stem(self):
        name = self.name
        suffix = self.suffix
        if suffix:
            return name[:-len(suffix)]
        return name

    def _parts_to_str(self, parts):
        if not parts:
            return '.'
        sep = self._sep
        if parts[0] == sep:
            if len(parts) == 1:
                return sep
            return sep + sep.join(parts[1:])
        return sep.join(parts)

    def __str__(self):
        if not self._parts:
            return '.'
        return self._parts_to_str(self._parts)

    def __repr__(self):
        return f"{self.__class__.__name__}('{str(self)}')"

    def __eq__(self, other):
        if isinstance(other, PurePath):
            return str(self) == str(other)
        return NotImplemented

    def __hash__(self):
        return hash(str(self))

    def __truediv__(self, other):
        if isinstance(other, str):
            return self.__class__(str(self), other)
        if isinstance(other, PurePath):
            return self.__class__(str(self), str(other))
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, str):
            return self.__class__(other, str(self))
        return NotImplemented

    def with_name(self, name):
        """Return a new path with the filename changed."""
        if not name or self._sep in name:
            raise ValueError(f"Invalid name: {name!r}")
        parts = list(self._parts)
        if not parts or parts[-1] == self._sep:
            raise ValueError(f"{self!r} has an empty name")
        parts[-1] = name
        return self.__class__(self._parts_to_str(parts))

    def with_suffix(self, suffix):
        """Return a new path with the suffix changed."""
        if suffix and not suffix.startswith('.'):
            raise ValueError(f"Invalid suffix: {suffix!r}")
        if suffix and suffix == '.':
            raise ValueError(f"Invalid suffix: {suffix!r}")
        name = self.name
        if not name:
            raise ValueError(f"{self!r} has an empty name")
        stem = self.stem
        new_name = stem + suffix
        return self.with_name(new_name)

    def relative_to(self, other):
        """Return path relative to another path."""
        if isinstance(other, str):
            other = self.__class__(other)
        elif not isinstance(other, PurePath):
            other = self.__class__(str(other))

        self_str = str(self)
        other_str = str(other)

        sep = self._sep

        # Normalize both
        self_norm = self._normalize(self_str)
        other_norm = self._normalize(other_str)

        # Check if self starts with other
        if self_norm == other_norm:
            return self.__class__('.')

        # other must be a prefix of self
        if other_norm.endswith(sep):
            prefix = other_norm
        else:
            prefix = other_norm + sep

        if not self_norm.startswith(prefix):
            raise ValueError(f"{self!r} is not relative to {other!r}")

        rel = self_norm[len(prefix):]
        if not rel:
            return self.__class__('.')
        return self.__class__(rel)

    def is_absolute(self):
        return bool(self.root)

    def is_relative_to(self, other):
        try:
            self.relative_to(other)
            return True
        except ValueError:
            return False

    def joinpath(self, *args):
        result = self
        for arg in args:
            result = result / arg
        return result

    def with_stem(self, stem):
        """Return a new path with the stem changed."""
        return self.with_name(stem + self.suffix)

    def match(self, pattern):
        """Match path against a pattern."""
        # Simple glob matching
        parts = self._parts
        pat_parts = self.__class__(pattern)._parts
        # Match from the right
        if len(pat_parts) > len(parts):
            return False
        for p, q in zip(reversed(parts), reversed(pat_parts)):
            if q == '*':
                continue
            if p != q:
                return False
        return True


class PurePosixPath(PurePath):
    """Pure path for POSIX systems."""
    _sep = '/'
    _altsep = None

    @property
    def drive(self):
        return ''


class PureWindowsPath(PurePath):
    """Pure path for Windows systems."""
    _sep = '\\'
    _altsep = '/'

    def __init__(self, *args):
        super().__init__(*args)

    def _is_absolute_str(self, s):
        # Windows absolute: starts with \ or has drive letter like C:\
        if s.startswith(self._sep) or s.startswith('/'):
            return True
        # Drive letter
        if len(s) >= 2 and s[1] == ':':
            return True
        return False

    def _normalize(self, path_str):
        """Normalize separators for Windows."""
        if not path_str:
            return ''
        # Replace forward slashes with backslashes
        path_str = path_str.replace('/', self._sep)
        sep = self._sep

        # Handle drive letter
        drive = ''
        rest = path_str
        if len(path_str) >= 2 and path_str[1] == ':':
            drive = path_str[:2]
            rest = path_str[2:]

        # Handle leading separator(s)
        leading = ''
        if rest.startswith(sep):
            leading = sep
            rest = rest.lstrip(sep)

        parts = [p for p in rest.split(sep) if p]
        result = drive + leading + sep.join(parts)
        return result

    def _parse_parts(self, path_str):
        normalized = self._normalize(path_str)
        if not normalized:
            return []
        sep = self._sep

        # Handle drive letter
        drive = ''
        rest = normalized
        if len(normalized) >= 2 and normalized[1] == ':':
            drive = normalized[:2]
            rest = normalized[2:]

        if rest.startswith(sep):
            anchor = drive + sep
            rest = rest[len(sep):]
            if rest:
                return [anchor] + rest.split(sep)
            else:
                return [anchor]
        else:
            if drive:
                if rest:
                    return [drive] + rest.split(sep)
                else:
                    return [drive]
            return rest.split(sep) if rest else []

    @property
    def drive(self):
        parts = self._parts
        if not parts:
            return ''
        first = parts[0]
        if len(first) >= 2 and first[1] == ':':
            return first[:2]
        if len(first) >= 3 and first[1] == ':' and first[2] == self._sep:
            return first[:2]
        return ''

    @property
    def root(self):
        parts = self._parts
        if not parts:
            return ''
        first = parts[0]
        if first == self._sep:
            return self._sep
        if len(first) >= 3 and first[1] == ':' and first[2] == self._sep:
            return self._sep
        return ''

    def _parts_to_str(self, parts):
        if not parts:
            return '.'
        sep = self._sep
        if parts[0].endswith(sep):
            # Anchor like C:\ or \
            if len(parts) == 1:
                return parts[0]
            return parts[0] + sep.join(parts[1:])
        if parts[0] == sep:
            if len(parts) == 1:
                return sep
            return sep + sep.join(parts[1:])
        return sep.join(parts)

    def __str__(self):
        if not self._parts:
            return '.'
        return self._parts_to_str(self._parts)


# ─── Invariant functions ───────────────────────────────────────────────────────

def pathlib4_with_name():
    """
    PurePosixPath('/a/b/c.txt').with_name('d.txt') == PurePosixPath('/a/b/d.txt')
    Returns the name of the resulting path.
    """
    p = PurePosixPath('/a/b/c.txt')
    result = p.with_name('d.txt')
    return result.name


def pathlib4_with_suffix():
    """
    PurePosixPath('/a/b.txt').with_suffix('.py').suffix == '.py'
    Returns the suffix of the resulting path.
    """
    p = PurePosixPath('/a/b.txt')
    result = p.with_suffix('.py')
    return result.suffix


def pathlib4_relative_to():
    """
    PurePosixPath('/a/b/c').relative_to('/a') == PurePosixPath('b/c')
    Returns the string representation of the relative path.
    """
    p = PurePosixPath('/a/b/c')
    result = p.relative_to('/a')
    return str(result)