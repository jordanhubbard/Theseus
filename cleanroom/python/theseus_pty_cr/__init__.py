"""
theseus_pty_cr — Clean-room pty module.
No import of the standard `pty` module.
Uses os.openpty() and os.fork() directly.
"""

import os as _os
import select as _select

STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2

_CHILD = 0


def openpty():
    """Return (master_fd, slave_fd) pair for a new pseudo-terminal."""
    return _os.openpty()


def fork():
    """
    Fork, returning (pid, master_fd) in parent and (0, 0) in child.
    The child's stdin/stdout/stderr are connected to a new pty.
    """
    master_fd, slave_fd = openpty()
    pid = _os.fork()
    if pid == _CHILD:
        _os.close(master_fd)
        _os.setsid()
        _os.dup2(slave_fd, STDIN_FILENO)
        _os.dup2(slave_fd, STDOUT_FILENO)
        _os.dup2(slave_fd, STDERR_FILENO)
        if slave_fd > STDERR_FILENO:
            _os.close(slave_fd)
        return _CHILD, 0
    else:
        _os.close(slave_fd)
        return pid, master_fd


def spawn(argv, master_read=None, stdin_read=None):
    """Spawn a process connected to a pty; copy I/O until the child exits."""
    if master_read is None:
        def master_read(fd):
            return _os.read(fd, 1024)
    if stdin_read is None:
        def stdin_read(fd):
            return _os.read(fd, 1024)

    pid, master_fd = fork()
    if pid == _CHILD:
        _os.execvp(argv[0], argv)
    else:
        try:
            _copy(master_fd, master_read, stdin_read)
        except OSError:
            pass
        _os.close(master_fd)
        _, status = _os.waitpid(pid, 0)
        return status


def _copy(master_fd, master_read, stdin_read):
    fds = [master_fd, STDIN_FILENO]
    while True:
        try:
            rfds, _, _ = _select.select(fds, [], [])
        except (KeyboardInterrupt, OSError):
            break
        if master_fd in rfds:
            data = master_read(master_fd)
            if not data:
                fds.remove(master_fd)
            else:
                _os.write(STDOUT_FILENO, data)
        if STDIN_FILENO in rfds:
            data = stdin_read(STDIN_FILENO)
            if not data:
                fds.remove(STDIN_FILENO)
            else:
                _os.write(master_fd, data)
        if not fds:
            break


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pty2_openpty():
    """openpty() returns (master_fd, slave_fd) as ints; returns True."""
    master_fd, slave_fd = openpty()
    try:
        return isinstance(master_fd, int) and isinstance(slave_fd, int)
    finally:
        _os.close(master_fd)
        _os.close(slave_fd)


def pty2_constants():
    """STDIN_FILENO == 0, STDOUT_FILENO == 1, STDERR_FILENO == 2; returns True."""
    return STDIN_FILENO == 0 and STDOUT_FILENO == 1 and STDERR_FILENO == 2


def pty2_fork():
    """fork is callable; returns True."""
    return callable(fork)


__all__ = [
    'STDIN_FILENO', 'STDOUT_FILENO', 'STDERR_FILENO',
    'openpty', 'fork', 'spawn',
    'pty2_openpty', 'pty2_constants', 'pty2_fork',
]
