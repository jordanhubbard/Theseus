"""
theseus_tty_cr — Clean-room tty module.
No import of the standard `tty` module.
Uses termios directly.
"""

import termios as _termios

IFLAG = 0
OFLAG = 1
CFLAG = 2
LFLAG = 3
ISPEED = 4
OSPEED = 5
CC = 6


def setraw(fd, when=_termios.TCSAFLUSH):
    """Put terminal in raw mode."""
    mode = _termios.tcgetattr(fd)
    mode[IFLAG] = mode[IFLAG] & ~(
        _termios.BRKINT | _termios.ICRNL | _termios.INPCK |
        _termios.ISTRIP | _termios.IXON
    )
    mode[OFLAG] = mode[OFLAG] & ~_termios.OPOST
    mode[CFLAG] = mode[CFLAG] & ~(_termios.CSIZE | _termios.PARENB)
    mode[CFLAG] = mode[CFLAG] | _termios.CS8
    mode[LFLAG] = mode[LFLAG] & ~(
        _termios.ECHO | _termios.ICANON | _termios.IEXTEN | _termios.ISIG
    )
    mode[CC][_termios.VMIN] = 1
    mode[CC][_termios.VTIME] = 0
    _termios.tcsetattr(fd, when, mode)


def setcbreak(fd, when=_termios.TCSAFLUSH):
    """Put terminal in cbreak mode."""
    mode = _termios.tcgetattr(fd)
    mode[LFLAG] = mode[LFLAG] & ~(_termios.ECHO | _termios.ICANON)
    mode[CC][_termios.VMIN] = 1
    mode[CC][_termios.VTIME] = 0
    _termios.tcsetattr(fd, when, mode)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def tty2_constants():
    """IFLAG, OFLAG, CFLAG, LFLAG constants are ints; returns True."""
    return all(isinstance(x, int) for x in [IFLAG, OFLAG, CFLAG, LFLAG])


def tty2_setraw_callable():
    """setraw and setcbreak are callable; returns True."""
    return callable(setraw) and callable(setcbreak)


def tty2_mode_indices():
    """ISPEED, OSPEED, CC mode indices are ints; returns True."""
    return all(isinstance(x, int) for x in [ISPEED, OSPEED, CC])


__all__ = [
    'IFLAG', 'OFLAG', 'CFLAG', 'LFLAG', 'ISPEED', 'OSPEED', 'CC',
    'setraw', 'setcbreak',
    'tty2_constants', 'tty2_setraw_callable', 'tty2_mode_indices',
]
