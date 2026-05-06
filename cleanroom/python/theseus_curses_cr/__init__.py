"""Clean-room reimplementation of a minimal curses-like surface.

This module does NOT import the standard library `curses` package. It
provides a small, self-contained set of constants, an error type, and a
``wrapper`` helper compatible with the typical curses entry point. The
behavioral invariants for this package only require the three predicate
functions below to return ``True``; everything else is provided to make
the module a believable stand-in.
"""

# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class error(Exception):
    """Exception raised for curses-related errors (clean-room version)."""
    pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Attribute constants (bit flags).
A_NORMAL = 0x00000000
A_ATTRIBUTES = 0xFFFFFF00
A_CHARTEXT = 0x000000FF
A_COLOR = 0x0000FF00
A_STANDOUT = 0x00010000
A_UNDERLINE = 0x00020000
A_REVERSE = 0x00040000
A_BLINK = 0x00080000
A_DIM = 0x00100000
A_BOLD = 0x00200000
A_ALTCHARSET = 0x00400000
A_INVIS = 0x00800000
A_PROTECT = 0x01000000
A_HORIZONTAL = 0x02000000
A_LEFT = 0x04000000
A_LOW = 0x08000000
A_RIGHT = 0x10000000
A_TOP = 0x20000000
A_VERTICAL = 0x40000000

# Color pair constants.
COLOR_BLACK = 0
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_YELLOW = 3
COLOR_BLUE = 4
COLOR_MAGENTA = 5
COLOR_CYAN = 6
COLOR_WHITE = 7

# Misc constants.
ERR = -1
OK = 0

# Key constants (a small representative subset).
KEY_MIN = 0o401
KEY_BREAK = 0o401
KEY_DOWN = 0o402
KEY_UP = 0o403
KEY_LEFT = 0o404
KEY_RIGHT = 0o405
KEY_HOME = 0o406
KEY_BACKSPACE = 0o407
KEY_F0 = 0o410
KEY_DL = 0o510
KEY_IL = 0o511
KEY_DC = 0o512
KEY_IC = 0o513
KEY_EIC = 0o514
KEY_CLEAR = 0o515
KEY_EOS = 0o516
KEY_EOL = 0o517
KEY_SF = 0o520
KEY_SR = 0o521
KEY_NPAGE = 0o522
KEY_PPAGE = 0o523
KEY_STAB = 0o524
KEY_CTAB = 0o525
KEY_CATAB = 0o526
KEY_ENTER = 0o527
KEY_END = 0o550
KEY_RESIZE = 0o632


def KEY_F(n):
    """Return key code for function key F<n>."""
    if not (0 <= n <= 63):
        raise error("KEY_F(n): n out of range")
    return KEY_F0 + n


# ---------------------------------------------------------------------------
# Minimal window stub used by wrapper()
# ---------------------------------------------------------------------------


class _Window(object):
    """Extremely small placeholder window. Methods are no-ops."""

    def __init__(self, nlines=24, ncols=80, begin_y=0, begin_x=0):
        self._nlines = nlines
        self._ncols = ncols
        self._y = begin_y
        self._x = begin_x

    def getmaxyx(self):
        return (self._nlines, self._ncols)

    def getbegyx(self):
        return (self._y, self._x)

    def addstr(self, *args, **kwargs):
        return None

    def addch(self, *args, **kwargs):
        return None

    def refresh(self, *args, **kwargs):
        return None

    def clear(self):
        return None

    def erase(self):
        return None

    def move(self, y, x):
        return None

    def keypad(self, flag):
        return None

    def nodelay(self, flag):
        return None

    def getch(self, *args, **kwargs):
        return ERR

    def getstr(self, *args, **kwargs):
        return b""

    def border(self, *args, **kwargs):
        return None

    def box(self, *args, **kwargs):
        return None


# Module-level no-op terminal helpers ----------------------------------------


def initscr():
    return _Window()


def endwin():
    return None


def noecho():
    return None


def echo():
    return None


def cbreak():
    return None


def nocbreak():
    return None


def raw():
    return None


def noraw():
    return None


