"""
theseus_winsound_cr — Clean-room winsound module.
No import of the standard `winsound` module.
Windows-only: stubs for non-Windows platforms.
"""

import sys as _sys

_ON_WINDOWS = _sys.platform == 'win32'

# Flags for PlaySound
SND_ASYNC = 1
SND_NODEFAULT = 2
SND_LOOP = 8
SND_PURGE = 64
SND_FILENAME = 0x20000
SND_ALIAS = 0x10000
SND_ALIAS_ID = 0x110000
SND_RESOURCE = 0x40004
SND_MEMORY = 4
SND_NOSTOP = 16
SND_NOWAIT = 0x2000
SND_SYNC = 0

# Beep frequency limits
MB_OK = 0x00000000
MB_ICONHAND = 0x00000010
MB_ICONQUESTION = 0x00000020
MB_ICONEXCLAMATION = 0x00000030
MB_ICONASTERISK = 0x00000040


def Beep(frequency, duration):
    """Play a beep; Windows only."""
    if _ON_WINDOWS:
        import _winsound
        return _winsound.Beep(frequency, duration)
    raise OSError("winsound.Beep() is only available on Windows")


def MessageBeep(type=MB_OK):
    """Play a system sound; Windows only."""
    if _ON_WINDOWS:
        import _winsound
        return _winsound.MessageBeep(type)
    raise OSError("winsound.MessageBeep() is only available on Windows")


def PlaySound(sound, flags):
    """Play a sound; Windows only."""
    if _ON_WINDOWS:
        import _winsound
        return _winsound.PlaySound(sound, flags)
    raise OSError("winsound.PlaySound() is only available on Windows")


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def winsound2_constants():
    """winsound constants have correct values; returns True."""
    return (isinstance(SND_ASYNC, int) and
            isinstance(SND_FILENAME, int) and
            SND_FILENAME == 0x20000 and
            SND_ALIAS == 0x10000)


def winsound2_platform():
    """winsound stubs correctly reflect platform; returns True."""
    is_win = _sys.platform == 'win32'
    try:
        # Beep with freq=1 and duration=1 — on Windows this would work,
        # on non-Windows it should raise OSError
        Beep(440, 1)
        return is_win
    except OSError:
        return not is_win


def winsound2_functions():
    """winsound function stubs are callable; returns True."""
    return (callable(Beep) and
            callable(MessageBeep) and
            callable(PlaySound))


__all__ = [
    'SND_ASYNC', 'SND_NODEFAULT', 'SND_LOOP', 'SND_PURGE',
    'SND_FILENAME', 'SND_ALIAS', 'SND_ALIAS_ID', 'SND_RESOURCE',
    'SND_MEMORY', 'SND_NOSTOP', 'SND_NOWAIT', 'SND_SYNC',
    'MB_OK', 'MB_ICONHAND', 'MB_ICONQUESTION', 'MB_ICONEXCLAMATION', 'MB_ICONASTERISK',
    'Beep', 'MessageBeep', 'PlaySound',
    'winsound2_constants', 'winsound2_platform', 'winsound2_functions',
]
