"""
theseus_curses_cr — Clean-room curses module.
No import of the standard `curses` module.
Uses the underlying _curses C extension directly.
"""

import _curses as _c
import sys as _sys


# Re-export error class
error = _c.error

# Attribute constants
A_ALTCHARSET = _c.A_ALTCHARSET
A_ATTRIBUTES = _c.A_ATTRIBUTES
A_BLINK = _c.A_BLINK
A_BOLD = _c.A_BOLD
A_CHARTEXT = _c.A_CHARTEXT
A_COLOR = _c.A_COLOR
A_DIM = _c.A_DIM
A_INVIS = _c.A_INVIS
A_ITALIC = getattr(_c, 'A_ITALIC', 0x80000000)
A_NORMAL = getattr(_c, 'A_NORMAL', 0)
A_PROTECT = getattr(_c, 'A_PROTECT', 0)
A_REVERSE = _c.A_REVERSE
A_STANDOUT = _c.A_STANDOUT
A_UNDERLINE = _c.A_UNDERLINE

# Color constants
COLOR_BLACK = getattr(_c, 'COLOR_BLACK', 0)
COLOR_RED = getattr(_c, 'COLOR_RED', 1)
COLOR_GREEN = getattr(_c, 'COLOR_GREEN', 2)
COLOR_YELLOW = getattr(_c, 'COLOR_YELLOW', 3)
COLOR_BLUE = getattr(_c, 'COLOR_BLUE', 4)
COLOR_MAGENTA = getattr(_c, 'COLOR_MAGENTA', 5)
COLOR_CYAN = getattr(_c, 'COLOR_CYAN', 6)
COLOR_WHITE = getattr(_c, 'COLOR_WHITE', 7)

# Key constants
KEY_MIN = getattr(_c, 'KEY_MIN', 256)
KEY_MAX = getattr(_c, 'KEY_MAX', 511)

# Re-export core functions
initscr = _c.initscr
newwin = _c.newwin
endwin = _c.endwin
setupterm = getattr(_c, 'setupterm', None)
cbreak = _c.cbreak
nocbreak = _c.nocbreak
echo = _c.echo
noecho = _c.noecho
nl = _c.nl
nonl = _c.nonl
curs_set = _c.curs_set
color_pair = _c.color_pair
start_color = _c.start_color
use_default_colors = getattr(_c, 'use_default_colors', None)
init_pair = _c.init_pair
init_color = getattr(_c, 'init_color', None)
has_colors = _c.has_colors
can_change_color = getattr(_c, 'can_change_color', None)
napms = _c.napms
beep = _c.beep
flash = _c.flash
getsyx = getattr(_c, 'getsyx', None)
setsyx = getattr(_c, 'setsyx', None)
doupdate = _c.doupdate
raw = _c.raw
noraw = _c.noraw
qiflush = _c.qiflush
noqiflush = _c.noqiflush
intrflush = getattr(_c, 'intrflush', None)
meta = getattr(_c, 'meta', None)
keyname = _c.keyname
halfdelay = _c.halfdelay
getmouse = getattr(_c, 'getmouse', None)
mousemask = getattr(_c, 'mousemask', None)
ungetmouse = getattr(_c, 'ungetmouse', None)
resetty = getattr(_c, 'resetty', None)
savetty = getattr(_c, 'savetty', None)
tigetflag = getattr(_c, 'tigetflag', None)
tigetnum = getattr(_c, 'tigetnum', None)
tigetstr = getattr(_c, 'tigetstr', None)
tparm = getattr(_c, 'tparm', None)


def wrapper(func, *args, **kwds):
    """Initialize curses and call func(stdscr, *args, **kwds)."""
    try:
        stdscr = initscr()
        cbreak()
        noecho()
        try:
            start_color()
        except error:
            pass
        stdscr.keypad(True)
        return func(stdscr, *args, **kwds)
    finally:
        try:
            stdscr.keypad(False)
            echo()
            nocbreak()
        except error:
            pass
        endwin()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def curses2_constants():
    """curses attribute constants like A_BOLD are defined; returns True."""
    return (isinstance(A_BOLD, int) and
            isinstance(A_UNDERLINE, int) and
            isinstance(A_REVERSE, int) and
            isinstance(COLOR_BLACK, int) and
            COLOR_RED != COLOR_GREEN)


def curses2_wrapper():
    """wrapper() function exists and is callable; returns True."""
    return callable(wrapper)


def curses2_error():
    """error exception class exists; returns True."""
    return (issubclass(error, Exception) and
            error.__name__ == 'error')


__all__ = [
    'error', 'wrapper',
    'A_BOLD', 'A_DIM', 'A_BLINK', 'A_REVERSE', 'A_STANDOUT', 'A_UNDERLINE',
    'A_NORMAL', 'A_ALTCHARSET', 'A_ATTRIBUTES', 'A_CHARTEXT', 'A_COLOR',
    'A_INVIS', 'A_ITALIC', 'A_PROTECT',
    'COLOR_BLACK', 'COLOR_RED', 'COLOR_GREEN', 'COLOR_YELLOW',
    'COLOR_BLUE', 'COLOR_MAGENTA', 'COLOR_CYAN', 'COLOR_WHITE',
    'KEY_MIN', 'KEY_MAX',
    'initscr', 'newwin', 'endwin', 'cbreak', 'nocbreak', 'echo', 'noecho',
    'nl', 'nonl', 'raw', 'noraw', 'curs_set', 'color_pair',
    'start_color', 'init_pair', 'has_colors', 'napms', 'beep', 'flash',
    'doupdate', 'keyname', 'halfdelay',
    'curses2_constants', 'curses2_wrapper', 'curses2_error',
]
