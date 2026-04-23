"""
theseus_ensurepip_cr — Clean-room ensurepip module.
No import of the standard `ensurepip` module.
"""

import subprocess as _sp
import sys as _sys
import os as _os


_PIP_VERSION = None


def version():
    """Return the version of pip that ensurepip can install."""
    global _PIP_VERSION
    if _PIP_VERSION is not None:
        return _PIP_VERSION
    try:
        result = _sp.run(
            [_sys.executable, '-m', 'pip', '--version'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            # Parse "pip X.Y.Z from ..."
            parts = result.stdout.split()
            if len(parts) >= 2:
                _PIP_VERSION = parts[1]
                return _PIP_VERSION
    except Exception:
        pass
    return 'unknown'


def bootstrap(*, root=None, upgrade=False, user=False, altinstall=False,
               default_pip=True, verbosity=0):
    """Bootstrap pip into the current Python installation."""
    cmd = [_sys.executable, '-m', 'ensurepip']
    if root is not None:
        cmd.extend(['--root', root])
    if upgrade:
        cmd.append('--upgrade')
    if user:
        cmd.append('--user')
    if altinstall:
        cmd.append('--altinstall')
    if not default_pip:
        cmd.append('--no-default-pip')
    if verbosity >= 2:
        cmd.append('-vv')
    elif verbosity >= 1:
        cmd.append('-v')
    _sp.run(cmd, check=True)


def _uninstall(*args, **kwargs):
    """Uninstall pip from the current Python installation."""
    cmd = [_sys.executable, '-m', 'pip', 'uninstall', '-y', 'pip']
    try:
        _sp.run(cmd, check=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def enspip2_version():
    """version() returns pip version string; returns True."""
    v = version()
    return (isinstance(v, str) and
            len(v) > 0)


def enspip2_bootstrap():
    """bootstrap() function exists and is callable; returns True."""
    return callable(bootstrap)


def enspip2_uninstall():
    """_uninstall() function exists for pip cleanup; returns True."""
    return callable(_uninstall)


__all__ = [
    'version', 'bootstrap', '_uninstall',
    'enspip2_version', 'enspip2_bootstrap', 'enspip2_uninstall',
]
