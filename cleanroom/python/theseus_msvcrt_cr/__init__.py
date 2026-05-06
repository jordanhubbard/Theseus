"""
theseus_msvcrt_cr - Clean-room msvcrt module stub.

This module is a behavioral specification implementation of CPython's
``msvcrt`` module. It does NOT import ``msvcrt`` (or the underlying
``_msvcrt`` C extension). On non-Windows platforms every function stub
raises ``OSError``. On Windows, the stubs likewise raise ``OSError``
because no real console / CRT bindings are wired up in the clean-room
build; the surface area (names, constants, signatures) matches the
documented public API.
"""

import sys as _sys

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

_ON_WINDOWS = _sys.platform == "win32"


def _not_available(name):
    """Raise OSError for an msvcrt entry point that is unavailable here."""
    raise OSError(
        "msvcrt.%s() is only available on Windows "
        "(theseus_msvcrt_cr is a clean-room stub)" % name
    )


# ---------------------------------------------------------------------------
# CRT / file translation constants
#
# Values mirror the documented Windows CRT header values. They are exposed
# as plain integers (and one string for CRT_ASSEMBLY_VERSION) so callers
# can reason about file modes without needing the real msvcrt.
# ---------------------------------------------------------------------------

CRT_ASSEMBLY_VERSION = "14.0.0.0"

# fcntl-style oflag constants from <fcntl.h> on Windows
O_RDONLY = 0x0000
O_WRONLY = 0x0001
O_RDWR = 0x0002
O_APPEND = 0x0008
O_CREAT = 0x0100
O_TRUNC = 0x0200
O_EXCL = 0x0400
O_TEXT = 0x4000
O_BINARY = 0x8000
O_NOINHERIT = 0x0080
O_TEMPORARY = 0x0040
O_SHORT_LIVED = 0x1000
O_OBTAIN_DIR = 0x2000
O_RANDOM = 0x0010
O_SEQUENTIAL = 0x0020

# locking() mode constants
LK_LOCK = 1
LK_NBLCK = 2
LK_NBRLCK = 3
LK_RLCK = 4
LK_UNLCK = 0

# SetErrorMode flags
SEM_FAILCRITICALERRORS = 0x0001
SEM_NOALIGNMENTFAULTEXCEPT = 0x0004
SEM_NOGPFAULTERRORBOX = 0x0002
SEM_NOOPENFILEERRORBOX = 0x8000


# ---------------------------------------------------------------------------
# Console I/O stubs
# ---------------------------------------------------------------------------

def getch():
    """Read a single keypress from the console (Windows only)."""
    _not_available("getch")


def getwch():
    """Wide-character variant of getch (Windows only)."""
    _not_available("getwch")


def getche():
    """Read a keypress and echo it to the console (Windows only)."""
    _not_available("getche")


def getwche():
    """Wide-character variant of getche (Windows only)."""
    _not_available("getwche")


def putch(char):
    """Print a byte character to the console (Windows only)."""
    _not_available("putch")


def putwch(char):
    """Print a wide character to the console (Windows only)."""
    _not_available("putwch")


def ungetch(char):
    """Push a character back into the console input buffer (Windows only)."""
    _not_available("ungetch")


def ungetwch(char):
    """Push a wide character back into the input buffer (Windows only)."""
    _not_available("ungetwch")


def kbhit():
    """Return True if a keypress is waiting to be read.

    On non-Windows platforms there is no console keyboard buffer, so this
    deterministically returns ``False`` (rather than raising) - matching the
    documented "no key pressed" outcome.
    """
    if _ON_WINDOWS:
        # We have no real console binding; report that no key is waiting.
        return False
    return False


# ---------------------------------------------------------------------------
# File descriptor / handle stubs
# ---------------------------------------------------------------------------

def setmode(fd, flags):
    """Set translation mode (text/binary) of an open fd (Windows only)."""
    _not_available("setmode")


def open_osfhandle(osfhandle, flags):
    """Create a C-runtime fd from an OS file handle (Windows only)."""
    _not_available("open_osfhandle")


def get_osfhandle(fd):
    """Return the OS file handle backing a C-runtime fd (Windows only)."""
    _not_available("get_osfhandle")


def locking(fd, mode, nbytes):
    """Lock / unlock a region of an open file (Windows only)."""
    _not_available("locking")


# ---------------------------------------------------------------------------
# Misc CRT stubs
# ---------------------------------------------------------------------------

def heapmin():
    """Force the CRT heap to release unused pages (Windows only)."""
    _not_available("heapmin")


def SetErrorMode(mode):
    """Wrapper around the Win32 SetErrorMode function (Windows only)."""
    _not_available("SetErrorMode")


