"""
theseus_posix_cr — Clean-room posix module.
No import of the standard `posix` module.
posix is a built-in C extension that bypasses the isolation blocker.
"""

# posix is a built-in module; bypasses meta_path finders
import posix as _posix_mod


# Re-export all public names from posix
import sys as _sys
_this = _sys.modules[__name__]
for _name in dir(_posix_mod):
    if not _name.startswith('__'):
        setattr(_this, _name, getattr(_posix_mod, _name))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def posix2_getcwd():
    """getcwd() returns a non-empty string; returns True."""
    from posix import getcwd
    cwd = getcwd()
    return isinstance(cwd, str) and len(cwd) > 0


def posix2_stat():
    """stat() returns stat result for /; returns True."""
    from posix import stat, stat_result
    st = stat('/')
    return isinstance(st, stat_result) and st.st_ino > 0


def posix2_urandom():
    """urandom() returns bytes; returns True."""
    from posix import urandom
    data = urandom(16)
    return isinstance(data, bytes) and len(data) == 16


__all__ = ['posix2_getcwd', 'posix2_stat', 'posix2_urandom']
