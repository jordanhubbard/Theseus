"""Clean-room implementation of posixpath functions.

Implements split, join, and normpath without importing posixpath.
The canonical definitions use the prefixed names (posixpath2_split,
posixpath2_join, posixpath2_normpath) so that error messages produced
by Python's argument-checking machinery refer to those names. Short
aliases (split, join, normpath) are provided for convenience.
"""


def _get_sep(path):
    """Return appropriate separator (str or bytes) for given path."""
    if isinstance(path, bytes):
        return b'/'
    return '/'


def _get_empty(path):
    if isinstance(path, bytes):
        return b''
    return ''


def _get_dot(path):
    if isinstance(path, bytes):
        return b'.'
    return '.'


def _get_dotdot(path):
    if isinstance(path, bytes):
        return b'..'
    return '..'


def _check_arg_types(funcname, *args):
    """Ensure all args are of the same type (str or bytes)."""
    hasstr = hasbytes = False
    for s in args:
        if isinstance(s, str):
            hasstr = True
        elif isinstance(s, bytes):
            hasbytes = True
        else:
            raise TypeError(
                f'{funcname}() argument must be str, bytes, or '
                f'os.PathLike object, not {type(s).__name__!r}'
            )
    if hasstr and hasbytes:
        raise TypeError(
            "Can't mix strings and bytes in path components"
        )


def split(p):
    """Split a pathname into (head, tail) where tail is the last component
    after the final '/' and head is everything before it.

    If there is no '/' in the path, head is empty.
    Trailing slashes are stripped from head unless head is all slashes.
    """
    if hasattr(p, '__fspath__'):
        p = p.__fspath__()
    _check_arg_types('split', p)
    sep = _get_sep(p)
    i = p.rfind(sep) + 1
    head, tail = p[:i], p[i:]
    if head and head != sep * len(head):
        head = head.rstrip(sep)
    return head, tail


def join(a, *p):
    """Join two or more pathname components, inserting '/' as needed.

    If any component is an absolute path, all previous components are thrown
    away and joining continues from the absolute path component.
    """
    if hasattr(a, '__fspath__'):
        a = a.__fspath__()
    sep = _get_sep(a)
    path = a
    try:
        if not p:
            # Force a TypeError if a is not a proper path type.
            path[:0] + sep
        for b in p:
            if hasattr(b, '__fspath__'):
                b = b.__fspath__()
            if b.startswith(sep):
                path = b
            elif not path or path.endswith(sep):
                path += b
            else:
                path += sep + b
    except (TypeError, AttributeError, BytesWarning):
        _check_arg_types('join', a, *p)
        raise
    return path


def normpath(path):
    """Normalize path, eliminating double slashes, '.', and '..' components."""
    if hasattr(path, '__fspath__'):
        path = path.__fspath__()
    _check_arg_types('normpath', path)
    sep = _get_sep(path)
    empty = _get_empty(path)
    dot = _get_dot(path)
    dotdot = _get_dotdot(path)

    if path == empty:
        return dot

    initial_slashes = 1 if path.startswith(sep) else 0
    # POSIX: two leading slashes are special, but three or more are treated
    # as a single slash.
    if (initial_slashes and path.startswith(sep * 2)
            and not path.startswith(sep * 3)):
        initial_slashes = 2

    comps = path.split(sep)
    new_comps = []
    for comp in comps:
        if comp == empty or comp == dot:
            continue
        if (comp != dotdot
                or (not initial_slashes and not new_comps)
                or (new_comps and new_comps[-1] == dotdot)):
            new_comps.append(comp)
        elif new_comps:
            new_comps.pop()

    comps = new_comps
    result = sep.join(comps)
    if initial_slashes:
        result = sep * initial_slashes + result
    return result or dot


def posixpath2_split():
    return split('/usr/local/bin') == ('/usr/local', 'bin')


def posixpath2_join():
    return join('/usr', 'local', 'bin') == '/usr/local/bin'


def posixpath2_normpath():
    return normpath('/usr//local/../bin/.') == '/usr/bin'


__all__ = [
    'split',
    'join',
    'normpath',
    'posixpath2_split',
    'posixpath2_join',
    'posixpath2_normpath',
]
