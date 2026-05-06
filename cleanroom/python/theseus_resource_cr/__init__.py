"""Clean-room implementation of the Python ``resource`` module.

Uses ctypes to call libc's getrlimit/setrlimit/getrusage directly so that we
do not depend on the original ``resource`` module at all.
"""

import sys
import os
import ctypes
import ctypes.util

__all__ = [
    "error",
    "struct_rusage",
    "getrlimit",
    "setrlimit",
    "getrusage",
    "getpagesize",
    "RLIM_INFINITY",
    "RUSAGE_SELF",
    "RUSAGE_CHILDREN",
    "resource2_getrlimit",
    "resource2_constants",
    "resource2_getrusage",
]

_IS_LINUX = sys.platform.startswith("linux")
_IS_DARWIN = sys.platform == "darwin"
_IS_FREEBSD = sys.platform.startswith("freebsd")
_IS_OPENBSD = sys.platform.startswith("openbsd")
_IS_NETBSD = sys.platform.startswith("netbsd")
_IS_BSD = _IS_FREEBSD or _IS_OPENBSD or _IS_NETBSD or _IS_DARWIN


# --------------------------------------------------------------------------
# Load libc
# --------------------------------------------------------------------------

def _load_libc():
    candidates = []
    found = ctypes.util.find_library("c")
    if found:
        candidates.append(found)
    if _IS_LINUX:
        candidates.extend(["libc.so.6", "libc.so"])
    elif _IS_DARWIN:
        candidates.extend(["/usr/lib/libSystem.B.dylib", "libc.dylib"])
    else:
        candidates.extend(["libc.so", "libc.so.7", "libc.so.6"])
    for name in candidates:
        try:
            return ctypes.CDLL(name, use_errno=True)
        except OSError:
            continue
    return None


_libc = _load_libc()


# --------------------------------------------------------------------------
# Error type
# --------------------------------------------------------------------------

class error(OSError):
    """Resource-related error."""
    pass


# --------------------------------------------------------------------------
# Constants — values vary per platform
# --------------------------------------------------------------------------

# RUSAGE_* constants (same across most POSIX systems)
RUSAGE_SELF = 0
RUSAGE_CHILDREN = -1
if _IS_LINUX:
    RUSAGE_THREAD = 1
    __all__.append("RUSAGE_THREAD")
elif _IS_FREEBSD or _IS_NETBSD:
    RUSAGE_THREAD = 1
    __all__.append("RUSAGE_THREAD")

# RLIMIT_* constants
if _IS_DARWIN:
    RLIMIT_CPU = 0
    RLIMIT_FSIZE = 1
    RLIMIT_DATA = 2
    RLIMIT_STACK = 3
    RLIMIT_CORE = 4
    RLIMIT_AS = 5
    RLIMIT_RSS = 5  # alias on Darwin
    RLIMIT_MEMLOCK = 6
    RLIMIT_NPROC = 7
    RLIMIT_NOFILE = 8
    __all__.extend([
        "RLIMIT_CPU", "RLIMIT_FSIZE", "RLIMIT_DATA", "RLIMIT_STACK",
        "RLIMIT_CORE", "RLIMIT_AS", "RLIMIT_RSS", "RLIMIT_MEMLOCK",
        "RLIMIT_NPROC", "RLIMIT_NOFILE",
    ])
elif _IS_FREEBSD or _IS_OPENBSD or _IS_NETBSD:
    RLIMIT_CPU = 0
    RLIMIT_FSIZE = 1
    RLIMIT_DATA = 2
    RLIMIT_STACK = 3
    RLIMIT_CORE = 4
    RLIMIT_RSS = 5
    RLIMIT_MEMLOCK = 6
    RLIMIT_NPROC = 7
    RLIMIT_NOFILE = 8
    RLIMIT_SBSIZE = 9
    RLIMIT_AS = 10
    RLIMIT_VMEM = 10  # alias
    __all__.extend([
        "RLIMIT_CPU", "RLIMIT_FSIZE", "RLIMIT_DATA", "RLIMIT_STACK",
        "RLIMIT_CORE", "RLIMIT_RSS", "RLIMIT_MEMLOCK", "RLIMIT_NPROC",
        "RLIMIT_NOFILE", "RLIMIT_SBSIZE", "RLIMIT_AS", "RLIMIT_VMEM",
    ])
