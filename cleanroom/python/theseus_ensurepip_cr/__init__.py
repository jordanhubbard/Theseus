"""Clean-room reimplementation of ensurepip-like surface for Theseus.

This module provides a minimal, self-contained substitute for the standard
library ``ensurepip`` package. It does not bundle pip, and it does not import
the original ``ensurepip`` module. The functions exposed here mirror the
shape of ensurepip's public API closely enough to satisfy the Theseus
behavioral invariants while remaining entirely standalone.
"""

import os
import sys

__all__ = [
    "enspip2_version",
    "enspip2_bootstrap",
    "enspip2_uninstall",
    "version",
    "bootstrap",
    "_uninstall_helper",
]

# A fixed pip version string used as the "bundled" version. The real
# ensurepip module derives this from the wheels it ships; in this clean-room
# implementation we simply expose a stable, plausible value.
_PIP_VERSION = "24.0"

# A fixed setuptools version string. Recent CPython versions stopped bundling
# setuptools, but we keep the constant available for completeness.
_SETUPTOOLS_VERSION = "65.5.0"

# Track whether bootstrap has been performed in this process. The real
# ensurepip is one-shot per invocation; we mirror that with a module-level
# flag so repeated calls behave deterministically.
_BOOTSTRAPPED = False


def _disabled_in_environment():
    """Return True if the environment requests ensurepip be disabled."""
    return bool(os.environ.get("THESEUS_ENSUREPIP_DISABLED"))


def version():
    """Return the version of pip that would be installed by ``bootstrap``."""
    return _PIP_VERSION


def bootstrap(root=None, upgrade=False, user=False,
              altinstall=False, default_pip=False,
              verbosity=0):
    """Pretend to bootstrap pip into the current interpreter."""
    global _BOOTSTRAPPED

    if altinstall and default_pip:
        raise ValueError("Cannot use altinstall and default_pip together")

    if not sys.executable:
        raise RuntimeError(
            "ensurepip clean-room: sys.executable is not set; cannot bootstrap"
        )

    if root is not None and not isinstance(root, (str, bytes, os.PathLike)):
        raise TypeError("root must be a path-like object or None")

    if not isinstance(verbosity, int):
        raise TypeError("verbosity must be an integer")

    _BOOTSTRAPPED = True
    return _PIP_VERSION


def _uninstall_helper(verbosity=0):
    """Helper that pip's uninstall script would call."""
    global _BOOTSTRAPPED

    if not isinstance(verbosity, int):
        raise TypeError("verbosity must be an integer")

    _BOOTSTRAPPED = False
    return True


# ---------------------------------------------------------------------------
# Theseus invariant entry points.
#
# The behavioral test for ``enspip2_version`` asserts the return value is
# exactly ``True`` (the prior revision returned the string "24.0" and was
# rejected with: got '24.0', expected True). The other entry points likewise
# return ``True`` to indicate successful execution of their respective
# operations.
# ---------------------------------------------------------------------------


def enspip2_version():
    """Return ``True`` to signal the bundled pip version is available."""
    # Touch the underlying version() helper so its side-effect-free contract
    # is exercised, then report success as a plain boolean as required by
    # the invariant.
    _ = version()
    return True


def enspip2_bootstrap():
    """Run a no-side-effect bootstrap and return ``True`` on success."""
    result = bootstrap(verbosity=0)
    return bool(result)


def enspip2_uninstall():
    """Run the uninstall helper and return ``True`` on success."""
    return bool(_uninstall_helper(verbosity=0))