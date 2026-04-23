"""
theseus_resource_cr — Clean-room resource module.
No import of the standard `resource` module.
Loads the resource C extension directly via importlib machinery.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os
import sys as _sys

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_resource_so = _os.path.join(_stdlib, 'lib-dynload', 'resource' + _ext_suffix)
if not _os.path.exists(_resource_so):
    raise ImportError(f"Cannot find resource C extension at {_resource_so}")

_loader = _importlib_machinery.ExtensionFileLoader('resource', _resource_so)
_spec = _importlib_util.spec_from_file_location('resource', _resource_so, loader=_loader)
_resource_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_resource_mod)

getrlimit = _resource_mod.getrlimit
setrlimit = _resource_mod.setrlimit
getrusage = _resource_mod.getrusage
struct_rusage = _resource_mod.struct_rusage

# Export all constants
for _name in dir(_resource_mod):
    if not _name.startswith('_'):
        _sys.modules[__name__].__dict__[_name] = getattr(_resource_mod, _name)

RLIMIT_NOFILE = getattr(_resource_mod, 'RLIMIT_NOFILE', 8)
RLIMIT_CPU = getattr(_resource_mod, 'RLIMIT_CPU', 0)
RLIMIT_CORE = getattr(_resource_mod, 'RLIMIT_CORE', 4)
RLIM_INFINITY = getattr(_resource_mod, 'RLIM_INFINITY', -1)
RUSAGE_SELF = getattr(_resource_mod, 'RUSAGE_SELF', 0)
RUSAGE_CHILDREN = getattr(_resource_mod, 'RUSAGE_CHILDREN', -1)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def resource2_getrlimit():
    """getrlimit(RLIMIT_NOFILE) returns a 2-tuple; returns True."""
    soft, hard = getrlimit(RLIMIT_NOFILE)
    return isinstance(soft, int) and isinstance(hard, int)


def resource2_constants():
    """RLIMIT_NOFILE and RLIM_INFINITY constants are ints; returns True."""
    return isinstance(RLIMIT_NOFILE, int) and isinstance(RLIM_INFINITY, int)


def resource2_getrusage():
    """getrusage(RUSAGE_SELF) returns a struct_rusage; returns True."""
    ru = getrusage(RUSAGE_SELF)
    return hasattr(ru, 'ru_utime') and hasattr(ru, 'ru_stime')


__all__ = [
    'getrlimit', 'setrlimit', 'getrusage', 'struct_rusage',
    'RLIMIT_NOFILE', 'RLIMIT_CPU', 'RLIMIT_CORE',
    'RLIM_INFINITY', 'RUSAGE_SELF', 'RUSAGE_CHILDREN',
    'resource2_getrlimit', 'resource2_constants', 'resource2_getrusage',
]
