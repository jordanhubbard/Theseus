"""
theseus_winsound_cr — Clean-room winsound module.

No import of the standard `winsound` module or its C backend `_winsound`.
On Windows, the functions are best-effort no-ops (they accept the call and
return None) so that callers don't fail with OSError. On non-Windows
platforms they raise OSError, mirroring the original module's behavior of
being unavailable off Windows.
"""

import sys as _sys

_ON_WINDOWS = _sys.platform == 'win32'

# ---------------------------------------------------------------------------
# Flags for PlaySound
# ---------------------------------------------------------------------------
SND_SYNC = 0
SND_ASYNC = 1
SND_NODEFAULT = 2
SND_MEMORY = 4
SND_LOOP = 8
SND_NOSTOP = 16
SND_PURGE = 64
SND_NOWAIT = 0x2000
SND_ALIAS = 0x10000
SND_FILENAME = 0x20000
SND_RESOURCE = 0x40004
SND_ALIAS_ID = 0x110000

# ---------------------------------------------------------------------------
# MessageBeep types
# ---------------------------------------------------------------------------
MB_OK = 0x00000000
MB_ICONHAND = 0x00000010
MB_ICONQUESTION = 0x00000020
MB_ICONEXCLAMATION = 0x00000030
MB_ICONASTERISK = 0x00000040


# ---------------------------------------------------------------------------
# Public API — clean-room stubs (no underlying platform imports)
# ---------------------------------------------------------------------------
def Beep(frequency, duration):
    """Play a beep tone; Windows only.

    Clean-room: we cannot actually emit audio without the standard winsound
    module, so on Windows this is a validated no-op. On non-Windows
    platforms, raise OSError to mirror the original module's unavailability.
    """
    if not isinstance(frequency, int) or not isinstance(duration, int):
        raise TypeError("frequency and duration must be integers")
    if frequency < 37 or frequency > 32767:
        raise ValueError("frequency must be between 37 and 32767")
    if duration < 0:
        raise ValueError("duration must be non-negative")
    if not _ON_WINDOWS:
        raise OSError("Beep() is only available on Windows")
    return None


def MessageBeep(type=MB_OK):
    """Play a system sound; Windows only.

    Clean-room no-op on Windows; raises OSError elsewhere.
    """
    if not isinstance(type, int):
        raise TypeError("type must be an integer")
    if not _ON_WINDOWS:
        raise OSError("MessageBeep() is only available on Windows")
    return None


def PlaySound(sound, flags):
    """Play a sound; Windows only.

    Clean-room no-op on Windows; raises OSError elsewhere.
    """
    if sound is not None and not isinstance(sound, (str, bytes)):
        raise TypeError("sound must be a string, bytes, or None")
    if not isinstance(flags, int):
        raise TypeError("flags must be an integer")
    if not _ON_WINDOWS:
        raise OSError("PlaySound() is only available on Windows")
    return None


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------
def winsound2_constants():
    """winsound constants have correct values; returns True."""
    return (
        isinstance(SND_ASYNC, int)
        and isinstance(SND_FILENAME, int)
        and SND_SYNC == 0
        and SND_ASYNC == 1
        and SND_NODEFAULT == 2
        and SND_MEMORY == 4
        and SND_LOOP == 8
        and SND_NOSTOP == 16
        and SND_PURGE == 64
        and SND_NOWAIT == 0x2000
        and SND_ALIAS == 0x10000
        and SND_FILENAME == 0x20000
        and SND_RESOURCE == 0x40004
        and SND_ALIAS_ID == 0x110000
        and MB_OK == 0
        and MB_ICONHAND == 0x10
        and MB_ICONQUESTION == 0x20
        and MB_ICONEXCLAMATION == 0x30
        and MB_ICONASTERISK == 0x40
    )


def winsound2_platform():
    """winsound stubs correctly reflect platform; returns True."""
    is_win = _sys.platform == 'win32'
    try:
        Beep(440, 1)
        # No exception from Beep -> we are on Windows.
        return is_win
    except OSError:
        # OSError -> our stub said this isn't Windows.
        return not is_win
    except Exception:
        # Any other exception (e.g. ValueError) shouldn't happen with
        # these args, but treat it as a platform-mismatch failure.
        return False


def winsound2_functions():
    """winsound function stubs are callable; returns True."""
    return (
        callable(Beep)
        and callable(MessageBeep)
        and callable(PlaySound)
    )


__all__ = [
    'SND_SYNC', 'SND_ASYNC', 'SND_NODEFAULT', 'SND_MEMORY',
    'SND_LOOP', 'SND_NOSTOP', 'SND_PURGE', 'SND_NOWAIT',
    'SND_ALIAS', 'SND_FILENAME', 'SND_RESOURCE', 'SND_ALIAS_ID',
    'MB_OK', 'MB_ICONHAND', 'MB_ICONQUESTION',
    'MB_ICONEXCLAMATION', 'MB_ICONASTERISK',
    'Beep', 'MessageBeep', 'PlaySound',
    'winsound2_constants', 'winsound2_platform', 'winsound2_functions',
]