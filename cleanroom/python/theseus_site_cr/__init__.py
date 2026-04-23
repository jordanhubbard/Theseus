"""
theseus_site_cr — Clean-room site module.
No import of the standard `site` module.
"""

import sys as _sys
import os as _os


# Site configuration
ENABLE_USER_SITE = True

def _get_prefixes():
    prefixes = [_sys.prefix, _sys.exec_prefix]
    return list(dict.fromkeys(prefixes))  # deduplicate

PREFIXES = _get_prefixes()


def _get_user_base():
    home = _os.path.expanduser('~')
    if _sys.platform == 'darwin':
        return _os.path.join(home, 'Library', 'Python',
                             f'{_sys.version_info.major}.{_sys.version_info.minor}')
    elif _sys.platform == 'win32':
        appdata = _os.environ.get('APPDATA', home)
        return _os.path.join(appdata, 'Python',
                             f'Python{_sys.version_info.major}{_sys.version_info.minor}')
    else:
        return _os.path.join(home, '.local')


def _get_user_site():
    base = _get_user_base()
    if _sys.platform == 'darwin':
        return _os.path.join(base, 'lib', 'python', 'site-packages')
    elif _sys.platform == 'win32':
        return _os.path.join(base, 'site-packages')
    else:
        return _os.path.join(base, 'lib',
                             f'python{_sys.version_info.major}.{_sys.version_info.minor}',
                             'site-packages')


USER_BASE = _get_user_base()
USER_SITE = _get_user_site()


def getusersitepackages():
    """Return the path of the user site-packages directory."""
    return USER_SITE


def getuserhome():
    """Return the path of the user's home directory."""
    return _os.path.expanduser('~')


def getsitepackages(prefixes=None):
    """Return a list of site-packages directories."""
    if prefixes is None:
        prefixes = PREFIXES
    sitepackages = []
    for prefix in prefixes:
        if _sys.platform == 'darwin':
            libdir = _os.path.join(prefix, 'lib', 'python',
                                   f'{_sys.version_info.major}.{_sys.version_info.minor}')
        else:
            libdir = _os.path.join(prefix, 'lib',
                                   f'python{_sys.version_info.major}.{_sys.version_info.minor}')
        sitepackages.append(_os.path.join(libdir, 'site-packages'))
    return sitepackages


def addsitedir(sitedir, known_paths=None):
    """Add 'sitedir' argument to sys.path if missing and handle .pth files."""
    if sitedir not in _sys.path:
        _sys.path.append(sitedir)
    # Process .pth files
    try:
        names = _os.listdir(sitedir)
    except OSError:
        return known_paths
    for name in sorted(names):
        if name.endswith('.pth'):
            addpackage(sitedir, name, known_paths)
    return known_paths


def addpackage(sitedir, name, known_paths):
    """Process a .pth file, adding its directories to sys.path."""
    try:
        f = open(_os.path.join(sitedir, name))
    except OSError:
        return known_paths
    try:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            if line.startswith('import '):
                continue
            path = _os.path.join(sitedir, line)
            if _os.path.isdir(path) and path not in _sys.path:
                _sys.path.append(path)
    finally:
        f.close()
    return known_paths


def abs_paths():
    """Make all paths in sys.path absolute."""
    for i, p in enumerate(_sys.path):
        if not _os.path.isabs(p):
            _sys.path[i] = _os.path.abspath(p)


def addsitepackages(known_paths, prefixes=None):
    """Add site-packages directories to sys.path."""
    for sitedir in getsitepackages(prefixes):
        addsitedir(sitedir, known_paths)
    return known_paths


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def site2_prefixes():
    """PREFIXES list contains sys.prefix; returns True."""
    return (isinstance(PREFIXES, list) and
            len(PREFIXES) > 0 and
            _sys.prefix in PREFIXES)


def site2_user_site():
    """USER_SITE path contains site-packages; returns True."""
    return (isinstance(USER_SITE, str) and
            'site-packages' in USER_SITE)


def site2_addsitedir():
    """addsitedir() function exists and is callable; returns True."""
    return callable(addsitedir)


__all__ = [
    'ENABLE_USER_SITE', 'PREFIXES', 'USER_BASE', 'USER_SITE',
    'getusersitepackages', 'getuserhome', 'getsitepackages',
    'addsitedir', 'addpackage', 'abs_paths', 'addsitepackages',
    'site2_prefixes', 'site2_user_site', 'site2_addsitedir',
]
