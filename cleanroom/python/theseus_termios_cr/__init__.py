"""
theseus_termios_cr — Clean-room termios module.

Pure clean-room reimplementation. Does NOT import the standard `termios`
module nor load its C extension. All constants are hard-coded from the
POSIX / Linux / Darwin termios.h headers, and the runtime functions are
implemented on top of `fcntl.ioctl` (a stdlib primitive that does not
itself live in `termios`).
"""

import os as _os
import sys as _sys
import struct as _struct

try:  # `fcntl` is POSIX-only; on Windows it simply isn't available.
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - non-POSIX platforms
    _fcntl = None


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

_PLATFORM = _sys.platform
_IS_LINUX = _PLATFORM.startswith("linux")
_IS_DARWIN = _PLATFORM == "darwin"
_IS_BSD = (
    _PLATFORM.startswith("freebsd")
    or _PLATFORM.startswith("openbsd")
    or _PLATFORM.startswith("netbsd")
)


# ---------------------------------------------------------------------------
# Constants
#
# Values come from the relevant <termios.h> / <bits/termios.h> headers
# (linux/asm-generic, glibc, darwin xnu, FreeBSD).  We pick a sane default
# per-platform; values default to the Linux/glibc set when the host platform
# is unknown.
# ---------------------------------------------------------------------------

if _IS_DARWIN or _IS_BSD:
    # ----- BSD / macOS layout (from <sys/termios.h>) ----------------------

    # tcsetattr "when" flags
    TCSANOW = 0
    TCSADRAIN = 1
    TCSAFLUSH = 2
    TCSASOFT = 0x10

    # tcflow / tcflush actions
    TCOOFF = 1
    TCOON = 2
    TCIOFF = 3
    TCION = 4
    TCIFLUSH = 1
    TCOFLUSH = 2
    TCIOFLUSH = 3

    # iflag
    IGNBRK = 0x00000001
    BRKINT = 0x00000002
    IGNPAR = 0x00000004
    PARMRK = 0x00000008
    INPCK = 0x00000010
    ISTRIP = 0x00000020
    INLCR = 0x00000040
    IGNCR = 0x00000080
    ICRNL = 0x00000100
    IXON = 0x00000200
    IXOFF = 0x00000400
    IXANY = 0x00000800
    IMAXBEL = 0x00002000

    # oflag
    OPOST = 0x00000001
    ONLCR = 0x00000002
    OXTABS = 0x00000004
    ONOEOT = 0x00000008
    OCRNL = 0x00000010
    ONOCR = 0x00000020
    ONLRET = 0x00000040
    OFDEL = 0x00020000

    # cflag
    CIGNORE = 0x00000001
    CSIZE = 0x00000300
    CS5 = 0x00000000
    CS6 = 0x00000100
    CS7 = 0x00000200
    CS8 = 0x00000300
    CSTOPB = 0x00000400
    CREAD = 0x00000800
    PARENB = 0x00001000
    PARODD = 0x00002000
    HUPCL = 0x00004000
    CLOCAL = 0x00008000

    # lflag
    ECHOKE = 0x00000001
    ECHOE = 0x00000002
    ECHOK = 0x00000004
    ECHO = 0x00000008
    ECHONL = 0x00000010
    ECHOPRT = 0x00000020
    ECHOCTL = 0x00000040
    ISIG = 0x00000080
    ICANON = 0x00000100
    ALTWERASE = 0x00000200
    IEXTEN = 0x00000400
    EXTPROC = 0x00000800
    TOSTOP = 0x00400000
    FLUSHO = 0x00800000
    NOKERNINFO = 0x02000000
    PENDIN = 0x20000000
    NOFLSH = 0x80000000

    # Baud rates (BSD encodes them as the literal speed)
    B0 = 0
    B50 = 50
    B75 = 75
    B110 = 110
    B134 = 134
    B150 = 150
    B200 = 200
    B300 = 300
    B600 = 600
    B1200 = 1200
    B1800 = 1800
    B2400 = 2400
    B4800 = 4800
    B9600 = 9600
    B19200 = 19200
    B38400 = 38400
    B57600 = 57600
    B115200 = 115200
    B230400 = 230400

    # Control characters indices (BSD uses NCCS == 20)
    VEOF = 0
    VEOL = 1
    VEOL2 = 2
    VERASE = 3
    VWERASE = 4
    VKILL = 5
    VREPRINT = 6
    VINTR = 8
    VQUIT = 9
    VSUSP = 10
    VDSUSP = 11
    VSTART = 12
    VSTOP = 13
    VLNEXT = 14
    VDISCARD = 15
    VMIN = 16
    VTIME = 17
    VSTATUS = 18

    NCCS = 20

    # ioctl request codes for tcgetattr/tcsetattr
    TIOCGETA = 0x402C7413
    TIOCSETA = 0x802C7414
    TIOCSETAW = 0x802C7415
    TIOCSETAF = 0x802C7416

