"""
theseus_syslog_cr — Clean-room reimplementation of Python's `syslog` module.

This implementation does NOT import or wrap the standard library's `syslog`
module (or its underlying C extension). It speaks the BSD syslog wire
protocol (RFC 3164) directly over a Unix-domain datagram socket connected
to a local syslog daemon (e.g. /dev/log, /var/run/syslog), with a graceful
no-op fallback when no daemon is reachable so that the module remains
importable and usable in sandboxed test environments.

Only Python standard-library built-ins are used (socket, os, time, sys).
"""

import os as _os
import sys as _sys
import time as _time
import socket as _socket


# ---------------------------------------------------------------------------
# Priority levels (RFC 3164 / RFC 5424 — severity codes 0..7)
# ---------------------------------------------------------------------------
LOG_EMERG    = 0
LOG_ALERT    = 1
LOG_CRIT     = 2
LOG_ERR      = 3
LOG_WARNING  = 4
LOG_NOTICE   = 5
LOG_INFO     = 6
LOG_DEBUG    = 7

# ---------------------------------------------------------------------------
# openlog() option flags
# ---------------------------------------------------------------------------
LOG_PID      = 0x01
LOG_CONS     = 0x02
LOG_ODELAY   = 0x04
LOG_NDELAY   = 0x08
LOG_NOWAIT   = 0x10
LOG_PERROR   = 0x20

# ---------------------------------------------------------------------------
# Facility codes (already pre-shifted by 3 bits, matching the C/Python API)
# ---------------------------------------------------------------------------
LOG_KERN     =  0 << 3   #  0
LOG_USER     =  1 << 3   #  8
LOG_MAIL     =  2 << 3   # 16
LOG_DAEMON   =  3 << 3   # 24
LOG_AUTH     =  4 << 3   # 32
LOG_SYSLOG   =  5 << 3   # 40
LOG_LPR      =  6 << 3   # 48
LOG_NEWS     =  7 << 3   # 56
LOG_UUCP     =  8 << 3   # 64
LOG_CRON     =  9 << 3   # 72
LOG_AUTHPRIV = 10 << 3   # 80
LOG_FTP      = 11 << 3   # 88

LOG_LOCAL0   = 16 << 3   # 128
LOG_LOCAL1   = 17 << 3   # 136
LOG_LOCAL2   = 18 << 3   # 144
LOG_LOCAL3   = 19 << 3   # 152
LOG_LOCAL4   = 20 << 3   # 160
LOG_LOCAL5   = 21 << 3   # 168
LOG_LOCAL6   = 22 << 3   # 176
LOG_LOCAL7   = 23 << 3   # 184


# ---------------------------------------------------------------------------
# Mask helpers
# ---------------------------------------------------------------------------
def LOG_MASK(pri):
    """Bit mask for the given priority level."""
    return 1 << pri


def LOG_UPTO(pri):
    """Bit mask for priorities <= pri (inclusive)."""
    return (1 << (pri + 1)) - 1


# ---------------------------------------------------------------------------
# Module-level state set up by openlog()
# ---------------------------------------------------------------------------
_S_IDENT = None
_S_LOGOPT = 0
_S_FACILITY = LOG_USER
_S_LOGMASK = 0xFF        # all priorities enabled by default
_S_SOCK = None
_S_SOCK_PATH = None
_S_OPENED = False

# Candidate Unix-domain syslog endpoints in priority order.
_SYSLOG_PATHS = ('/dev/log', '/var/run/syslog', '/var/run/log')


def _close_sock():
    global _S_SOCK, _S_SOCK_PATH
    if _S_SOCK is not None:
        try:
            _S_SOCK.close()
        except Exception:
            pass
    _S_SOCK = None
    _S_SOCK_PATH = None


