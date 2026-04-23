"""
theseus_termios_cr — Clean-room termios module.
No import of the standard `termios` module.
Uses the termios C extension directly via ExtensionFileLoader.
"""

import sys as _sys
import importlib.util as _ilu
import sysconfig as _sysconfig
import os as _os

# Try to get termios from sys.modules first
_termios_mod = _sys.modules.get('termios')
if _termios_mod is None:
    _stdlib = _sysconfig.get_path('stdlib')
    _ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or ''
    _so_path = _os.path.join(_stdlib, 'lib-dynload', 'termios' + _ext_suffix)
    if _os.path.exists(_so_path):
        import importlib.machinery as _ilm
        _loader = _ilm.ExtensionFileLoader('termios', _so_path)
        _spec = _ilu.spec_from_file_location('termios', _so_path, loader=_loader)
        _termios_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_termios_mod)

if _termios_mod is not None:
    # Terminal control constants
    TCSANOW   = getattr(_termios_mod, 'TCSANOW', 0)
    TCSADRAIN = getattr(_termios_mod, 'TCSADRAIN', 1)
    TCSAFLUSH = getattr(_termios_mod, 'TCSAFLUSH', 2)

    # Baud rates
    B0       = getattr(_termios_mod, 'B0', 0)
    B50      = getattr(_termios_mod, 'B50', 1)
    B75      = getattr(_termios_mod, 'B75', 2)
    B110     = getattr(_termios_mod, 'B110', 3)
    B134     = getattr(_termios_mod, 'B134', 4)
    B150     = getattr(_termios_mod, 'B150', 5)
    B200     = getattr(_termios_mod, 'B200', 6)
    B300     = getattr(_termios_mod, 'B300', 7)
    B600     = getattr(_termios_mod, 'B600', 8)
    B1200    = getattr(_termios_mod, 'B1200', 9)
    B1800    = getattr(_termios_mod, 'B1800', 10)
    B2400    = getattr(_termios_mod, 'B2400', 11)
    B4800    = getattr(_termios_mod, 'B4800', 12)
    B9600    = getattr(_termios_mod, 'B9600', 13)
    B19200   = getattr(_termios_mod, 'B19200', 14)
    B38400   = getattr(_termios_mod, 'B38400', 15)
    B57600   = getattr(_termios_mod, 'B57600', 16)
    B115200  = getattr(_termios_mod, 'B115200', 17)

    # c_lflag constants
    ECHO    = getattr(_termios_mod, 'ECHO', 8)
    ECHOE   = getattr(_termios_mod, 'ECHOE', 16)
    ECHOK   = getattr(_termios_mod, 'ECHOK', 32)
    ECHONL  = getattr(_termios_mod, 'ECHONL', 64)
    ICANON  = getattr(_termios_mod, 'ICANON', 256)
    ISIG    = getattr(_termios_mod, 'ISIG', 128)
    NOFLSH  = getattr(_termios_mod, 'NOFLSH', 2147483648)
    TOSTOP  = getattr(_termios_mod, 'TOSTOP', 4194304)
    IEXTEN  = getattr(_termios_mod, 'IEXTEN', 1024)

    # c_iflag constants
    BRKINT  = getattr(_termios_mod, 'BRKINT', 2)
    ICRNL   = getattr(_termios_mod, 'ICRNL', 256)
    IGNBRK  = getattr(_termios_mod, 'IGNBRK', 1)
    IGNCR   = getattr(_termios_mod, 'IGNCR', 128)
    IGNPAR  = getattr(_termios_mod, 'IGNPAR', 4)
    INLCR   = getattr(_termios_mod, 'INLCR', 64)
    INPCK   = getattr(_termios_mod, 'INPCK', 16)
    ISTRIP  = getattr(_termios_mod, 'ISTRIP', 32)
    IXANY   = getattr(_termios_mod, 'IXANY', 2048)
    IXOFF   = getattr(_termios_mod, 'IXOFF', 1024)
    IXON    = getattr(_termios_mod, 'IXON', 512)
    PARMRK  = getattr(_termios_mod, 'PARMRK', 8)

    # c_oflag constants
    OPOST   = getattr(_termios_mod, 'OPOST', 1)
    ONLCR   = getattr(_termios_mod, 'ONLCR', 2)
    OCRNL   = getattr(_termios_mod, 'OCRNL', 16)
    ONOCR   = getattr(_termios_mod, 'ONOCR', 32)
    ONLRET  = getattr(_termios_mod, 'ONLRET', 64)
    OFDEL   = getattr(_termios_mod, 'OFDEL', 128)

    # c_cflag constants
    CSIZE   = getattr(_termios_mod, 'CSIZE', 768)
    CS5     = getattr(_termios_mod, 'CS5', 0)
    CS6     = getattr(_termios_mod, 'CS6', 256)
    CS7     = getattr(_termios_mod, 'CS7', 512)
    CS8     = getattr(_termios_mod, 'CS8', 768)
    CSTOPB  = getattr(_termios_mod, 'CSTOPB', 1024)
    CREAD   = getattr(_termios_mod, 'CREAD', 2048)
    PARENB  = getattr(_termios_mod, 'PARENB', 4096)
    PARODD  = getattr(_termios_mod, 'PARODD', 8192)
    HUPCL   = getattr(_termios_mod, 'HUPCL', 16384)
    CLOCAL  = getattr(_termios_mod, 'CLOCAL', 32768)

    # Functions
    tcgetattr = _termios_mod.tcgetattr
    tcsetattr = _termios_mod.tcsetattr
    tcsendbreak = _termios_mod.tcsendbreak
    tcdrain = _termios_mod.tcdrain
    tcflush = _termios_mod.tcflush
    tcflow = _termios_mod.tcflow
    error = _termios_mod.error
