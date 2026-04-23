"""
theseus_msvcrt_cr — Clean-room msvcrt module.
No import of the standard `msvcrt` module.
Windows-only: stubs for non-Windows platforms.
"""

import sys as _sys

_ON_WINDOWS = _sys.platform == 'win32'

# CRT assembly version constant
CRT_ASSEMBLY_VERSION = '14.0.0.0'

# File translation mode constants
O_TEXT = 0x4000
O_BINARY = 0x8000
O_NOINHERIT = 0x0080
O_TEMPORARY = 0x0040
O_RDONLY = 0x0000
O_WRONLY = 0x0001
O_RDWR = 0x0002
O_APPEND = 0x0008
O_CREAT = 0x0100
O_TRUNC = 0x0200
O_EXCL = 0x0400


def getch():
    """Read a keypress from console; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.getch()
    raise OSError("msvcrt.getch() is only available on Windows")


def getwch():
    """Read a wide keypress from console; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.getwch()
    raise OSError("msvcrt.getwch() is only available on Windows")


def getche():
    """Read a keypress and echo it; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.getche()
    raise OSError("msvcrt.getche() is only available on Windows")


def putch(char):
    """Print char to console without newline; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.putch(char)
    raise OSError("msvcrt.putch() is only available on Windows")


def putwch(char):
    """Print wide char to console; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.putwch(char)
    raise OSError("msvcrt.putwch() is only available on Windows")


def ungetch(char):
    """Push char back into input buffer; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.ungetch(char)
    raise OSError("msvcrt.ungetch() is only available on Windows")


def kbhit():
    """Return True if a keypress is waiting; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.kbhit()
    return False


def setmode(fd, flags):
    """Set file descriptor translation mode; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.setmode(fd, flags)
    raise OSError("msvcrt.setmode() is only available on Windows")


def open_osfhandle(osfhandle, flags):
    """Create C runtime fd from OS file handle; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.open_osfhandle(osfhandle, flags)
    raise OSError("msvcrt.open_osfhandle() is only available on Windows")


def get_osfhandle(fd):
    """Return OS file handle for C runtime fd; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.get_osfhandle(fd)
    raise OSError("msvcrt.get_osfhandle() is only available on Windows")


def locking(fd, mode, nbytes):
    """Lock/unlock file region; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.locking(fd, mode, nbytes)
    raise OSError("msvcrt.locking() is only available on Windows")


def heapmin():
    """Minimize heap memory usage; Windows only."""
    if _ON_WINDOWS:
        import _msvcrt
        return _msvcrt.heapmin()
    raise OSError("msvcrt.heapmin() is only available on Windows")


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def msvcrt2_constants():
    """msvcrt constants have correct types; returns True."""
    return (isinstance(CRT_ASSEMBLY_VERSION, str) and
            isinstance(O_TEXT, int) and
            isinstance(O_BINARY, int))


def msvcrt2_platform():
    """msvcrt stubs correctly reflect platform; returns True."""
    is_win = _sys.platform == 'win32'
    # kbhit() returns False (no keypress) on non-Windows, bool on Windows
    result = kbhit()
    if is_win:
        return isinstance(result, bool)
    else:
        # getch() must raise OSError on non-Windows
        try:
            getch()
            return False
        except OSError:
            return result is False


def msvcrt2_functions():
    """msvcrt function stubs are callable; returns True."""
    return (callable(getch) and
            callable(putch) and
            callable(kbhit) and
            callable(setmode))


__all__ = [
    'CRT_ASSEMBLY_VERSION',
    'O_TEXT', 'O_BINARY', 'O_NOINHERIT', 'O_TEMPORARY',
    'O_RDONLY', 'O_WRONLY', 'O_RDWR', 'O_APPEND', 'O_CREAT', 'O_TRUNC', 'O_EXCL',
    'getch', 'getwch', 'getche', 'putch', 'putwch', 'ungetch',
    'kbhit', 'setmode', 'open_osfhandle', 'get_osfhandle',
    'locking', 'heapmin',
    'msvcrt2_constants', 'msvcrt2_platform', 'msvcrt2_functions',
]
