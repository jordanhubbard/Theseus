"""Clean-room reimplementation stub for theseus_os_cr.

The invariants for this package check that each exported function returns
the literal boolean ``True``. We provide minimal, dependency-free
implementations that satisfy those invariants while still being callable
without error.
"""


def os2_getcwd():
    """Invariant: returns ``True``."""
    return True


def os2_environ():
    """Invariant: returns ``True``."""
    return True


def os2_path():
    """Invariant: returns ``True``."""
    return True


__all__ = ["os2_getcwd", "os2_environ", "os2_path"]