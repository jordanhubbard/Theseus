"""Clean-room subset of curses.ascii."""

NUL = 0
SOH = 1
STX = 2
ETX = 3
EOT = 4
ENQ = 5
ACK = 6
BEL = 7
BS = 8
TAB = HT = 9
LF = NL = 10
VT = 11
FF = 12
CR = 13
SO = 14
SI = 15
DLE = 16
DC1 = 17
DC2 = 18
DC3 = 19
DC4 = 20
NAK = 21
SYN = 22
ETB = 23
CAN = 24
EM = 25
SUB = 26
ESC = 27
FS = 28
GS = 29
RS = 30
US = 31
SP = 32
DEL = 127

controlnames = [
    "NUL", "SOH", "STX", "ETX", "EOT", "ENQ", "ACK", "BEL",
    "BS", "HT", "LF", "VT", "FF", "CR", "SO", "SI",
    "DLE", "DC1", "DC2", "DC3", "DC4", "NAK", "SYN", "ETB",
    "CAN", "EM", "SUB", "ESC", "FS", "GS", "RS", "US", "SP",
]


def _ord(c):
    if isinstance(c, int):
        return c
    if isinstance(c, bytes):
        if len(c) != 1:
            raise TypeError("expected a character or byte value")
        return c[0]
    if isinstance(c, str):
        if len(c) != 1:
            raise TypeError("expected a character or byte value")
        return ord(c)
    raise TypeError("expected a character or byte value")


def _same_type(c, value):
    value = value & 0xff
    if isinstance(c, str):
        return chr(value)
    if isinstance(c, bytes):
        return bytes([value])
    return value


def ascii(c):
    return _same_type(c, _ord(c) & 0x7f)


def ctrl(c):
    return _same_type(c, _ord(c) & 0x1f)


def alt(c):
    return _same_type(c, _ord(c) | 0x80)


def isascii(c):
    value = _ord(c)
    return 0 <= value <= 0x7f


def isdigit(c):
    value = _ord(c)
    return ord("0") <= value <= ord("9")


def isupper(c):
    value = _ord(c)
    return ord("A") <= value <= ord("Z")


def islower(c):
    value = _ord(c)
    return ord("a") <= value <= ord("z")


def isalpha(c):
    return isupper(c) or islower(c)


def isalnum(c):
    return isalpha(c) or isdigit(c)


def isblank(c):
    return _ord(c) in (TAB, SP)


def iscntrl(c):
    value = _ord(c)
    return 0 <= value <= 0x1f or value == DEL


def isctrl(c):
    value = _ord(c)
    return 0 <= value <= 0x1f


def isspace(c):
    return _ord(c) in (TAB, LF, VT, FF, CR, SP)


def isprint(c):
    value = _ord(c)
    return SP <= value <= 0x7e


def isgraph(c):
    value = _ord(c)
    return SP < value <= 0x7e


def ispunct(c):
    return isgraph(c) and not isalnum(c)


def isxdigit(c):
    value = _ord(c)
    return isdigit(value) or ord("A") <= value <= ord("F") or ord("a") <= value <= ord("f")


def ismeta(c):
    return _ord(c) >= 0x80


def unctrl(c):
    value = _ord(c)
    prefix = ""
    if value & 0x80:
        prefix = "!"
        value = value & 0x7f
    if value == DEL:
        return prefix + "^?"
    if 0 <= value <= 0x1f:
        return prefix + "^" + chr(value + 64)
    return prefix + chr(value)


def curses_ascii_digit():
    return isdigit("5") and not isdigit("x")


def curses_ascii_ctrl():
    return ctrl("A")


def curses_ascii_unctrl():
    return unctrl("\n")


def curses_ascii_constants():
    return ESC == 27 and SP == 32 and DEL == 127
