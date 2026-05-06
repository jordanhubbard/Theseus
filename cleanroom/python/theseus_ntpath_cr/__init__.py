"""Clean-room implementation of ntpath split/join/normpath."""


def _get_consts(p):
    if isinstance(p, bytes):
        return b'\\', b'/', b':', b'.', b'..', b''
    return '\\', '/', ':', '.', '..', ''


def _splitdrive(p):
    """Split a pathname into drive/UNC sharepoint and relative path."""
    if isinstance(p, bytes):
        sep = b'\\'
        altsep = b'/'
        colon = b':'
    else:
        sep = '\\'
        altsep = '/'
        colon = ':'
    if len(p) >= 2:
        normp = p.replace(altsep, sep)
        if normp[0:2] == sep + sep and normp[2:3] != sep:
            # UNC path: \\server\share\...
            index = normp.find(sep, 2)
            if index == -1:
                return p[:0], p
            index2 = normp.find(sep, index + 1)
            # A UNC path can't have two slashes in a row
            if index2 == index + 1:
                return p[:0], p
            if index2 == -1:
                index2 = len(p)
            return p[:index2], p[index2:]
        if normp[1:2] == colon:
            return p[:2], p[2:]
    return p[:0], p


def ntpath2_split(p=''):
    """Split a pathname into (head, tail). tail has no slashes."""
    sep, altsep, colon, curdir, pardir, empty = _get_consts(p)
    d, rest = _splitdrive(p)

    # Walk back to the position just past the last separator
    i = len(rest)
    while i:
        c = rest[i - 1:i]
        if c == sep or c == altsep:
            break
        i -= 1

    head, tail = rest[:i], rest[i:]
    # Strip trailing separators from head unless head is all separators
    if isinstance(p, bytes):
        seps = b'\\/'
    else:
        seps = '\\/'
    head_stripped = head.rstrip(seps)
    if not head_stripped:
        head_stripped = head
    return d + head_stripped, tail


def ntpath2_join(path='', *paths):
    """Join two or more pathname components, inserting '\\' as needed."""
    sep, altsep, colon, curdir, pardir, empty = _get_consts(path)
    if isinstance(path, bytes):
        seps = b'\\/'
    else:
        seps = '\\/'

    result_drive, result_path = _splitdrive(path)
    for p in paths:
        # Ensure the type matches (bytes vs str). If mismatched, let it raise on concat.
        p_drive, p_path = _splitdrive(p)
        if p_path and p_path[0:1] in seps:
            # Second path is absolute
            if p_drive or not result_drive:
                result_drive = p_drive
            result_path = p_path
            continue
        elif p_drive and p_drive != result_drive:
            if p_drive.lower() != result_drive.lower():
                # Different drives -> ignore the first path entirely
                result_drive = p_drive
                result_path = p_path
                continue
            # Same drive in different case
            result_drive = p_drive
        # Second path is relative to the first
        if result_path and result_path[-1:] not in seps:
            result_path = result_path + sep
        result_path = result_path + p_path

    # Add separator between drive and path if needed
    if (result_path and result_path[0:1] not in seps and
            result_drive and result_drive[-1:] != colon):
        return result_drive + sep + result_path
    return result_drive + result_path


def ntpath2_normpath(path=''):
    """Normalize path, eliminating double slashes, etc."""
    if isinstance(path, bytes):
        sep = b'\\'
        altsep = b'/'
        curdir = b'.'
        pardir = b'..'
        special_prefixes = (b'\\\\.\\', b'\\\\?\\')
    else:
        sep = '\\'
        altsep = '/'
        curdir = '.'
        pardir = '..'
        special_prefixes = ('\\\\.\\', '\\\\?\\')

    if path.startswith(special_prefixes):
        # \\.\ -> device names, \\?\ -> literal paths; do not normalize
        return path

    path = path.replace(altsep, sep)
    prefix, path = _splitdrive(path)

    # Collapse leading backslashes into the prefix
    if path.startswith(sep):
        prefix = prefix + sep
        path = path.lstrip(sep)

    comps = path.split(sep)
    i = 0
    while i < len(comps):
        if not comps[i] or comps[i] == curdir:
            del comps[i]
        elif comps[i] == pardir:
            if i > 0 and comps[i - 1] != pardir:
                del comps[i - 1:i + 1]
                i -= 1
            elif i == 0 and prefix.endswith(sep):
                # Leading '..' against an absolute prefix is absorbed
                del comps[i]
            else:
                i += 1
        else:
            i += 1

    # If the path is now empty, substitute '.'
    if not prefix and not comps:
        comps.append(curdir)
    return prefix + sep.join(comps)


split = ntpath2_split
join = ntpath2_join
normpath = ntpath2_normpath


def ntpath2_split():
    return split(r'C:\Temp\file.txt') == (r'C:\Temp', 'file.txt')


def ntpath2_join():
    return join(r'C:\Temp', 'folder', 'file.txt') == r'C:\Temp\folder\file.txt'


def ntpath2_normpath():
    return normpath(r'C:\Temp\..\Windows\.') == r'C:\Windows'


__all__ = [
    'split',
    'join',
    'normpath',
    'ntpath2_split',
    'ntpath2_join',
    'ntpath2_normpath',
]