else:
    # ----- Linux / glibc layout (from <bits/termios.h>) -------------------

    # tcsetattr "when" flags
    TCSANOW = 0
    TCSADRAIN = 1
    TCSAFLUSH = 2

    # tcflow / tcflush actions
    TCOOFF = 0
    TCOON = 1
    TCIOFF = 2
    TCION = 3
    TCIFLUSH = 0
    TCOFLUSH = 1
    TCIOFLUSH = 2

    # iflag
    IGNBRK = 0o000001
    BRKINT = 0o000002
    IGNPAR = 0o000004
    PARMRK = 0o000010
    INPCK = 0o000020
    ISTRIP = 0o000040
    INLCR = 0o000100
    IGNCR = 0o000200
    ICRNL = 0o000400
    IUCLC = 0o001000
    IXON = 0o002000
    IXANY = 0o004000
    IXOFF = 0o010000
    IMAXBEL = 0o020000
    IUTF8 = 0o040000

    # oflag
    OPOST = 0o000001
    OLCUC = 0o000002
    ONLCR = 0o000004
    OCRNL = 0o000010
    ONOCR = 0o000020
    ONLRET = 0o000040
    OFILL = 0o000100
    OFDEL = 0o000200
    NLDLY = 0o000400
    NL0 = 0o000000
    NL1 = 0o000400
    CRDLY = 0o003000
    CR0 = 0o000000
    CR1 = 0o001000
    CR2 = 0o002000
    CR3 = 0o003000
    TABDLY = 0o014000
    TAB0 = 0o000000
    TAB1 = 0o004000
    TAB2 = 0o010000
    TAB3 = 0o014000
    BSDLY = 0o020000
    BS0 = 0o000000
    BS1 = 0o020000
    FFDLY = 0o100000
    FF0 = 0o000000
    FF1 = 0o100000
    VTDLY = 0o040000
    VT0 = 0o000000
    VT1 = 0o040000

    # cflag
    CSIZE = 0o000060
    CS5 = 0o000000
    CS6 = 0o000020
    CS7 = 0o000040
    CS8 = 0o000060
    CSTOPB = 0o000100
    CREAD = 0o000200
    PARENB = 0o000400
    PARODD = 0o001000
    HUPCL = 0o002000
    CLOCAL = 0o004000

    # lflag
    ISIG = 0o000001
    ICANON = 0o000002
    ECHO = 0o000010
    ECHOE = 0o000020
    ECHOK = 0o000040
    ECHONL = 0o000100
    NOFLSH = 0o000200
    TOSTOP = 0o000400
    ECHOCTL = 0o001000
    ECHOPRT = 0o002000
    ECHOKE = 0o004000
    FLUSHO = 0o010000
    PENDIN = 0o040000
    IEXTEN = 0o100000
    EXTPROC = 0o200000

    # Baud rates (Linux uses small token codes)
    B0 = 0o000000
    B50 = 0o000001
    B75 = 0o000002
    B110 = 0o000003
    B134 = 0o000004
    B150 = 0o000005
    B200 = 0o000006
    B300 = 0o000007
    B600 = 0o000010
    B1200 = 0o000011
    B1800 = 0o000012
    B2400 = 0o000013
    B4800 = 0o000014
    B9600 = 0o000015
    B19200 = 0o000016
    B38400 = 0o000017
    B57600 = 0o010001
    B115200 = 0o010002
    B230400 = 0o010003
    B460800 = 0o010004
    B500000 = 0o010005
    B576000 = 0o010006
    B921600 = 0o010007
    B1000000 = 0o010010
    B1152000 = 0o010011
    B1500000 = 0o010012
    B2000000 = 0o010013
    B2500000 = 0o010014
    B3000000 = 0o010015
    B3500000 = 0o010016
    B4000000 = 0o010017

    CBAUD = 0o010017
    CBAUDEX = 0o010000

    # Control characters indices (Linux uses NCCS == 32)
    VINTR = 0
    VQUIT = 1
    VERASE = 2
    VKILL = 3
    VEOF = 4
    VTIME = 5
    VMIN = 6
    VSWTC = 7
    VSTART = 8
    VSTOP = 9
    VSUSP = 10
    VEOL = 11
    VREPRINT = 12
    VDISCARD = 13
    VWERASE = 14
    VLNEXT = 15
    VEOL2 = 16

    NCCS = 32

    # ioctl request codes
    TCGETS = 0x5401
    TCSETS = 0x5402
    TCSETSW = 0x5403
    TCSETSF = 0x5404
    TCSBRK = 0x5409
    TCXONC = 0x540A
    TCFLSH = 0x540B


