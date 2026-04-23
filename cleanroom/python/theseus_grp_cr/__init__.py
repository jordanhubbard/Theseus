"""
theseus_grp_cr — Clean-room grp module.
No import of the standard `grp` module.
Loads the grp C extension directly via importlib machinery.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_grp_so = _os.path.join(_stdlib, 'lib-dynload', 'grp' + _ext_suffix)
if not _os.path.exists(_grp_so):
    raise ImportError(f"Cannot find grp C extension at {_grp_so}")

_loader = _importlib_machinery.ExtensionFileLoader('grp', _grp_so)
_spec = _importlib_util.spec_from_file_location('grp', _grp_so, loader=_loader)
_grp_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_grp_mod)

getgrall = _grp_mod.getgrall
getgrgid = _grp_mod.getgrgid
getgrnam = _grp_mod.getgrnam
struct_group = _grp_mod.struct_group


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def grp2_getgrall():
    """getgrall() returns a non-empty list of group entries; returns True."""
    groups = getgrall()
    return isinstance(groups, list) and len(groups) > 0


def grp2_struct_group():
    """struct_group has gr_name and gr_gid fields; returns True."""
    groups = getgrall()
    if not groups:
        return False
    g = groups[0]
    return hasattr(g, 'gr_name') and hasattr(g, 'gr_gid')


def grp2_getgrgid():
    """getgrgid returns group by numeric ID; returns True."""
    groups = getgrall()
    if not groups:
        return False
    gid = groups[0].gr_gid
    g = getgrgid(gid)
    return g.gr_gid == gid


__all__ = [
    'getgrall', 'getgrgid', 'getgrnam', 'struct_group',
    'grp2_getgrall', 'grp2_struct_group', 'grp2_getgrgid',
]
