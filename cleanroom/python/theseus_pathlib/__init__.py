"""
theseus_pathlib: Clean-room path manipulation utilities.
No imports of pathlib, os.path, or posixpath allowed.
"""


def path_join(*parts):
    """
    Join path components with '/' separator.
    If a component is an absolute path (starts with '/'), it resets the result.
    Empty parts are skipped.
    
    Example: path_join('a', 'b', 'c') -> 'a/b/c'
    """
    if not parts:
        return ''
    
    result = ''
    for part in parts:
        if not part:
            continue
        if part.startswith('/'):
            # Absolute component resets the path
            result = part
        else:
            if result == '':
                result = part
            elif result.endswith('/'):
                result = result + part
            else:
                result = result + '/' + part
    
    return result


def path_basename(path):
    """
    Return the final component of a path.
    
    Example: path_basename('/foo/bar.txt') -> 'bar.txt'
    """
    if not path:
        return ''
    
    # Strip trailing slashes (unless the path is just '/')
    stripped = path.rstrip('/')
    if not stripped:
        return '/'
    
    # Find the last '/'
    idx = stripped.rfind('/')
    if idx == -1:
        return stripped
    return stripped[idx + 1:]


def path_dirname(path):
    """
    Return the directory component of a path.
    
    Example: path_dirname('/foo/bar.txt') -> '/foo'
    """
    if not path:
        return ''
    
    # Strip trailing slashes (unless the path is just '/')
    stripped = path.rstrip('/')
    if not stripped:
        return '/'
    
    # Find the last '/'
    idx = stripped.rfind('/')
    if idx == -1:
        # No slash found, directory is current directory
        return ''
    elif idx == 0:
        # The slash is the root
        return '/'
    else:
        return stripped[:idx]


def path_splitext(path):
    """
    Split the extension from a path.
    Returns a tuple (root, ext) where ext includes the leading dot.
    If there is no extension, ext is ''.
    
    Example: path_splitext('file.txt') -> ('file', '.txt')
    """
    if not path:
        return ('', '')
    
    # Get the basename to avoid treating dots in directory names
    basename = path_basename(path)
    dirname = path_dirname(path)
    
    # Find the last dot in the basename
    # A leading dot (hidden files like '.bashrc') is not treated as extension
    if basename.startswith('.'):
        # Check if there's another dot after the leading one
        rest = basename[1:]
        dot_idx = rest.rfind('.')
        if dot_idx == -1:
            # No extension
            if dirname:
                return (path, '')
            else:
                return (path, '')
        else:
            # Extension found
            ext_start = 1 + dot_idx  # position in basename
            ext = basename[ext_start:]
            root_base = basename[:ext_start]
            if dirname:
                root = path_join(dirname, root_base)
            else:
                root = root_base
            return (root, ext)
    else:
        dot_idx = basename.rfind('.')
        if dot_idx == -1:
            return (path, '')
        else:
            ext = basename[dot_idx:]
            root_base = basename[:dot_idx]
            if dirname:
                root = path_join(dirname, root_base)
            else:
                root = root_base
            return (root, ext)


def path_is_absolute(path):
    """
    Return True if the path is absolute (starts with '/').
    
    Example: path_is_absolute('/foo') -> True
             path_is_absolute('foo') -> False
    """
    if not path:
        return False
    return path.startswith('/')