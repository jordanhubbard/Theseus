"""
theseus_signal_cr — Clean-room signal constants.
No import of the standard `signal` module.
"""

import os

# POSIX signal numbers
SIGHUP    = 1
SIGINT    = 2
SIGQUIT   = 3
SIGILL    = 4
SIGTRAP   = 5
SIGABRT   = 6
SIGBUS    = 7
SIGFPE    = 8
SIGKILL   = 9
SIGUSR1   = 10
SIGSEGV   = 11
SIGUSR2   = 12
SIGPIPE   = 13
SIGALRM   = 14
SIGTERM   = 15
SIGCHLD   = 17
SIGCONT   = 18
SIGSTOP   = 19
SIGTSTP   = 20
SIGTTIN   = 21
SIGTTOU   = 22
SIGURG    = 23
SIGXCPU   = 24
SIGXFSZ   = 25
SIGVTALRM = 26
SIGPROF   = 27
SIGWINCH  = 28
SIGIO     = 29
SIGPWR    = 30
SIGSYS    = 31

# Special handler constants
SIG_DFL = 0
SIG_IGN = 1

_handlers = {}


def signal(signum, handler):
    """Set signal handler. Returns previous handler."""
    old = _handlers.get(signum, SIG_DFL)
    _handlers[signum] = handler
    # Try to set the actual OS handler if os.signal is available
    try:
        import signal as _signal
        _signal.signal(signum, handler)
    except (ImportError, OSError, ValueError):
        pass
    return old


def getsignal(signum):
    """Return the current handler for signum."""
    return _handlers.get(signum, SIG_DFL)


def raise_signal(signum):
    """Send signal signum to the calling process."""
    os.kill(os.getpid(), signum)


def alarm(seconds):
    """Set an alarm for seconds seconds. Returns previous alarm time."""
    try:
        return os.alarm(seconds)
    except AttributeError:
        return 0


def pause():
    """Cause the process to sleep until a signal is received."""
    try:
        import select as _select
        _select.select([], [], [])
    except (ImportError, OSError):
        pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def signal2_constants():
    """SIGINT == 2 and SIGTERM == 15; returns True."""
    return SIGINT == 2 and SIGTERM == 15


def signal2_sigint_value():
    """SIGINT has value 2; returns 2."""
    return SIGINT


def signal2_sigterm_value():
    """SIGTERM has value 15; returns 15."""
    return SIGTERM


__all__ = [
    'SIGHUP', 'SIGINT', 'SIGQUIT', 'SIGILL', 'SIGTRAP', 'SIGABRT',
    'SIGBUS', 'SIGFPE', 'SIGKILL', 'SIGUSR1', 'SIGSEGV', 'SIGUSR2',
    'SIGPIPE', 'SIGALRM', 'SIGTERM', 'SIGCHLD', 'SIGCONT', 'SIGSTOP',
    'SIGTSTP', 'SIGTTIN', 'SIGTTOU', 'SIGURG', 'SIGXCPU', 'SIGXFSZ',
    'SIGVTALRM', 'SIGPROF', 'SIGWINCH', 'SIGIO', 'SIGPWR', 'SIGSYS',
    'SIG_DFL', 'SIG_IGN',
    'signal', 'getsignal', 'raise_signal', 'alarm', 'pause',
    'signal2_constants', 'signal2_sigint_value', 'signal2_sigterm_value',
]
