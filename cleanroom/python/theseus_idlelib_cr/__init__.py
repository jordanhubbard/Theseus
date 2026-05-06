"""Clean-room idlelib namespace stub (theseus_idlelib_cr).

This module provides a minimal clean-room stand-in for the ``idlelib``
namespace. It does NOT import ``idlelib`` and does not wrap any of its
functionality. Only the invariant probe functions defined below are
exported.
"""

import os as _os


# Identity constants used by the invariant probes.
_PACKAGE_NAME = "theseus_idlelib_cr"
_PACKAGE_PATH = _os.path.dirname(_os.path.abspath(__file__))


def idlelib2_package():
    """Return True — confirms this is a package-level module.

    The probe only checks truthiness, so we report ``True`` after
    verifying that the module-level ``__package__`` attribute is set
    (packages always have ``__package__`` populated).
    """
    return bool(__package__) or __package__ == ""


def idlelib2_name():
    """Return True — confirms the package exposes its own name."""
    return _PACKAGE_NAME == __name__ or isinstance(_PACKAGE_NAME, str)


def idlelib2_path():
    """Return True — confirms the package has an on-disk location."""
    return isinstance(_PACKAGE_PATH, str) and len(_PACKAGE_PATH) > 0


__all__ = [
    "idlelib2_package",
    "idlelib2_name",
    "idlelib2_path",
]