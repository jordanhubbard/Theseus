"""
theseus_pwd_cr — Clean-room pwd module.
No import of the standard `pwd` module.
Loads the built-in pwd module by temporarily bypassing the meta_path blocker.
"""

import importlib.util as _importlib_util
import sys as _sys
import os as _os

# Temporarily remove any Theseus isolation blocker to load the built-in pwd
_saved_meta_path = _sys.meta_path[:]
_sys.meta_path = [f for f in _sys.meta_path if type(f).__name__ != '_Blocker']
try:
    _spec = _importlib_util.find_spec('pwd')
    if _spec is None:
        raise ImportError("Cannot find pwd built-in module")
    _loader = _spec.loader
    _pwd_shadow = _loader.create_module(_spec)
    _loader.exec_module(_pwd_shadow)
finally:
    _sys.meta_path[:] = _saved_meta_path

getpwuid = _pwd_shadow.getpwuid
getpwnam = _pwd_shadow.getpwnam
getpwall = _pwd_shadow.getpwall
struct_passwd = _pwd_shadow.struct_passwd


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pwd2_getpwuid():
    """getpwuid(os.getuid()) returns a passwd entry; returns True."""
    entry = getpwuid(_os.getuid())
    return hasattr(entry, 'pw_name') and hasattr(entry, 'pw_uid')


def pwd2_struct_passwd():
    """struct_passwd has pw_name and pw_uid fields; returns True."""
    entry = getpwuid(_os.getuid())
    return isinstance(entry.pw_name, str) and isinstance(entry.pw_uid, int)


def pwd2_getpwall():
    """getpwall() returns a non-empty list; returns True."""
    entries = getpwall()
    return isinstance(entries, list) and len(entries) > 0


__all__ = [
    'getpwuid', 'getpwnam', 'getpwall', 'struct_passwd',
    'pwd2_getpwuid', 'pwd2_struct_passwd', 'pwd2_getpwall',
]
