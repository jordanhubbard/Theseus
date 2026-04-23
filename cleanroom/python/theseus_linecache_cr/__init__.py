"""
theseus_linecache_cr — Clean-room linecache module.
No import of the standard `linecache` module.
Avoids tokenize (which imports linecache).
"""

import os as _os
import sys as _sys

cache = {}


def getlines(filename, module_globals=None):
    """Get the lines for a Python source file, returning them as a list."""
    if filename in cache:
        entry = cache[filename]
        if isinstance(entry, tuple) and len(entry) == 4:
            return entry[2]
        return []

    return updatecache(filename, module_globals)


def getline(filename, lineno, module_globals=None):
    """Get a single line from a file, as a string."""
    lines = getlines(filename, module_globals)
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1]
    return ''


def clearcache():
    """Clear the cache entirely."""
    global cache
    cache.clear()


def updatecache(filename, module_globals=None):
    """Update a cache entry and return its list of lines."""
    if filename in cache:
        del cache[filename]

    if not filename or (filename.startswith('<') and filename.endswith('>')):
        lines = _get_source_from_globals(filename, module_globals)
        if lines is not None:
            cache[filename] = (0, None, lines, filename)
            return lines
        return []

    try:
        stat = _os.stat(filename)
    except OSError:
        return []

    # Detect encoding from BOM or coding comment, then read
    lines = _read_source_file(filename)
    if lines is None:
        return []

    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'

    cache[filename] = (stat.st_size, stat.st_mtime, lines, filename)
    return lines


def _detect_encoding(filename):
    """Detect source file encoding from BOM or coding comment."""
    try:
        with open(filename, 'rb') as f:
            bom = f.read(3)
            if bom.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig'
            f.seek(0)
            first_line = f.readline()
            second_line = f.readline()
        import re as _re
        coding_re = _re.compile(rb'coding[:=]\s*([-\w.]+)')
        for line in (first_line, second_line):
            m = coding_re.search(line)
            if m:
                return m.group(1).decode('ascii')
    except OSError:
        pass
    return 'utf-8'


def _read_source_file(filename):
    """Read a source file, detecting its encoding."""
    encoding = _detect_encoding(filename)
    try:
        with open(filename, encoding=encoding, errors='replace') as f:
            return f.readlines()
    except (OSError, LookupError):
        try:
            with open(filename, encoding='utf-8', errors='replace') as f:
                return f.readlines()
        except OSError:
            return None


def _get_source_from_globals(filename, module_globals):
    """Try to get source from module globals (for <string> etc.)."""
    if not module_globals:
        return None
    loader = module_globals.get('__loader__')
    if loader is None:
        return None
    try:
        get_source = getattr(loader, 'get_source', None)
        if get_source is None:
            return None
        name = module_globals.get('__name__')
        source = get_source(name)
        if source is None:
            return None
        return [l + '\n' for l in source.splitlines()]
    except Exception:
        return None


def checkcache(filename=None):
    """Discard cache entries that are out of date."""
    if filename is None:
        filenames = list(cache.keys())
    else:
        filenames = [filename]

    for name in filenames:
        entry = cache.get(name)
        if not isinstance(entry, tuple) or len(entry) != 4:
            continue
        size, mtime, lines, fullname = entry
        try:
            stat = _os.stat(fullname)
        except OSError:
            del cache[name]
            continue
        if size != stat.st_size or mtime != stat.st_mtime:
            del cache[name]


def lazycache(filename, module_globals):
    """Seed the cache for filename with module_globals."""
    if filename in cache:
        return True
    if not module_globals:
        return False
    spec = module_globals.get('__spec__')
    if spec is None:
        return False
    loader = getattr(spec, 'loader', None)
    if loader is None:
        return False
    cache[filename] = module_globals
    return True


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def linecache2_getline():
    """getline() returns a line from a file; returns True."""
    path = _os.__file__
    if path.endswith('.pyc'):
        path = path[:-1]
    line = getline(path, 1)
    return isinstance(line, str) and len(line) > 0


def linecache2_getlines():
    """getlines() returns all lines from a file; returns True."""
    path = _os.__file__
    if path.endswith('.pyc'):
        path = path[:-1]
    lines = getlines(path)
    return isinstance(lines, list) and len(lines) > 0


def linecache2_clearcache():
    """clearcache() clears the cache; returns True."""
    path = _os.__file__
    if path.endswith('.pyc'):
        path = path[:-1]
    getlines(path)
    clearcache()
    return len(cache) == 0


__all__ = [
    'cache', 'getline', 'getlines', 'clearcache', 'updatecache',
    'checkcache', 'lazycache',
    'linecache2_getline', 'linecache2_getlines', 'linecache2_clearcache',
]