# ---------------------------------------------------------------------------
# Exception type
# ---------------------------------------------------------------------------

class error(Exception):
    """Raised when a terminal operation fails — mirrors `termios.error`."""


# ---------------------------------------------------------------------------
# Runtime helpers
# ---------------------------------------------------------------------------

def _coerce_fd(fd):
    """Return an integer file descriptor for `fd` (which may be a file)."""
    if isinstance(fd, int):
        return fd
    if hasattr(fd, "fileno"):
        try:
            return int(fd.fileno())
        except Exception as exc:  # noqa: BLE001
            raise error("invalid file descriptor: " + str(exc))
    raise error("expected int or fileno()-providing object")


def _decode_attrs_linux(buf):
    """Decode a Linux struct termios buffer into the 7-tuple Python form."""
    if len(buf) < 17 + NCCS:
        raise error("termios buffer too small: " + str(len(buf)))
    iflag, oflag, cflag, lflag = _struct.unpack_from("IIII", buf, 0)
    cc_bytes = buf[17:17 + NCCS]
    cc_out = [bytes([b]) for b in cc_bytes]
    try:
        ispeed, ospeed = _struct.unpack_from("II", buf, 17 + NCCS)
    except _struct.error:
        ispeed = ospeed = 0
    if VMIN < len(cc_out):
        cc_out[VMIN] = cc_bytes[VMIN]
    if VTIME < len(cc_out):
        cc_out[VTIME] = cc_bytes[VTIME]
    return [iflag, oflag, cflag, lflag, ispeed, ospeed, cc_out]


def _decode_attrs_bsd(buf):
    """Decode a Darwin/BSD struct termios buffer."""
    flag_size = 8 if len(buf) >= 4 * 8 + NCCS + 2 * 8 else 4
    fmt = ("Q" if flag_size == 8 else "I") * 4
    iflag, oflag, cflag, lflag = _struct.unpack_from(fmt, buf, 0)
    cc_off = 4 * flag_size
    cc_bytes = buf[cc_off:cc_off + NCCS]
    cc_out = [bytes([b]) for b in cc_bytes]
    speed_fmt = ("Q" if flag_size == 8 else "I") * 2
    try:
        ispeed, ospeed = _struct.unpack_from(speed_fmt, buf, cc_off + NCCS)
    except _struct.error:
        ispeed = ospeed = 0
    if VMIN < len(cc_out):
        cc_out[VMIN] = cc_bytes[VMIN]
    if VTIME < len(cc_out):
        cc_out[VTIME] = cc_bytes[VTIME]
    return [iflag, oflag, cflag, lflag, ispeed, ospeed, cc_out]


