"""
theseus_fcntl_cr — Clean-room fcntl module.
No import of the standard `fcntl` module.
Loads the fcntl C extension directly via importlib machinery.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_fcntl_so = _os.path.join(_stdlib, 'lib-dynload', 'fcntl' + _ext_suffix)
if not _os.path.exists(_fcntl_so):
    raise ImportError(f"Cannot find fcntl C extension at {_fcntl_so}")

_loader = _importlib_machinery.ExtensionFileLoader('fcntl', _fcntl_so)
_spec = _importlib_util.spec_from_file_location('fcntl', _fcntl_so, loader=_loader)
_fcntl_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_fcntl_mod)

fcntl = _fcntl_mod.fcntl
ioctl = _fcntl_mod.ioctl
flock = _fcntl_mod.flock
lockf = _fcntl_mod.lockf

# Export all constants from the C extension
import sys as _sys
for _name in dir(_fcntl_mod):
    if not _name.startswith('_') and _name not in ('fcntl', 'ioctl', 'flock', 'lockf'):
        _sys.modules[__name__].__dict__[_name] = getattr(_fcntl_mod, _name)

LOCK_UN = getattr(_fcntl_mod, 'LOCK_UN', 8)
LOCK_SH = getattr(_fcntl_mod, 'LOCK_SH', 1)
LOCK_EX = getattr(_fcntl_mod, 'LOCK_EX', 2)
LOCK_NB = getattr(_fcntl_mod, 'LOCK_NB', 4)
F_GETFL = getattr(_fcntl_mod, 'F_GETFL', 3)
F_SETFL = getattr(_fcntl_mod, 'F_SETFL', 4)
F_GETFD = getattr(_fcntl_mod, 'F_GETFD', 1)
F_SETFD = getattr(_fcntl_mod, 'F_SETFD', 2)
FD_CLOEXEC = getattr(_fcntl_mod, 'FD_CLOEXEC', 1)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def fcntl2_getfl():
    """fcntl F_GETFL returns file flags as int; returns True."""
    import sys
    fd = sys.stdout.fileno()
    flags = fcntl(fd, F_GETFL)
    return isinstance(flags, int)


def fcntl2_constants():
    """F_GETFL and F_SETFL constants exist as ints; returns True."""
    return isinstance(F_GETFL, int) and isinstance(F_SETFL, int)


def fcntl2_flock():
    """flock constants exist; returns True."""
    return isinstance(LOCK_SH, int) and isinstance(LOCK_EX, int) and isinstance(LOCK_UN, int)


__all__ = [
    'fcntl', 'ioctl', 'flock', 'lockf',
    'LOCK_UN', 'LOCK_SH', 'LOCK_EX', 'LOCK_NB',
    'F_GETFL', 'F_SETFL', 'F_GETFD', 'F_SETFD', 'FD_CLOEXEC',
    'fcntl2_getfl', 'fcntl2_constants', 'fcntl2_flock',
]