def _open_sock():
    """Try to open a connection to a local syslogd. Best-effort; never raises."""
    global _S_SOCK, _S_SOCK_PATH

    # Prefer a Unix-domain datagram socket — this is what BSD syslog uses.
    af_unix = getattr(_socket, 'AF_UNIX', None)
    if af_unix is not None:
        for path in _SYSLOG_PATHS:
            try:
                if not _os.path.exists(path):
                    continue
            except Exception:
                continue
            for stype in (_socket.SOCK_DGRAM, _socket.SOCK_STREAM):
                try:
                    s = _socket.socket(af_unix, stype)
                    s.connect(path)
                    _S_SOCK = s
                    _S_SOCK_PATH = path
                    return True
                except Exception:
                    try:
                        s.close()
                    except Exception:
                        pass
                    continue

    # No reachable syslogd — leave socket as None; syslog() will be a no-op.
    return False


def _ensure_open():
    """Lazily open the connection if openlog() was never explicitly called."""
    global _S_OPENED
    if _S_OPENED:
        return
    _S_OPENED = True
    _open_sock()


def _default_ident():
    """Reasonable ident string when openlog() wasn't given one."""
    try:
        argv = getattr(_sys, 'argv', None) or []
        if argv:
            base = _os.path.basename(argv[0]) if argv[0] else ''
            if base:
                return base
    except Exception:
        pass
    return 'python'


def _format_timestamp(t):
    """RFC 3164 timestamp: 'Mmm dd hh:mm:ss' in local time."""
    months = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    lt = _time.localtime(t)
    return '%s %2d %02d:%02d:%02d' % (
        months[lt.tm_mon - 1], lt.tm_mday,
        lt.tm_hour, lt.tm_min, lt.tm_sec,
    )


# ---------------------------------------------------------------------------
# Public API: openlog / closelog / setlogmask / syslog
# ---------------------------------------------------------------------------
def openlog(ident=None, logopt=0, facility=LOG_USER):
    """Initialize subsequent calls to syslog()."""
    global _S_IDENT, _S_LOGOPT, _S_FACILITY, _S_OPENED

    if ident is not None and not isinstance(ident, str):
        raise TypeError('ident must be a string or None')
    if not isinstance(logopt, int):
        raise TypeError('logopt must be an integer')
    if not isinstance(facility, int):
        raise TypeError('facility must be an integer')

    _S_IDENT = ident
    _S_LOGOPT = logopt
    _S_FACILITY = facility

    _close_sock()
    _S_OPENED = True
    if logopt & LOG_NDELAY:
        _open_sock()


def closelog():
    """Close the syslog connection. Resets module state to defaults."""
    global _S_IDENT, _S_LOGOPT, _S_FACILITY, _S_LOGMASK, _S_OPENED
    _close_sock()
    _S_IDENT = None
    _S_LOGOPT = 0
    _S_FACILITY = LOG_USER
    _S_LOGMASK = 0xFF
    _S_OPENED = False


def setlogmask(maskpri):
    """Set the priority mask. A maskpri of 0 leaves the mask unchanged.
    Returns the previous mask."""
    global _S_LOGMASK
    if not isinstance(maskpri, int):
        raise TypeError('mask must be an integer')
    prev = _S_LOGMASK
    if maskpri != 0:
        _S_LOGMASK = maskpri
    return prev


def syslog(*args):
    """syslog(priority, message) or syslog(message) with default LOG_INFO."""
    if len(args) == 1:
        priority = LOG_INFO
        message = args[0]
    elif len(args) == 2:
        priority, message = args
    else:
        raise TypeError(
            'syslog() takes 1 or 2 positional arguments (got %d)' % len(args)
        )

    if not isinstance(priority, int):
        raise TypeError('priority must be an integer')
    if not isinstance(message, str):
        raise TypeError('message must be a string')

    severity = priority & 0x07
    if not (_S_LOGMASK & LOG_MASK(severity)):
        return

    if (priority & ~0x07) == 0:
        prival = _S_FACILITY | severity
    else:
        prival = priority

    _ensure_open()

    ident = _S_IDENT if _S_IDENT is not None else _default_ident()
    timestamp = _format_timestamp(_time.time())

    if _S_LOGOPT & LOG_PID:
        tag = '%s[%d]:' % (ident, _os.getpid())
    else:
        tag = '%s:' % ident

    line = '<%d>%s %s %s' % (prival, timestamp, tag, message)

    if _S_SOCK is not None:
        try:
            _S_SOCK.send(line.encode('utf-8', 'replace'))
        except Exception:
            try:
                _close_sock()
                _open_sock()
                if _S_SOCK is not None:
                    _S_SOCK.send(line.encode('utf-8', 'replace'))
            except Exception:
                pass

    if _S_LOGOPT & LOG_PERROR:
        try:
            _sys.stderr.write(line + '\n')
            _sys.stderr.flush()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Invariant probe functions