def _encode_attrs_linux(attrs):
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = attrs
    buf = bytearray(_struct.pack("IIII", iflag & 0xFFFFFFFF,
                                 oflag & 0xFFFFFFFF,
                                 cflag & 0xFFFFFFFF,
                                 lflag & 0xFFFFFFFF))
    buf.append(0)  # c_line
    cc_bytes = bytearray(NCCS)
    for i, ch in enumerate(cc[:NCCS]):
        if isinstance(ch, (bytes, bytearray)):
            cc_bytes[i] = ch[0] if len(ch) else 0
        else:
            cc_bytes[i] = int(ch) & 0xFF
    buf.extend(cc_bytes)
    buf.extend(_struct.pack("II", ispeed & 0xFFFFFFFF, ospeed & 0xFFFFFFFF))
    return bytes(buf)


def _encode_attrs_bsd(attrs):
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = attrs
    flag_size = 8  # assume LP64
    fmt = ("Q" if flag_size == 8 else "I") * 4
    buf = bytearray(_struct.pack(fmt, iflag, oflag, cflag, lflag))
    cc_bytes = bytearray(NCCS)
    for i, ch in enumerate(cc[:NCCS]):
        if isinstance(ch, (bytes, bytearray)):
            cc_bytes[i] = ch[0] if len(ch) else 0
        else:
            cc_bytes[i] = int(ch) & 0xFF
    buf.extend(cc_bytes)
    speed_fmt = ("Q" if flag_size == 8 else "I") * 2
    buf.extend(_struct.pack(speed_fmt, ispeed, ospeed))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tcgetattr(fd):
    """Return the terminal attributes for `fd` as a 7-element list."""
    fd = _coerce_fd(fd)
    if _fcntl is None:
        raise error("fcntl not available on this platform")
    if _IS_LINUX:
        buf = bytearray(60)
        try:
            res = _fcntl.ioctl(fd, TCGETS, bytes(buf))
        except OSError as exc:
            raise error(exc.errno, exc.strerror)
        return _decode_attrs_linux(res)
    if _IS_DARWIN or _IS_BSD:
        buf = bytearray(72)
        try:
            res = _fcntl.ioctl(fd, TIOCGETA, bytes(buf))
        except OSError as exc:
            raise error(exc.errno, exc.strerror)
        return _decode_attrs_bsd(res)
    raise error("tcgetattr: unsupported platform " + _PLATFORM)


def tcsetattr(fd, when, attributes):
    """Set the terminal attributes for `fd` from a 7-element list."""
    fd = _coerce_fd(fd)
    if _fcntl is None:
        raise error("fcntl not available on this platform")
    if not (isinstance(attributes, (list, tuple)) and len(attributes) == 7):
        raise error("attributes must be a 7-element list")
    if _IS_LINUX:
        request = {TCSANOW: TCSETS,
                   TCSADRAIN: TCSETSW,
                   TCSAFLUSH: TCSETSF}.get(when)
        if request is None:
            raise error("invalid 'when' argument: " + repr(when))
        encoded = _encode_attrs_linux(attributes)
        try:
            _fcntl.ioctl(fd, request, encoded)
        except OSError as exc:
            raise error(exc.errno, exc.strerror)
        return None
    if _IS_DARWIN or _IS_BSD:
        request = {TCSANOW: TIOCSETA,
                   TCSADRAIN: TIOCSETAW,
                   TCSAFLUSH: TIOCSETAF}.get(when)
        if request is None:
            raise error("invalid 'when' argument: " + repr(when))
        encoded = _encode_attrs_bsd(attributes)
        try:
            _fcntl.ioctl(fd, request, encoded)
        except OSError as exc:
            raise error(exc.errno, exc.strerror)
        return None
    raise error("tcsetattr: unsupported platform " + _PLATFORM)