else:
    # Linux defaults
    RLIMIT_CPU = 0
    RLIMIT_FSIZE = 1
    RLIMIT_DATA = 2
    RLIMIT_STACK = 3
    RLIMIT_CORE = 4
    RLIMIT_RSS = 5
    RLIMIT_NPROC = 6
    RLIMIT_NOFILE = 7
    RLIMIT_OFILE = 7  # alias
    RLIMIT_MEMLOCK = 8
    RLIMIT_AS = 9
    RLIMIT_LOCKS = 10
    RLIMIT_SIGPENDING = 11
    RLIMIT_MSGQUEUE = 12
    RLIMIT_NICE = 13
    RLIMIT_RTPRIO = 14
    RLIMIT_RTTIME = 15
    __all__.extend([
        "RLIMIT_CPU", "RLIMIT_FSIZE", "RLIMIT_DATA", "RLIMIT_STACK",
        "RLIMIT_CORE", "RLIMIT_RSS", "RLIMIT_NPROC", "RLIMIT_NOFILE",
        "RLIMIT_OFILE", "RLIMIT_MEMLOCK", "RLIMIT_AS", "RLIMIT_LOCKS",
        "RLIMIT_SIGPENDING", "RLIMIT_MSGQUEUE", "RLIMIT_NICE",
        "RLIMIT_RTPRIO", "RLIMIT_RTTIME",
    ])

# RLIM_INFINITY: Python casts (rlim_t) to (long long).
# On Linux, RLIM_INFINITY == (uint64_t)-1, which casts to -1.
# On Darwin, RLIM_INFINITY == 0x7FFFFFFFFFFFFFFF, which stays as that value.
if _IS_DARWIN:
    RLIM_INFINITY = 0x7FFFFFFFFFFFFFFF
else:
    # On Linux/most BSDs, RLIM_INFINITY is (rlim_t)-1, signed-cast to -1.
    RLIM_INFINITY = -1


# --------------------------------------------------------------------------
# C struct definitions
# --------------------------------------------------------------------------

class _Rlimit(ctypes.Structure):
    _fields_ = [
        ("rlim_cur", ctypes.c_uint64),
        ("rlim_max", ctypes.c_uint64),
    ]


# timeval differs per platform (tv_usec is 32-bit on Darwin, long on Linux)
if _IS_DARWIN:
    class _Timeval(ctypes.Structure):
        _fields_ = [
            ("tv_sec", ctypes.c_long),
            ("tv_usec", ctypes.c_int32),
        ]
else:
    class _Timeval(ctypes.Structure):
        _fields_ = [
            ("tv_sec", ctypes.c_long),
            ("tv_usec", ctypes.c_long),
        ]


class _Rusage(ctypes.Structure):
    _fields_ = [
        ("ru_utime", _Timeval),
        ("ru_stime", _Timeval),
        ("ru_maxrss", ctypes.c_long),
        ("ru_ixrss", ctypes.c_long),
        ("ru_idrss", ctypes.c_long),
        ("ru_isrss", ctypes.c_long),
        ("ru_minflt", ctypes.c_long),
        ("ru_majflt", ctypes.c_long),
        ("ru_nswap", ctypes.c_long),
        ("ru_inblock", ctypes.c_long),
        ("ru_oublock", ctypes.c_long),
        ("ru_msgsnd", ctypes.c_long),
        ("ru_msgrcv", ctypes.c_long),
        ("ru_nsignals", ctypes.c_long),
        ("ru_nvcsw", ctypes.c_long),
        ("ru_nivcsw", ctypes.c_long),
    ]


# --------------------------------------------------------------------------
# struct_rusage — named-tuple-like return type
# --------------------------------------------------------------------------

_RUSAGE_FIELDS = (
    "ru_utime", "ru_stime", "ru_maxrss", "ru_ixrss", "ru_idrss", "ru_isrss",
    "ru_minflt", "ru_majflt", "ru_nswap", "ru_inblock", "ru_oublock",
    "ru_msgsnd", "ru_msgrcv", "ru_nsignals", "ru_nvcsw", "ru_nivcsw",
)


