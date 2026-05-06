"""Clean-room reimplementation of Python's tty module.

Provides terminal control mode indices and helpers (setraw/setcbreak)
without importing the standard-library tty module.
"""

# termios is a separate standard-library module (the C-level terminal
# interface); it is NOT the package being replaced here, so it is allowed.
try:
    import termios as _termios
except ImportError:  # pragma: no cover - non-POSIX platforms
    _termios = None


# ---------------------------------------------------------------------------
# Mode list indices
#
# tcgetattr() returns a list of seven items in the canonical order:
#   [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
# ---------------------------------------------------------------------------
IFLAG = 0
OFLAG = 1
CFLAG = 2
LFLAG = 3
ISPEED = 4
OSPEED = 5
CC = 6


# ---------------------------------------------------------------------------
# Re-export the relevant termios constants so callers that previously used
# `tty.<NAME>` keep working.  We copy them rather than star-importing in
# order to keep the surface area explicit.
# ---------------------------------------------------------------------------
def _import_termios_constants():
    if _termios is None:
        return
    g = globals()
    for _name in dir(_termios):
        if _name.startswith("_"):
            continue
        g.setdefault(_name, getattr(_termios, _name))


_import_termios_constants()


# Provide a reasonable default for TCSAFLUSH so the functions remain
# callable even on platforms where termios is unavailable (the call will
# fail at runtime, but importing the module will not).
if "TCSAFLUSH" not in globals():
    TCSAFLUSH = 2


# ---------------------------------------------------------------------------
# Helper accessors so we always reach for the *current* termios value
# (avoids stale-binding surprises if termios is monkey-patched in tests).
# ---------------------------------------------------------------------------
def _c(name, default=0):
    if _termios is None:
        return default
    return getattr(_termios, name, default)


# ---------------------------------------------------------------------------
# setraw / setcbreak
# ---------------------------------------------------------------------------
def setraw(fd, when=None):
    """Put terminal into raw mode."""
    if _termios is None:
        raise RuntimeError("termios is not available on this platform")
    if when is None:
        when = _c("TCSAFLUSH", 2)

    BRKINT = _c("BRKINT")
    ICRNL = _c("ICRNL")
    INPCK = _c("INPCK")
    ISTRIP = _c("ISTRIP")
    IXON = _c("IXON")
    OPOST = _c("OPOST")
    CSIZE = _c("CSIZE")
    PARENB = _c("PARENB")
    CS8 = _c("CS8")
    ECHO = _c("ECHO")
    ICANON = _c("ICANON")
    IEXTEN = _c("IEXTEN")
    ISIG = _c("ISIG")
    VMIN = _c("VMIN")
    VTIME = _c("VTIME")

    mode = _termios.tcgetattr(fd)
    mode[IFLAG] = mode[IFLAG] & ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON)
    mode[OFLAG] = mode[OFLAG] & ~OPOST
    mode[CFLAG] = mode[CFLAG] & ~(CSIZE | PARENB)
    mode[CFLAG] = mode[CFLAG] | CS8
    mode[LFLAG] = mode[LFLAG] & ~(ECHO | ICANON | IEXTEN | ISIG)
    mode[CC][VMIN] = 1
    mode[CC][VTIME] = 0
    _termios.tcsetattr(fd, when, mode)


def setcbreak(fd, when=None):
    """Put terminal into cbreak mode."""
    if _termios is None:
        raise RuntimeError("termios is not available on this platform")
    if when is None:
        when = _c("TCSAFLUSH", 2)

    ECHO = _c("ECHO")
    ICANON = _c("ICANON")
    VMIN = _c("VMIN")
    VTIME = _c("VTIME")

    mode = _termios.tcgetattr(fd)
    mode[LFLAG] = mode[LFLAG] & ~(ECHO | ICANON)
    mode[CC][VMIN] = 1
    mode[CC][VTIME] = 0
    _termios.tcsetattr(fd, when, mode)


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------
def tty2_constants():
    """All seven mode-list indices are exposed and distinct."""
    names = ("IFLAG", "OFLAG", "CFLAG", "LFLAG", "ISPEED", "OSPEED", "CC")
    g = globals()
    for n in names:
        if n not in g:
            return False
        v = g[n]
        if not isinstance(v, int):
            return False
    values = [g[n] for n in names]
    return len(set(values)) == len(values)


def tty2_setraw_callable():
    """setraw and setcbreak are callable functions."""
    return callable(setraw) and callable(setcbreak)


def tty2_mode_indices():
    """Mode-list indices match the canonical tcgetattr ordering."""
    return (
        IFLAG == 0
        and OFLAG == 1
        and CFLAG == 2
        and LFLAG == 3
        and ISPEED == 4
        and OSPEED == 5
        and CC == 6
    )


__all__ = [
    "IFLAG", "OFLAG", "CFLAG", "LFLAG", "ISPEED", "OSPEED", "CC",
    "setraw", "setcbreak",
    "tty2_constants", "tty2_setraw_callable", "tty2_mode_indices",
]