"""
theseus_pathlib_cr5 - Clean-room implementation of pathlib pure path utilities.
No imports of pathlib or os.path allowed.
"""

import re


def _fnmatch_pattern_to_regex(pattern):
    """Convert a glob-style pattern to a regex pattern."""
    regex = ''
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == '*':
            if i + 1 < len(pattern) and pattern[i + 1] == '*':
                # '**' matches everything including '/'
                regex += '.*'
                i += 2
            else:
                # '*' matches everything except '/'
                regex += '[^/]*'
                i += 1
        elif c == '?':
            regex += '[^/]'
            i += 1
        elif c == '[':
            # Character class
            j = i + 1
            if j < len(pattern) and pattern[j] == '!':
                j += 1
            if j < len(pattern) and pattern[j] == ']':
                j += 1
            while j < len(pattern) and pattern[j] != ']':
                j += 1
            if j >= len(pattern):
                regex += re.escape(c)
                i += 1
            else:
                char_class = pattern[i:j+1]
                # Convert [!...] to [^...]
                if char_class[1:2] == '!':
                    char_class = '[^' + char_class[2:]
                regex += char_class
                i = j + 1
        else:
            regex += re.escape(c)
            i += 1
    return regex


class PurePath:
    """Base class for pure path objects."""

    def __init__(self, *args):
        if not args:
            self._raw = '.'
        else:
            # Join all parts
            parts = []
            for arg in args:
                if isinstance(arg, PurePath):
                    parts.append(arg._raw)
                else:
                    parts.append(str(arg))
            # Join with separator
            self._raw = self._join_paths(parts)

    def _join_paths(self, parts):
        """Join path parts together."""
        result = ''
        for part in parts:
            if not part:
                continue
            if result and not result.endswith(self._sep) and not part.startswith(self._sep):
                result += self._sep + part
            elif result and result.endswith(self._sep) and part.startswith(self._sep):
                result += part[1:]
            else:
                result += part
        return result if result else '.'

    @property
    def _sep(self):
        return '/'

    @property
    def parts(self):
        """Return a tuple of path components."""
        return self._get_parts()

    def _get_parts(self):
        raw = self._raw
        sep = self._sep
        if not raw or raw == '.':
            return ('.',)

        parts = []
        if raw.startswith(sep):
            parts.append(sep)
            raw = raw.lstrip(sep)

        if raw:
            components = [c for c in raw.split(sep) if c]
            parts.extend(components)

        return tuple(parts) if parts else ('.',)

    def is_absolute(self):
        """Return True if the path is absolute."""
        return self._raw.startswith(self._sep)

    def match(self, pattern):
        """
        Return True if this path matches the given pattern.
        The pattern is matched against the path from the right.
        """
        # Get path parts
        path_parts = self.parts
        # Remove root if present
        if path_parts and path_parts[0] == self._sep:
            path_parts = path_parts[1:]

        # Get pattern parts
        pattern_parts = [p for p in pattern.split(self._sep) if p]

        if not pattern_parts:
            return False

        # Match from the right
        if len(pattern_parts) > len(path_parts):
            return False

        # Match each pattern part against corresponding path part from the right
        for i, pat in enumerate(reversed(pattern_parts)):
            path_component = path_parts[len(path_parts) - 1 - i]
            regex = '^' + _fnmatch_pattern_to_regex(pat) + '$'
            if not re.match(regex, path_component):
                return False

        return True

    @property
    def name(self):
        """The final path component."""
        parts = self.parts
        if not parts:
            return ''
        last = parts[-1]
        if last == self._sep:
            return ''
        return last

    @property
    def suffix(self):
        """The file extension of the final component."""
        name = self.name
        i = name.rfind('.')
        if i <= 0:
            return ''
        return name[i:]

    @property
    def suffixes(self):
        """A list of the path's file extensions."""
        name = self.name
        if name.endswith('.'):
            return []
        name = name.lstrip('.')
        return ['.' + suffix for suffix in name.split('.')[1:]]

    @property
    def stem(self):
        """The final path component, without its suffix."""
        name = self.name
        suffix = self.suffix
        if suffix:
            return name[:-len(suffix)]
        return name

    @property
    def parent(self):
        """The logical parent of the path."""
        parts = self.parts
        if len(parts) <= 1:
            return self.__class__(self._raw)
        if parts[0] == self._sep:
            if len(parts) == 2:
                return self.__class__(self._sep)
            return self.__class__(self._sep + self._sep.join(parts[1:-1]))
        return self.__class__(self._sep.join(parts[:-1]))

    @property
    def parents(self):
        """An immutable sequence providing access to the logical ancestors."""
        result = []
        current = self.parent
        seen = set()
        while True:
            key = current._raw
            if key in seen:
                break
            seen.add(key)
            result.append(current)
            next_parent = current.parent
            if next_parent._raw == current._raw:
                break
            current = next_parent
        return tuple(result)

    def __str__(self):
        return self._raw

    def __repr__(self):
        return f"{self.__class__.__name__}('{self._raw}')"

    def __eq__(self, other):
        if isinstance(other, PurePath):
            return self._raw == other._raw
        return NotImplemented

    def __hash__(self):
        return hash(self._raw)

    def __truediv__(self, other):
        if isinstance(other, str):
            return self.__class__(self._raw, other)
        elif isinstance(other, PurePath):
            return self.__class__(self._raw, other._raw)
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, str):
            return self.__class__(other, self._raw)
        return NotImplemented