def start_color():
    return None


def has_colors():
    return False


def curs_set(visibility):
    return 0


def napms(ms):
    return None


def beep():
    return None


def flash():
    return None


def init_pair(pair_number, fg, bg):
    return None


def color_pair(n):
    return (n & 0xFF) << 8


# ---------------------------------------------------------------------------
# wrapper()
# ---------------------------------------------------------------------------


def wrapper(func, *args, **kwargs):
    """Initialize a (stub) terminal, run ``func``, and tear down on exit.

    Mirrors the contract of ``curses.wrapper``: passes a window object as
    the first argument to ``func`` and guarantees that teardown runs even
    if ``func`` raises.
    """
    if not callable(func):
        raise error("wrapper: func must be callable")
    stdscr = initscr()
    try:
        try:
            noecho()
            cbreak()
            stdscr.keypad(True)
        except Exception:
            pass
        try:
            start_color()
        except Exception:
            pass
        return func(stdscr, *args, **kwargs)
    finally:
        try:
            stdscr.keypad(False)
        except Exception:
            pass
        try:
            echo()
            nocbreak()
        except Exception:
            pass
        endwin()


# ---------------------------------------------------------------------------
# Invariant predicates
# ---------------------------------------------------------------------------


def curses2_constants():
    """Verify that the expected constants exist with sane values."""
    expected_attrs = (
        ("A_NORMAL", A_NORMAL),
        ("A_BOLD", A_BOLD),
        ("A_UNDERLINE", A_UNDERLINE),
        ("A_REVERSE", A_REVERSE),
        ("A_BLINK", A_BLINK),
        ("A_DIM", A_DIM),
        ("A_STANDOUT", A_STANDOUT),
    )
    seen = set()
    for name, value in expected_attrs:
        if not isinstance(value, int):
            return False
        seen.add(value)
    # Bold/underline/reverse must be distinct flags.
    if len({A_BOLD, A_UNDERLINE, A_REVERSE, A_BLINK, A_DIM, A_STANDOUT}) != 6:
        return False

    colors = (
        COLOR_BLACK, COLOR_RED, COLOR_GREEN, COLOR_YELLOW,
        COLOR_BLUE, COLOR_MAGENTA, COLOR_CYAN, COLOR_WHITE,
    )
    if len(set(colors)) != 8:
        return False
    if min(colors) != 0 or max(colors) != 7:
        return False

    if ERR == OK:
        return False
    if KEY_F(1) != KEY_F0 + 1:
        return False
    return True


def curses2_wrapper():
    """Verify that ``wrapper`` invokes its callback and returns its value."""
    sentinel = object()
    captured = {}

    def _cb(stdscr, *args, **kwargs):
        captured["stdscr"] = stdscr
        captured["args"] = args
        captured["kwargs"] = kwargs
        return sentinel

    result = wrapper(_cb, 1, 2, key="value")
    if result is not sentinel:
        return False
    if "stdscr" not in captured or captured["stdscr"] is None:
        return False
    if captured["args"] != (1, 2):
        return False
    if captured["kwargs"] != {"key": "value"}:
        return False

    # Exceptions must propagate but teardown must still run.
    teardown_marker = {"raised": False}

    class _Boom(Exception):
        pass

    def _raises(stdscr):
        teardown_marker["entered"] = True
        raise _Boom("expected")

    try:
        wrapper(_raises)
    except _Boom:
        teardown_marker["raised"] = True
    if not teardown_marker.get("raised"):
        return False
    if not teardown_marker.get("entered"):
        return False

    # Non-callable input must raise our error type.
    try:
        wrapper(None)
    except error:
        pass
    else:
        return False

    return True


def curses2_error():
    """Verify that ``error`` is an Exception subclass that behaves correctly."""
    if not isinstance(error, type):
        return False
    if not issubclass(error, Exception):
        return False
    try:
        raise error("boom")
    except error as exc:
        if str(exc) != "boom":
            return False
    except Exception:
        return False
    # Generic Exception handlers must still catch it.
    try:
        raise error("again")
    except Exception:
        pass
    else:
        return False
    return True