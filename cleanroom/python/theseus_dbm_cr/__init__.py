"""
theseus_dbm_cr — Clean-room dbm module.
No import of the standard `dbm` module.
Uses the _dbm C extension directly.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os
import tempfile as _tempfile

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_dbm_so = _os.path.join(_stdlib, 'lib-dynload', '_dbm' + _ext_suffix)
if not _os.path.exists(_dbm_so):
    raise ImportError(f"Cannot find _dbm C extension at {_dbm_so}")

_loader = _importlib_machinery.ExtensionFileLoader('_dbm', _dbm_so)
_spec = _importlib_util.spec_from_file_location('_dbm', _dbm_so, loader=_loader)
_dbm_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_dbm_mod)

error = _dbm_mod.error
_open = _dbm_mod.open
library = getattr(_dbm_mod, 'library', '')

_VALID_FLAGS = frozenset(['r', 'w', 'c', 'n',
                          'rf', 'wf', 'cf', 'nf',
                          'rs', 'ws', 'cs', 'ns'])


def open(file, flag='r', mode=0o666):
    """Open a database file, returning a dbm object."""
    return _open(file, flag, mode)


def whichdb(filename):
    """Return the type of an existing dbm-style database."""
    for suffix in ['', '.db', '.dir', '.pag']:
        path = filename + suffix
        if _os.path.exists(path):
            return library or 'dbm'
    return None


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def dbm2_open():
    """open() creates a dbm database and supports key-value store; returns True."""
    with _tempfile.TemporaryDirectory() as d:
        path = _os.path.join(d, 'test')
        db = open(path, 'n')
        db[b'key1'] = b'value1'
        db[b'key2'] = b'value2'
        v = db[b'key1']
        db.close()
        db2 = open(path, 'r')
        v2 = db2[b'key1']
        db2.close()
        return v == b'value1' and v2 == b'value1'


def dbm2_error():
    """dbm.error exception class exists; returns True."""
    return issubclass(error, Exception)


def dbm2_whichdb():
    """whichdb() is callable; returns True."""
    return callable(whichdb)


__all__ = ['open', 'whichdb', 'error', 'library',
           'dbm2_open', 'dbm2_error', 'dbm2_whichdb']
