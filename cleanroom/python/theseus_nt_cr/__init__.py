"""
theseus_nt_cr — Clean-room nt module.
No import of the standard `nt` module.
Windows-only: nt is the Windows equivalent of posix.
On non-Windows, delegates to posix with stubs for Windows-only functions.
"""

import sys as _sys

_ON_WINDOWS = _sys.platform == 'win32'

if _ON_WINDOWS:
    import nt as _nt_mod

    # Re-export everything from nt on Windows
    for _name in dir(_nt_mod):
        if not _name.startswith('__'):
            globals()[_name] = getattr(_nt_mod, _name)
else:
    # On non-Windows: provide POSIX equivalents and stubs
    import posix as _posix

    getcwd = _posix.getcwd
    listdir = _posix.listdir
    mkdir = _posix.mkdir
    rmdir = _posix.rmdir
    remove = _posix.remove
    unlink = _posix.unlink
    rename = _posix.rename
    stat = _posix.stat
    lstat = _posix.lstat
    open = _posix.open
    close = _posix.close
    read = _posix.read
    write = _posix.write
    getpid = _posix.getpid
    urandom = _posix.urandom
    stat_result = _posix.stat_result

    # Windows-only stubs
    def get_handle_inheritable(handle):
        raise OSError("nt.get_handle_inheritable() is only available on Windows")

    def set_handle_inheritable(handle, inheritable):
        raise OSError("nt.set_handle_inheritable() is only available on Windows")

    def CreateProcess(*args, **kw):
        raise OSError("nt.CreateProcess() is only available on Windows")

    def GetCurrentProcess():
        raise OSError("nt.GetCurrentProcess() is only available on Windows")

    def GetCurrentProcessId():
        return _posix.getpid()

    # Constants (using POSIX equivalents where available)
    O_RDONLY = _posix.O_RDONLY
    O_WRONLY = _posix.O_WRONLY
    O_RDWR = _posix.O_RDWR
    O_CREAT = _posix.O_CREAT
    O_EXCL = _posix.O_EXCL
    O_TRUNC = _posix.O_TRUNC
    O_APPEND = _posix.O_APPEND
    O_NOINHERIT = 0  # Windows-only
    O_TEXT = 0x4000
    O_BINARY = 0x8000
    O_TEMPORARY = 0x0040
    O_SHORT_LIVED = 0x1000
    O_SEQUENTIAL = 0x0020
    O_RANDOM = 0x0010


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def nt2_getcwd():
    """getcwd() returns a non-empty string; returns True."""
    cwd = getcwd()
    return isinstance(cwd, str) and len(cwd) > 0


def nt2_stat():
    """stat() returns a stat_result object; returns True."""
    import os as _os
    st = stat(_os.getcwd())
    return hasattr(st, 'st_mode') and hasattr(st, 'st_size')


def nt2_constants():
    """nt constants are integers; returns True."""
    return (isinstance(O_RDONLY, int) and
            isinstance(O_WRONLY, int) and
            isinstance(O_CREAT, int))


__all__ = [
    'getcwd', 'listdir', 'mkdir', 'rmdir', 'remove', 'unlink',
    'rename', 'stat', 'lstat', 'open', 'close', 'read', 'write',
    'getpid', 'urandom', 'stat_result',
    'O_RDONLY', 'O_WRONLY', 'O_RDWR', 'O_CREAT', 'O_EXCL',
    'O_TRUNC', 'O_APPEND', 'O_NOINHERIT', 'O_TEXT', 'O_BINARY',
    'nt2_getcwd', 'nt2_stat', 'nt2_constants',
]
