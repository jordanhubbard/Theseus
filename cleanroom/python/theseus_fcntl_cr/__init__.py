"""Clean-room reimplementation of fcntl using ctypes to call libc directly.

Does not import the original `fcntl` module. All functionality is provided by
direct libc syscalls via ctypes (a Python standard library module).
"""

import ctypes
import ctypes.util
import os
import platform
import tempfile

# ---------------------------------------------------------------------------
# Platform-specific constants
# ---------------------------------------------------------------------------

_system = platform.system()

if _system == "Darwin":
    F_DUPFD = 0
    F_GETFD = 1
    F_SETFD = 2
    F_GETFL = 3
    F_SETFL = 4
    F_GETOWN = 5
    F_SETOWN = 6
    F_GETLK = 7
    F_SETLK = 8
    F_SETLKW = 9
elif _system == "Linux":
    F_DUPFD = 0
    F_GETFD = 1
    F_SETFD = 2
    F_GETFL = 3
    F_SETFL = 4
    F_GETLK = 5
    F_SETLK = 6
    F_SETLKW = 7
    F_SETOWN = 8
    F_GETOWN = 9
else:
    # Reasonable defaults shared by most POSIX systems
    F_DUPFD = 0
    F_GETFD = 1
    F_SETFD = 2
    F_GETFL = 3
    F_SETFL = 4
    F_GETLK = 5
    F_SETLK = 6
    F_SETLKW = 7

# flock(2) operations -- same on Linux, macOS, *BSD
LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8

# Close-on-exec flag for F_SETFD
FD_CLOEXEC = 1

# Lock type values for struct flock
F_RDLCK = 0 if _system == "Linux" else 1
F_WRLCK = 1 if _system == "Linux" else 3
F_UNLCK = 2

# ---------------------------------------------------------------------------
# libc bindings
# ---------------------------------------------------------------------------

_libc_path = ctypes.util.find_library("c")
if _libc_path is None:
    # Fall back to common names
    _libc_path = "libc.so.6" if _system == "Linux" else "libc.dylib"

_libc = ctypes.CDLL(_libc_path, use_errno=True)

# fcntl is variadic; we'll invoke it with explicit arg types per call.
_libc.fcntl.restype = ctypes.c_int

_libc.flock.argtypes = [ctypes.c_int, ctypes.c_int]
_libc.flock.restype = ctypes.c_int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_fd(file_or_fd):
    """Accept an int fd or an object with .fileno()."""
    if isinstance(file_or_fd, int):
        return file_or_fd
    fileno = getattr(file_or_fd, "fileno", None)
    if fileno is None:
        raise TypeError("argument must be an int or have a fileno() method")
    return int(fileno())


def _oserror_from_errno():
    err = ctypes.get_errno()
    return OSError(err, os.strerror(err))


# ---------------------------------------------------------------------------
# Public API: fcntl, flock, ioctl-lite
# ---------------------------------------------------------------------------

def fcntl(fd, cmd, arg=0):
    """Perform fcntl(fd, cmd, arg).

    If `arg` is a bytes/bytearray, it is passed as a buffer and the (possibly
    mutated) buffer contents are returned. Otherwise it is passed as an
    integer and the return value (an int) is returned.
    """
    fd = _coerce_fd(fd)

    if isinstance(arg, (bytes, bytearray)):
        raw = bytes(arg)
        buf = ctypes.create_string_buffer(raw, len(raw))
        ctypes.set_errno(0)
        rv = _libc.fcntl(ctypes.c_int(fd), ctypes.c_int(cmd), buf)
        if rv < 0:
            raise _oserror_from_errno()
        return buf.raw[: len(raw)]

    if not isinstance(arg, int):
        raise TypeError("arg must be an int or bytes-like object")

    ctypes.set_errno(0)
    rv = _libc.fcntl(ctypes.c_int(fd), ctypes.c_int(cmd), ctypes.c_long(arg))
    if rv < 0:
        raise _oserror_from_errno()
    return rv


def flock(fd, operation):
    """Apply or remove an advisory file lock on `fd` (flock(2))."""
    fd = _coerce_fd(fd)
    ctypes.set_errno(0)
    rv = _libc.flock(ctypes.c_int(fd), ctypes.c_int(operation))
    if rv < 0:
        raise _oserror_from_errno()
    return None


# Convenience wrappers
def lockf(fd, operation, length=0, start=0, whence=0):
    """Best-effort POSIX lockf-style wrapper using flock semantics."""
    fd = _coerce_fd(fd)
    if operation == LOCK_UN:
        return flock(fd, LOCK_UN)
    return flock(fd, operation)


# ---------------------------------------------------------------------------
# Self-test / invariant functions
# ---------------------------------------------------------------------------

def fcntl2_getfl():
    """Invariant: fcntl(fd, F_GETFL) returns a non-negative integer for an
    open file descriptor."""
    try:
        with tempfile.TemporaryFile() as tf:
            fd = tf.fileno()
            flags = fcntl(fd, F_GETFL)
            if not isinstance(flags, int):
                return False
            if flags < 0:
                return False
            # F_GETFD should also yield a non-negative int
            fd_flags = fcntl(fd, F_GETFD)
            if not isinstance(fd_flags, int) or fd_flags < 0:
                return False
        return True
    except Exception:
        return False


def fcntl2_constants():
    """Invariant: required fcntl/flock constants exist, are integers, and
    have the well-known POSIX flock relationships."""
    try:
        required = [
            "F_GETFD", "F_SETFD", "F_GETFL", "F_SETFL",
            "LOCK_SH", "LOCK_EX", "LOCK_NB", "LOCK_UN",
            "FD_CLOEXEC",
        ]
        g = globals()
        for name in required:
            if name not in g:
                return False
            if not isinstance(g[name], int):
                return False

        # Distinctness / well-known values
        if LOCK_SH == LOCK_EX or LOCK_SH == LOCK_UN or LOCK_EX == LOCK_UN:
            return False
        if LOCK_NB == 0:
            return False
        if LOCK_SH != 1 or LOCK_EX != 2 or LOCK_NB != 4 or LOCK_UN != 8:
            return False
        if FD_CLOEXEC != 1:
            return False
        # F_GETFL / F_SETFL must differ
        if F_GETFL == F_SETFL:
            return False
        return True
    except Exception:
        return False


def fcntl2_flock():
    """Invariant: flock(LOCK_EX|LOCK_NB) succeeds on a fresh temp file and
    LOCK_UN releases it."""
    try:
        with tempfile.TemporaryFile() as tf:
            fd = tf.fileno()
            # Acquire exclusive non-blocking lock
            flock(fd, LOCK_EX | LOCK_NB)
            # Release
            flock(fd, LOCK_UN)
            # Acquire shared, then release
            flock(fd, LOCK_SH | LOCK_NB)
            flock(fd, LOCK_UN)
        return True
    except Exception:
        return False


__all__ = [
    "fcntl", "flock", "lockf",
    "F_DUPFD", "F_GETFD", "F_SETFD", "F_GETFL", "F_SETFL",
    "F_GETLK", "F_SETLK", "F_SETLKW",
    "LOCK_SH", "LOCK_EX", "LOCK_NB", "LOCK_UN",
    "FD_CLOEXEC", "F_RDLCK", "F_WRLCK", "F_UNLCK",
    "fcntl2_getfl", "fcntl2_constants", "fcntl2_flock",
]