def tcsendbreak(fd, duration):
    fd = _coerce_fd(fd)
    if _fcntl is None:
        raise error("fcntl not available on this platform")
    if _IS_LINUX:
        try:
            _fcntl.ioctl(fd, TCSBRK, int(duration))
        except OSError as exc:
            raise error(exc.errno, exc.strerror)
        return None
    raise error("tcsendbreak: unsupported platform " + _PLATFORM)


def tcdrain(fd):
    fd = _coerce_fd(fd)
    if _fcntl is None:
        raise error("fcntl not available on this platform")
    if _IS_LINUX:
        try:
            _fcntl.ioctl(fd, TCSBRK, 1)
        except OSError as exc:
            raise error(exc.errno, exc.strerror)
        return None
    raise error("tcdrain: unsupported platform " + _PLATFORM)


def tcflush(fd, queue):
    fd = _coerce_fd(fd)
    if _fcntl is None:
        raise error("fcntl not available on this platform")
    if _IS_LINUX:
        try:
            _fcntl.ioctl(fd, TCFLSH, int(queue))
        except OSError as exc:
            raise error(exc.errno, exc.strerror)
        return None
    raise error("tcflush: unsupported platform " + _PLATFORM)


def tcflow(fd, action):
    fd = _coerce_fd(fd)
    if _fcntl is None:
        raise error("fcntl not available on this platform")
    if _IS_LINUX:
        try:
            _fcntl.ioctl(fd, TCXONC, int(action))
        except OSError as exc:
            raise error(exc.errno, exc.strerror)
        return None
    raise error("tcflow: unsupported platform " + _PLATFORM)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def termios2_constants():
    """TCSANOW, TCSADRAIN, TCSAFLUSH constants exist; returns True."""
    return (
        isinstance(TCSANOW, int)
        and isinstance(TCSADRAIN, int)
        and isinstance(TCSAFLUSH, int)
        and TCSANOW != TCSADRAIN
        and TCSADRAIN != TCSAFLUSH
    )


def termios2_baud_rates():
    """B0, B9600, B115200 baud rate constants exist; returns True."""
    return (
        isinstance(B0, int)
        and isinstance(B9600, int)
        and isinstance(B115200, int)
        and B0 >= 0
        and B9600 > 0
        and B115200 > 0
    )


def termios2_tcgetattr():
    """tcgetattr() function exists and is callable; returns True."""
    return callable(tcgetattr)


__all__ = [
    "TCSANOW", "TCSADRAIN", "TCSAFLUSH",
    "TCIFLUSH", "TCOFLUSH", "TCIOFLUSH",
    "TCOOFF", "TCOON", "TCIOFF", "TCION",
    "B0", "B50", "B75", "B110", "B134", "B150", "B200", "B300",
    "B600", "B1200", "B1800", "B2400", "B4800", "B9600", "B19200",
    "B38400", "B57600", "B115200", "B230400",
    "IGNBRK", "BRKINT", "IGNPAR", "PARMRK", "INPCK", "ISTRIP",
    "INLCR", "IGNCR", "ICRNL", "IXON", "IXOFF", "IXANY",
    "OPOST", "ONLCR", "OCRNL", "ONOCR", "ONLRET", "OFDEL",
    "CSIZE", "CS5", "CS6", "CS7", "CS8", "CSTOPB", "CREAD",
    "PARENB", "PARODD", "HUPCL", "CLOCAL",
    "ISIG", "ICANON", "ECHO", "ECHOE", "ECHOK", "ECHONL",
    "NOFLSH", "TOSTOP", "IEXTEN",
    "VINTR", "VQUIT", "VERASE", "VKILL", "VEOF", "VTIME",
    "VMIN", "VSTART", "VSTOP", "VSUSP", "VEOL",
    "VREPRINT", "VDISCARD", "VWERASE", "VLNEXT", "VEOL2",
    "NCCS",
    "error",
    "tcgetattr", "tcsetattr", "tcsendbreak",
    "tcdrain", "tcflush", "tcflow",
    "termios2_constants", "termios2_baud_rates", "termios2_tcgetattr",
]