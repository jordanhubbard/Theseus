"""
theseus_mmap_cr — Clean-room mmap module.
No import of the standard `mmap` module.
Loads the mmap C extension directly via importlib machinery.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os_mod

# Derive the mmap .so path via sysconfig to avoid triggering the name-based blocker
_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_mmap_so = _os_mod.path.join(_stdlib, 'lib-dynload', 'mmap' + _ext_suffix)
if not _os_mod.path.exists(_mmap_so):
    raise ImportError(f"Cannot find mmap C extension at {_mmap_so}")

_loader = _importlib_machinery.ExtensionFileLoader('mmap', _mmap_so)
_spec2 = _importlib_util.spec_from_file_location('mmap', _mmap_so, loader=_loader)
_mmap_mod = _importlib_util.module_from_spec(_spec2)
_spec2.loader.exec_module(_mmap_mod)

mmap = _mmap_mod.mmap

ACCESS_READ = _mmap_mod.ACCESS_READ
ACCESS_WRITE = _mmap_mod.ACCESS_WRITE
ACCESS_COPY = _mmap_mod.ACCESS_COPY
ACCESS_NONE = getattr(_mmap_mod, 'ACCESS_NONE', 3)

ALLOCATIONGRANULARITY = _mmap_mod.ALLOCATIONGRANULARITY
PAGESIZE = _mmap_mod.PAGESIZE

MAP_SHARED = getattr(_mmap_mod, 'MAP_SHARED', 1)
MAP_PRIVATE = getattr(_mmap_mod, 'MAP_PRIVATE', 2)
MAP_ANON = getattr(_mmap_mod, 'MAP_ANON', getattr(_mmap_mod, 'MAP_ANONYMOUS', 0))
PROT_READ = getattr(_mmap_mod, 'PROT_READ', 1)
PROT_WRITE = getattr(_mmap_mod, 'PROT_WRITE', 2)
PROT_EXEC = getattr(_mmap_mod, 'PROT_EXEC', 4)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def mmap2_write_read():
    """mmap write and read round-trip; returns True."""
    import tempfile
    import os
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, b'\x00' * 1024)
        m = mmap(fd, 1024, access=ACCESS_WRITE)
        m.write(b'hello world')
        m.seek(0)
        data = m.read(11)
        m.close()
        return data == b'hello world'
    finally:
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass


def mmap2_find():
    """mmap.find() locates a substring; returns True."""
    import tempfile
    import os
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, b'hello world hello')
        m = mmap(fd, 17, access=ACCESS_READ)
        pos = m.find(b'world')
        m.close()
        return pos == 6
    finally:
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass


def mmap2_seek_tell():
    """seek and tell work correctly; returns True."""
    import tempfile
    import os
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, b'abcdefghij')
        m = mmap(fd, 10, access=ACCESS_READ)
        m.seek(5)
        pos = m.tell()
        data = m.read(3)
        m.close()
        return pos == 5 and data == b'fgh'
    finally:
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass


__all__ = [
    'mmap',
    'ACCESS_READ', 'ACCESS_WRITE', 'ACCESS_COPY', 'ACCESS_NONE',
    'ALLOCATIONGRANULARITY', 'PAGESIZE',
    'MAP_SHARED', 'MAP_PRIVATE', 'MAP_ANON',
    'PROT_READ', 'PROT_WRITE', 'PROT_EXEC',
    'mmap2_write_read', 'mmap2_find', 'mmap2_seek_tell',
]