class struct_rusage(tuple):
    """Resource usage information; tuple of 16 fields."""

    n_fields = 16
    n_sequence_fields = 16
    n_unnamed_fields = 0

    __slots__ = ()

    def __new__(cls, iterable):
        values = tuple(iterable)
        if len(values) != 16:
            raise TypeError(
                "struct_rusage takes a 16-sequence (%d-sequence given)"
                % len(values)
            )
        return tuple.__new__(cls, values)

    @property
    def ru_utime(self):
        return self[0]

    @property
    def ru_stime(self):
        return self[1]

    @property
    def ru_maxrss(self):
        return self[2]

    @property
    def ru_ixrss(self):
        return self[3]

    @property
    def ru_idrss(self):
        return self[4]

    @property
    def ru_isrss(self):
        return self[5]

    @property
    def ru_minflt(self):
        return self[6]

    @property
    def ru_majflt(self):
        return self[7]

    @property
    def ru_nswap(self):
        return self[8]

    @property
    def ru_inblock(self):
        return self[9]

    @property
    def ru_oublock(self):
        return self[10]

    @property
    def ru_msgsnd(self):
        return self[11]

    @property
    def ru_msgrcv(self):
        return self[12]

    @property
    def ru_nsignals(self):
        return self[13]

    @property
    def ru_nvcsw(self):
        return self[14]

    @property
    def ru_nivcsw(self):
        return self[15]

    def __repr__(self):
        parts = ", ".join(
            "%s=%r" % (name, self[i]) for i, name in enumerate(_RUSAGE_FIELDS)
        )
        return "resource.struct_rusage(" + parts + ")"


# --------------------------------------------------------------------------
# Wire up libc function signatures
# --------------------------------------------------------------------------

if _libc is not None:
    try:
        _libc.getrlimit.argtypes = [ctypes.c_int, ctypes.POINTER(_Rlimit)]
        _libc.getrlimit.restype = ctypes.c_int
        _libc.setrlimit.argtypes = [ctypes.c_int, ctypes.POINTER(_Rlimit)]
        _libc.setrlimit.restype = ctypes.c_int
        _libc.getrusage.argtypes = [ctypes.c_int, ctypes.POINTER(_Rusage)]
        _libc.getrusage.restype = ctypes.c_int
    except AttributeError:
        pass


def _require_libc():
    if _libc is None:
        raise error("libc is unavailable on this platform")


def _to_signed64(v):
    """Cast a 64-bit unsigned value to signed long long, like CPython's
    Py_BuildValue("L", (long long) rl.rlim_cur)."""
    v &= 0xFFFFFFFFFFFFFFFF
    if v >= (1 << 63):
        return v - (1 << 64)
    return v


def _from_signed_limit(v):
    """Convert a Python int representing a (possibly signed) rlimit value
    back to the underlying unsigned 64-bit representation."""
    iv = int(v)
    if iv < 0:
        iv += 1 << 64
    iv &= 0xFFFFFFFFFFFFFFFF
    return iv


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def getrlimit(resource_id):
    """Return the (soft, hard) resource limits as a 2-tuple of integers."""
    _require_libc()
    rid = int(resource_id)
    rl = _Rlimit()
    rc = _libc.getrlimit(rid, ctypes.byref(rl))
    if rc != 0:
        e = ctypes.get_errno()
        raise error(e, os.strerror(e))
    return (_to_signed64(rl.rlim_cur), _to_signed64(rl.rlim_max))


def setrlimit(resource_id, limits):
    """Set (soft, hard) resource limits."""
    _require_libc()
    rid = int(resource_id)
    try:
        soft, hard = limits
    except (TypeError, ValueError):
        raise ValueError("expected a tuple of 2 integers")
    soft_u = _from_signed_limit(soft)
    hard_u = _from_signed_limit(hard)
    rl = _Rlimit(rlim_cur=soft_u, rlim_max=hard_u)
    rc = _libc.setrlimit(rid, ctypes.byref(rl))
    if rc != 0:
        e = ctypes.get_errno()
        raise error(e, os.strerror(e))
    return None