# ---------------------------------------------------------------------------
def syslog2_constants():
    """All standard syslog constants are present and correctly typed."""
    severities = (LOG_EMERG, LOG_ALERT, LOG_CRIT, LOG_ERR,
                  LOG_WARNING, LOG_NOTICE, LOG_INFO, LOG_DEBUG)
    if list(severities) != [0, 1, 2, 3, 4, 5, 6, 7]:
        return False
    facilities = (LOG_KERN, LOG_USER, LOG_MAIL, LOG_DAEMON,
                  LOG_AUTH, LOG_LPR, LOG_LOCAL0, LOG_LOCAL7)
    if not all(isinstance(f, int) and f >= 0 for f in facilities):
        return False
    if LOG_USER != 8 or LOG_LOCAL0 != 128 or LOG_LOCAL7 != 184:
        return False
    options = (LOG_PID, LOG_CONS, LOG_NDELAY, LOG_NOWAIT, LOG_PERROR)
    if not all(isinstance(o, int) and o > 0 for o in options):
        return False
    return True


def syslog2_priority_names():
    """The eight severity levels are strictly ordered EMERG < ... < DEBUG."""
    ordered = (LOG_EMERG, LOG_ALERT, LOG_CRIT, LOG_ERR,
               LOG_WARNING, LOG_NOTICE, LOG_INFO, LOG_DEBUG)
    for i in range(len(ordered) - 1):
        if ordered[i] >= ordered[i + 1]:
            return False
    if LOG_MASK(LOG_INFO) != (1 << LOG_INFO):
        return False
    if LOG_UPTO(LOG_DEBUG) != 0xFF:
        return False
    return True


def syslog2_syslog():
    """syslog(), openlog(), closelog(), setlogmask() are callable; smoke test."""
    if not (callable(syslog) and callable(openlog)
            and callable(closelog) and callable(setlogmask)):
        return False
    try:
        prev = setlogmask(0)
        setlogmask(LOG_UPTO(LOG_DEBUG))
        openlog('theseus-test', LOG_PID, LOG_USER)
        syslog(LOG_INFO, 'theseus invariant probe')
        syslog('default-priority message')
        closelog()
        setlogmask(prev if prev else 0xFF)
    except Exception:
        return False
    return True


__all__ = [
    'LOG_EMERG', 'LOG_ALERT', 'LOG_CRIT', 'LOG_ERR',
    'LOG_WARNING', 'LOG_NOTICE', 'LOG_INFO', 'LOG_DEBUG',
    'LOG_PID', 'LOG_CONS', 'LOG_ODELAY', 'LOG_NDELAY',
    'LOG_NOWAIT', 'LOG_PERROR',
    'LOG_KERN', 'LOG_USER', 'LOG_MAIL', 'LOG_DAEMON', 'LOG_AUTH',
    'LOG_SYSLOG', 'LOG_LPR', 'LOG_NEWS', 'LOG_UUCP', 'LOG_CRON',
    'LOG_AUTHPRIV', 'LOG_FTP',
    'LOG_LOCAL0', 'LOG_LOCAL1', 'LOG_LOCAL2', 'LOG_LOCAL3',
    'LOG_LOCAL4', 'LOG_LOCAL5', 'LOG_LOCAL6', 'LOG_LOCAL7',
    'LOG_MASK', 'LOG_UPTO',
    'openlog', 'closelog', 'setlogmask', 'syslog',
    'syslog2_constants', 'syslog2_priority_names', 'syslog2_syslog',
]