"""
theseus_pathlib_cr3 - Clean-room implementation of pure POSIX path utilities.
No imports of pathlib, os, or os.path allowed.
"""


class PurePosixPath:
    """
    A pure (no I/O) POSIX path object implemented from scratch.
    """

    def __init__(self, *args):
        # Join all parts together
        if not args:
            self._raw = ''
        else:
            parts = []
            for arg in args:
                if isinstance(arg, PurePosixPath):
                    parts.append(arg._raw)
                else:
                    parts.append(str(arg))
            # Join with '/' and normalize
            self._raw = self._join_and_normalize(parts)

    def _join_and_normalize(self, parts):
        """Join path parts and normalize the result."""
        if not parts:
            return ''
        
        # Determine if result should be absolute
        result = ''
        for part in parts:
            if not part:
                continue
            if part.startswith('/'):
                # Absolute path resets everything
                result = part
            else:
                if result:
                    result = result.rstrip('/') + '/' + part
                else:
                    result = part
        
        return self._normalize(result)

    def _normalize(self, path):
        """Normalize a path string (collapse multiple slashes, handle . and ..)."""
        if not path:
            return '.'
        
        absolute = path.startswith('/')
        
        # Split into components
        parts = path.split('/')
        
        normalized = []
        for part in parts:
            if part == '' or part == '.':
                continue
            elif part == '..':
                if normalized and normalized[-1] != '..':
                    normalized.pop()
                elif not absolute:
                    normalized.append('..')
            else:
                normalized.append(part)
        
        result = '/'.join(normalized)
        if absolute:
            result = '/' + result
        
        if not result:
            result = '.' if not absolute else '/'
        
        return result

    @property
    def parts(self):
        """Return a tuple of the path's components."""
        if self._raw == '.':
            return ('.',)
        
        absolute = self._raw.startswith('/')
        
        if absolute:
            rest = self._raw[1:]
            if rest:
                components = rest.split('/')
                return ('/',) + tuple(c for c in components if c)
            else:
                return ('/',)
        else:
            components = self._raw.split('/')
            return tuple(c for c in components if c)

    @property
    def name(self):
        """The final path component."""
        raw = self._raw
        if raw == '/':
            return ''
        # Get last component
        idx = raw.rfind('/')
        if idx == -1:
            return raw
        return raw[idx + 1:]

    @property
    def suffix(self):
        """The file extension of the final component."""
        name = self.name
        if not name or name.startswith('.') and name.count('.') == 1:
            return ''
        idx = name.rfind('.')
        if idx <= 0:
            return ''
        return name[idx:]

    @property
    def suffixes(self):
        """A list of the path's file extensions."""
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
        """The final path component without its suffix."""
        name = self.name
        suffix = self.suffix
        if suffix:
            return name[:-len(suffix)]
        return name

    @property
    def parent(self):
        """The logical parent of the path."""
        raw = self._raw
        if raw == '/':
            return PurePosixPath('/')
        if raw == '.':
            return PurePosixPath('.')
        
        idx = raw.rfind('/')
        if idx == -1:
            return PurePosixPath('.')
        elif idx == 0:
            return PurePosixPath('/')
        else:
            return PurePosixPath(raw[:idx])

    @property
    def parents(self):
        """An immutable sequence of the path's logical ancestors."""
        result = []
        current = self.parent
        while True:
            result.append(current)
            next_parent = current.parent
            if next_parent == current:
                break
            current = next_parent
        return tuple(result)

    def __str__(self):
        return self._raw

    def __repr__(self):
        return f"PurePosixPath('{self._raw}')"

    def __eq__(self, other):
        if isinstance(other, PurePosixPath):
            return self._raw == other._raw
        if isinstance(other, str):
            return self._raw == other
        return NotImplemented

    def __hash__(self):
        return hash(self._raw)

    def __truediv__(self, other):
        """Support path / 'component' syntax."""
        if isinstance(other, PurePosixPath):
            return PurePosixPath(self._raw, other._raw)
        return PurePosixPath(self._raw, str(other))

    def __rtruediv__(self, other):
        return PurePosixPath(str(other), self._raw)

    def with_name(self, name):
        """Return a new path with the file name changed."""
        if not self.name:
            raise ValueError(f"{self!r} has an empty name")
        parent = self.parent
        if parent._raw == '.':
            return PurePosixPath(name)
        return PurePosixPath(parent._raw + '/' + name)

    def with_suffix(self, suffix):
        """Return a new path with the file suffix changed."""
        if suffix and not suffix.startswith('.'):
            raise ValueError(f"Invalid suffix {suffix!r}")
        name = self.stem + suffix
        return self.with_name(name)

    def is_absolute(self):
        """Return True if the path is absolute."""
        return self._raw.startswith('/')

    def joinpath(self, *args):
        """Combine this path with one or several arguments."""
        result = self
        for arg in args:
            result = result / arg
        return result


def pathlib3_stem():
    """Return the stem of 'dir/file.txt'."""
    return PurePosixPath('dir/file.txt').stem


def pathlib3_suffix():
    """Return the suffix of 'dir/file.txt'."""
    return PurePosixPath('dir/file.txt').suffix


def pathlib3_parent():
    """Return the string representation of the parent of '/a/b/c'."""
    return str(PurePosixPath('/a/b/c').parent)


__all__ = [
    'PurePosixPath',
    'pathlib3_stem',
    'pathlib3_suffix',
    'pathlib3_parent',
]