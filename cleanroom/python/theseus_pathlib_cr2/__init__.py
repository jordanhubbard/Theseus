# theseus_pathlib_cr2 - Clean-room implementation of path manipulation utilities
# No imports of pathlib, os, or os.path allowed

class PurePath:
    """
    A clean-room implementation of a pure path manipulation class.
    Supports POSIX-style paths.
    """
    
    def __init__(self, *parts):
        if not parts:
            self._path = ''
        else:
            # Join all parts together
            segments = []
            for part in parts:
                if isinstance(part, PurePath):
                    part = part._path
                part = str(part)
                segments.append(part)
            
            # Join segments with '/'
            result = self._join_segments(segments)
            self._path = result
    
    def _join_segments(self, segments):
        """Join path segments, handling absolute paths and normalization."""
        if not segments:
            return ''
        
        result = segments[0]
        for seg in segments[1:]:
            if not seg:
                continue
            # If segment is absolute, it replaces the current path
            if seg.startswith('/'):
                result = seg
            else:
                if result.endswith('/'):
                    result = result + seg
                elif result == '':
                    result = seg
                else:
                    result = result + '/' + seg
        
        return self._normalize(result)
    
    def _normalize(self, path):
        """Normalize a path by resolving . and .. components."""
        if not path:
            return ''
        
        is_absolute = path.startswith('/')
        
        # Split into components
        parts = path.split('/')
        
        normalized = []
        for part in parts:
            if part == '' or part == '.':
                continue
            elif part == '..':
                if normalized and normalized[-1] != '..':
                    normalized.pop()
                elif not is_absolute:
                    normalized.append('..')
            else:
                normalized.append(part)
        
        result = '/'.join(normalized)
        if is_absolute:
            result = '/' + result
        
        return result if result else ('/' if is_absolute else '.')
    
    @property
    def parts(self):
        """Return a tuple of the path's components."""
        if not self._path or self._path == '.':
            return ()
        
        is_absolute = self._path.startswith('/')
        
        if is_absolute:
            components = self._path[1:].split('/')
            result = ['/'] + [c for c in components if c]
        else:
            result = [c for c in self._path.split('/') if c]
        
        return tuple(result)
    
    @property
    def name(self):
        """Return the final component of the path."""
        p = self.parts
        if not p:
            return ''
        last = p[-1]
        # If the only part is '/', return ''
        if last == '/':
            return ''
        return last
    
    @property
    def suffix(self):
        """Return the file extension of the final component."""
        name = self.name
        if not name:
            return ''
        # Find the last dot
        idx = name.rfind('.')
        if idx <= 0:  # No dot, or dot at start (hidden file)
            return ''
        return name[idx:]
    
    @property
    def stem(self):
        """Return the final component without its suffix."""
        name = self.name
        suffix = self.suffix
        if suffix:
            return name[:-len(suffix)]
        return name
    
    @property
    def parent(self):
        """Return the logical parent of the path."""
        p = self.parts
        if not p:
            return PurePath('.')
        
        if len(p) == 1:
            if p[0] == '/':
                return PurePath('/')
            return PurePath('.')
        
        # Reconstruct parent path from all parts except the last
        parent_parts = p[:-1]
        
        if parent_parts[0] == '/':
            if len(parent_parts) == 1:
                return PurePath('/')
            return PurePath('/' + '/'.join(parent_parts[1:]))
        else:
            return PurePath('/'.join(parent_parts))
    
    def __truediv__(self, other):
        """Implement the / operator for path joining."""
        if isinstance(other, PurePath):
            other = other._path
        return PurePath(self._path, str(other))
    
    def __rtruediv__(self, other):
        """Implement the / operator when PurePath is on the right."""
        if isinstance(other, PurePath):
            other = other._path
        return PurePath(str(other), self._path)
    
    def __str__(self):
        return self._path
    
    def __repr__(self):
        return f"PurePath('{self._path}')"
    
    def __eq__(self, other):
        if isinstance(other, PurePath):
            return self._path == other._path
        return NotImplemented
    
    def __hash__(self):
        return hash(self._path)
    
    def __fspath__(self):
        return self._path


# Required exported functions that satisfy the invariants

def pathlib_suffix():
    """Returns the suffix of '/foo/bar/baz.txt' which is '.txt'"""
    return PurePath('/foo/bar/baz.txt').suffix


def pathlib_stem():
    """Returns the stem of '/foo/bar/baz.txt' which is 'baz'"""
    return PurePath('/foo/bar/baz.txt').stem


def pathlib_join():
    """Returns the string representation of PurePath('a/b') / 'c' which is 'a/b/c'"""
    result = PurePath('a/b') / 'c'
    return str(result)