def CrtSetReportMode(type, mode):
    """Configure CRT debug report mode (Windows only)."""
    _not_available("CrtSetReportMode")


def CrtSetReportFile(type, file):
    """Configure CRT debug report file (Windows only)."""
    _not_available("CrtSetReportFile")


# ---------------------------------------------------------------------------
# Invariant validators
# ---------------------------------------------------------------------------

def msvcrt2_constants():
    """msvcrt constants have correct types."""
    int_constants = (
        O_RDONLY, O_WRONLY, O_RDWR, O_APPEND, O_CREAT, O_TRUNC, O_EXCL,
        O_TEXT, O_BINARY, O_NOINHERIT, O_TEMPORARY,
        O_SHORT_LIVED, O_OBTAIN_DIR, O_RANDOM, O_SEQUENTIAL,
        LK_LOCK, LK_NBLCK, LK_NBRLCK, LK_RLCK, LK_UNLCK,
        SEM_FAILCRITICALERRORS, SEM_NOALIGNMENTFAULTEXCEPT,
        SEM_NOGPFAULTERRORBOX, SEM_NOOPENFILEERRORBOX,
    )
    if not all(isinstance(c, int) and not isinstance(c, bool) for c in int_constants):
        return False
    if not isinstance(CRT_ASSEMBLY_VERSION, str):
        return False
    # Sanity: text and binary translation modes must differ
    if O_TEXT == O_BINARY:
        return False
    # Distinct lock modes
    if len({LK_LOCK, LK_NBLCK, LK_NBRLCK, LK_RLCK, LK_UNLCK}) != 5:
        return False
    return True


def msvcrt2_platform():
    """msvcrt stubs correctly reflect platform."""
    is_win = _sys.platform == "win32"

    # kbhit must not raise; it should return a boolean on every platform.
    try:
        hit = kbhit()
    except Exception:
        return False
    if not isinstance(hit, bool):
        return False

    if is_win:
        # On Windows the stub still reports "no key" (False) because we do
        # not bind to the real CRT, but it must remain a non-raising call.
        return hit is False

    # Non-Windows: the documented Windows-only entry points must raise OSError.
    windows_only = (
        ("getch", lambda: getch()),
        ("getwch", lambda: getwch()),
        ("getche", lambda: getche()),
        ("getwche", lambda: getwche()),
        ("putch", lambda: putch(b"x")),
        ("putwch", lambda: putwch("x")),
        ("ungetch", lambda: ungetch(b"x")),
        ("ungetwch", lambda: ungetwch("x")),
        ("setmode", lambda: setmode(0, O_BINARY)),
        ("open_osfhandle", lambda: open_osfhandle(0, 0)),
        ("get_osfhandle", lambda: get_osfhandle(0)),
        ("locking", lambda: locking(0, LK_LOCK, 0)),
        ("heapmin", lambda: heapmin()),
    )
    for _name, fn in windows_only:
        try:
            fn()
        except OSError:
            continue
        except Exception:
            return False
        else:
            return False
    return hit is False


def msvcrt2_functions():
    """msvcrt function stubs are callable."""
    expected = (
        getch, getwch, getche, getwche,
        putch, putwch, ungetch, ungetwch,
        kbhit, setmode, open_osfhandle, get_osfhandle,
        locking, heapmin,
        SetErrorMode, CrtSetReportMode, CrtSetReportFile,
    )
    return all(callable(fn) for fn in expected)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    # constants
    "CRT_ASSEMBLY_VERSION",
    "O_RDONLY", "O_WRONLY", "O_RDWR", "O_APPEND", "O_CREAT", "O_TRUNC", "O_EXCL",
    "O_TEXT", "O_BINARY", "O_NOINHERIT", "O_TEMPORARY",
    "O_SHORT_LIVED", "O_OBTAIN_DIR", "O_RANDOM", "O_SEQUENTIAL",
    "LK_LOCK", "LK_NBLCK", "LK_NBRLCK", "LK_RLCK", "LK_UNLCK",
    "SEM_FAILCRITICALERRORS", "SEM_NOALIGNMENTFAULTEXCEPT",
    "SEM_NOGPFAULTERRORBOX", "SEM_NOOPENFILEERRORBOX",
    # functions
    "getch", "getwch", "getche", "getwche",
    "putch", "putwch", "ungetch", "ungetwch",
    "kbhit", "setmode", "open_osfhandle", "get_osfhandle",
    "locking", "heapmin",
    "SetErrorMode", "CrtSetReportMode", "CrtSetReportFile",
    # invariants
    "msvcrt2_constants", "msvcrt2_platform", "msvcrt2_functions",
]