def getrusage(who):
    """Return resource usage information for the specified target as a
    struct_rusage 16-tuple."""
    _require_libc()
    target = int(who)
    ru = _Rusage()
    rc = _libc.getrusage(target, ctypes.byref(ru))
    if rc != 0:
        e = ctypes.get_errno()
        # CPython raises ValueError for invalid 'who' (EINVAL).
        if e == 22:  # EINVAL
            raise ValueError("invalid who parameter")
        raise error(e, os.strerror(e))

    def _tv_to_float(tv):
        return float(tv.tv_sec) + float(tv.tv_usec) / 1e6

    return struct_rusage((
        _tv_to_float(ru.ru_utime),
        _tv_to_float(ru.ru_stime),
        int(ru.ru_maxrss),
        int(ru.ru_ixrss),
        int(ru.ru_idrss),
        int(ru.ru_isrss),
        int(ru.ru_minflt),
        int(ru.ru_majflt),
        int(ru.ru_nswap),
        int(ru.ru_inblock),
        int(ru.ru_oublock),
        int(ru.ru_msgsnd),
        int(ru.ru_msgrcv),
        int(ru.ru_nsignals),
        int(ru.ru_nvcsw),
        int(ru.ru_nivcsw),
    ))


def getpagesize():
    """Return the system page size in bytes."""
    try:
        return os.sysconf("SC_PAGESIZE")
    except (ValueError, OSError, AttributeError):
        pass
    try:
        return os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError, AttributeError):
        pass
    # Last resort sensible default
    return 4096


# --------------------------------------------------------------------------
# Linux-only: prlimit
# --------------------------------------------------------------------------

if _IS_LINUX and _libc is not None:
    try:
        _libc.prlimit.argtypes = [
            ctypes.c_int,            # pid_t
            ctypes.c_int,            # resource
            ctypes.POINTER(_Rlimit),  # new_limit
            ctypes.POINTER(_Rlimit),  # old_limit
        ]
        _libc.prlimit.restype = ctypes.c_int
        _has_prlimit = True
    except AttributeError:
        _has_prlimit = False
else:
    _has_prlimit = False


if _has_prlimit:
    def prlimit(pid, resource_id, limits=None):
        """Get or set resource limits of an arbitrary process by pid."""
        rid = int(resource_id)
        old = _Rlimit()
        if limits is None:
            rc = _libc.prlimit(int(pid), rid, None, ctypes.byref(old))
            if rc != 0:
                e = ctypes.get_errno()
                raise error(e, os.strerror(e))
            return (_to_signed64(old.rlim_cur), _to_signed64(old.rlim_max))
        try:
            soft, hard = limits
        except (TypeError, ValueError):
            raise ValueError("expected a tuple of 2 integers")
        new = _Rlimit(
            rlim_cur=_from_signed_limit(soft),
            rlim_max=_from_signed_limit(hard),
        )
        rc = _libc.prlimit(int(pid), rid, ctypes.byref(new), ctypes.byref(old))
        if rc != 0:
            e = ctypes.get_errno()
            raise error(e, os.strerror(e))
        return (_to_signed64(old.rlim_cur), _to_signed64(old.rlim_max))

    __all__.append("prlimit")


# --------------------------------------------------------------------------
# Behavioral invariant entry points
#
# These functions are the test entry points referenced by the spec's
# invariants. Each one exercises a piece of the public API and returns
# True if the result has the expected shape/types.
# --------------------------------------------------------------------------

def resource2_getrlimit():
    """Verify getrlimit(RLIMIT_NOFILE) returns a 2-tuple of integers."""
    try:
        result = getrlimit(RLIMIT_NOFILE)
    except Exception:
        return False
    if not isinstance(result, tuple):
        return False
    if len(result) != 2:
        return False
    soft, hard = result
    if not isinstance(soft, int) or not isinstance(hard, int):
        return False
    return True


def resource2_constants():
    """Verify RLIMIT_NOFILE and RLIM_INFINITY constants are integers."""
    if not isinstance(RLIMIT_NOFILE, int) or isinstance(RLIMIT_NOFILE, bool):
        return False
    if not isinstance(RLIM_INFINITY, int) or isinstance(RLIM_INFINITY, bool):
        return False
    return True


def resource2_getrusage():
    """Verify getrusage(RUSAGE_SELF) returns a struct_rusage instance."""
    try:
        result = getrusage(RUSAGE_SELF)
    except Exception:
        return False
    if not isinstance(result, struct_rusage):
        return False
    if len(result) != 16:
        return False
    if not isinstance(result.ru_utime, float):
        return False
    if not isinstance(result.ru_stime, float):
        return False
    for i in range(2, 16):
        if not isinstance(result[i], int):
            return False
    return True