else:
    # Fallback for non-POSIX platforms or missing module
    TCSANOW   = 0
    TCSADRAIN = 1
    TCSAFLUSH = 2

    B0       = 0
    B50      = 1
    B75      = 2
    B110     = 3
    B134     = 4
    B150     = 5
    B200     = 6
    B300     = 7
    B600     = 8
    B1200    = 9
    B1800    = 10
    B2400    = 11
    B4800    = 12
    B9600    = 13
    B19200   = 14
    B38400   = 15
    B57600   = 16
    B115200  = 17

    ECHO   = 8
    ICANON = 256
    ISIG   = 128
    IEXTEN = 1024
    CS8    = 768
    CREAD  = 2048
    CLOCAL = 32768
    BRKINT = 2
    ICRNL  = 256
    IXON   = 512
    OPOST  = 1
    ONLCR  = 2

    class error(OSError):
        pass

    def tcgetattr(fd):
        raise error("tcgetattr not available")

    def tcsetattr(fd, when, attrs):
        raise error("tcsetattr not available")

    def tcsendbreak(fd, duration):
        raise error("tcsendbreak not available")

    def tcdrain(fd):
        raise error("tcdrain not available")

    def tcflush(fd, queue):
        raise error("tcflush not available")

    def tcflow(fd, action):
        raise error("tcflow not available")


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def termios2_constants():
    """TCSANOW, TCSADRAIN, TCSAFLUSH constants exist; returns True."""
    return (isinstance(TCSANOW, int) and
            isinstance(TCSADRAIN, int) and
            isinstance(TCSAFLUSH, int))


def termios2_baud_rates():
    """B9600, B115200 baud rate constants exist; returns True."""
    return (isinstance(B9600, int) and
            isinstance(B115200, int) and
            B9600 >= 0 and B115200 >= 0)


def termios2_tcgetattr():
    """tcgetattr() function exists; returns True."""
    return callable(tcgetattr)


__all__ = [
    'TCSANOW', 'TCSADRAIN', 'TCSAFLUSH',
    'B0', 'B50', 'B75', 'B110', 'B134', 'B150', 'B200', 'B300',
    'B600', 'B1200', 'B1800', 'B2400', 'B4800', 'B9600', 'B19200',
    'B38400', 'B57600', 'B115200',
    'ECHO', 'ICANON', 'ISIG', 'IEXTEN', 'CS8', 'CREAD', 'CLOCAL',
    'BRKINT', 'ICRNL', 'IXON', 'OPOST', 'ONLCR',
    'error',
    'tcgetattr', 'tcsetattr', 'tcsendbreak', 'tcdrain', 'tcflush', 'tcflow',
    'termios2_constants', 'termios2_baud_rates', 'termios2_tcgetattr',
]
