"""Clean-room posix subset for Theseus invariants."""

import os


def getcwd():
    return os.getcwd()


def stat(path):
    return os.stat(path)


def urandom(n):
    return os.urandom(n)


def posix2_getcwd():
    cwd = getcwd()
    return isinstance(cwd, str) and len(cwd) > 0


def posix2_stat():
    st = stat("/")
    return hasattr(st, "st_mode") and hasattr(st, "st_size")


def posix2_urandom():
    data = urandom(8)
    return isinstance(data, bytes) and len(data) == 8


__all__ = ["getcwd", "stat", "urandom", "posix2_getcwd", "posix2_stat", "posix2_urandom"]
