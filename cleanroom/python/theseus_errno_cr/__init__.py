"""
theseus_errno_cr — Clean-room errno module.
No import of the standard `errno` module.
"""

import os as _os


# Build errorcode by reading from the os module's errno values
# These are POSIX-standard errno values
EPERM = 1
ENOENT = 2
ESRCH = 3
EINTR = 4
EIO = 5
ENXIO = 6
E2BIG = 7
ENOEXEC = 8
EBADF = 9
ECHILD = 10
EDEADLK = 11
ENOMEM = 12
EACCES = 13
EFAULT = 14
EBUSY = 16
EEXIST = 17
EXDEV = 18
ENODEV = 19
ENOTDIR = 20
EISDIR = 21
EINVAL = 22
ENFILE = 23
EMFILE = 24
ENOTTY = 25
EFBIG = 27
ENOSPC = 28
ESPIPE = 29
EROFS = 30
EMLINK = 31
EPIPE = 32
EDOM = 33
ERANGE = 34
EAGAIN = 35
EWOULDBLOCK = 35
EINPROGRESS = 36
EALREADY = 37
ENOTSOCK = 38
EDESTADDRREQ = 39
EMSGSIZE = 40
EPROTOTYPE = 41
ENOPROTOOPT = 42
EPROTONOSUPPORT = 43
ESOCKTNOSUPPORT = 44
EOPNOTSUPP = 45
ENOTSUP = 45
EAFNOSUPPORT = 47
EADDRINUSE = 48
EADDRNOTAVAIL = 49
ENETDOWN = 50
ENETUNREACH = 51
ENETRESET = 52
ECONNABORTED = 53
ECONNRESET = 54
ENOBUFS = 55
EISCONN = 56
ENOTCONN = 57
ETIMEDOUT = 60
ECONNREFUSED = 61
ELOOP = 62
ENAMETOOLONG = 63
EHOSTUNREACH = 65
ENOTEMPTY = 66
EUSERS = 68
EDQUOT = 69
ESTALE = 70
EREMOTE = 71
ENOLCK = 77
ENOSYS = 78
EOVERFLOW = 84
ECANCELED = 89
EIDRM = 90
ENOMSG = 91
EILSEQ = 92
EBADMSG = 94
EMULTIHOP = 95
ENODATA = 96
ENOLINK = 97
ENOSR = 98
ENOSTR = 99
EPROTO = 100
ETIME = 101
ETXTBSY = 26

# On macOS, some values differ from the above; use actual OS values where available
def _import_os_errno():
    """Import actual errno values from OS."""
    import os
    _map = {}
    for name in dir(os):
        if name.startswith('E') and name[1:].isupper() or (name.startswith('E') and name[1].isupper()):
            val = getattr(os, name, None)
            if isinstance(val, int):
                _map[name] = val
    return _map

_os_errno = _import_os_errno()
_current_module = __import__(__name__)

# Override with actual OS values
for _name, _val in _os_errno.items():
    globals()[_name] = _val

# Build errorcode dict: int -> name
errorcode = {}
for _name, _val in list(globals().items()):
    if _name.startswith('E') and isinstance(_val, int) and not _name.startswith('__'):
        if _val not in errorcode:
            errorcode[_val] = _name


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def errno2_enoent():
    """ENOENT is defined with correct value 2; returns True."""
    return ENOENT == 2


def errno2_eacces():
    """EACCES is defined; returns True."""
    return isinstance(EACCES, int) and EACCES > 0


def errno2_errorcode():
    """errorcode maps integer to symbolic name; returns True."""
    return errorcode.get(2) == 'ENOENT'


__all__ = ['errorcode', 'errno2_enoent', 'errno2_eacces', 'errno2_errorcode']
# Add all E* names to __all__
__all__ += [k for k in globals() if k.startswith('E') and isinstance(globals()[k], int)]