class PurePosixPath(PurePath):
    """A pure path for POSIX systems."""

    @property
    def _sep(self):
        return '/'

    def _get_parts(self):
        raw = self._raw
        sep = '/'
        if not raw or raw == '.':
            return ('.',)

        parts = []
        if raw.startswith(sep):
            parts.append(sep)
            raw = raw.lstrip(sep)

        if raw:
            components = [c for c in raw.split(sep) if c]
            parts.extend(components)

        return tuple(parts) if parts else ('.',)


class PureWindowsPath(PurePath):
    """A pure path for Windows systems."""

    @property
    def _sep(self):
        return '\\'

    def is_absolute(self):
        """Return True if the path is absolute (Windows style)."""
        raw = self._raw
        # Windows absolute: starts with drive letter + colon + backslash, or UNC path
        if len(raw) >= 3 and raw[1] == ':' and raw[2] in ('\\', '/'):
            return True
        if raw.startswith('\\\\') or raw.startswith('//'):
            return True
        return False

    def _get_parts(self):
        raw = self._raw
        sep = '\\'
        if not raw or raw == '.':
            return ('.',)

        # Normalize forward slashes to backslashes
        raw = raw.replace('/', '\\')

        parts = []
        # Check for drive letter
        if len(raw) >= 2 and raw[1] == ':':
            drive = raw[:2]
            parts.append(drive + sep if len(raw) > 2 and raw[2] == sep else drive)
            raw = raw[2:].lstrip(sep)
        elif raw.startswith(sep):
            parts.append(sep)
            raw = raw.lstrip(sep)

        if raw:
            components = [c for c in raw.split(sep) if c]
            parts.extend(components)

        return tuple(parts) if parts else ('.',)


# Zero-argument invariant functions

def pathlib5_match():
    """
    Demonstrates PurePosixPath('/a/b/c.py').match('*.py') == True
    Returns True (hardcoded result per spec).
    """
    path = PurePosixPath('/a/b/c.py')
    return path.match('*.py')


def pathlib5_is_absolute():
    """
    Demonstrates PurePosixPath('/a/b').is_absolute() == True
    Returns True (hardcoded result per spec).
    """
    path = PurePosixPath('/a/b')
    return path.is_absolute()


def pathlib5_parts():
    """
    Demonstrates PurePosixPath('/a/b/c').parts == ('/', 'a', 'b', 'c')
    Returns ['/', 'a', 'b', 'c'] (as list per invariant spec).
    """
    path = PurePosixPath('/a/b/c')
    return list(path.parts)