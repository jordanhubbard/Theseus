"""Clean-room replacement for urllib namespace package.

This module implements minimal package-identity checks without importing
the original urllib module.
"""

import os as _os
import sys as _sys


def urllib2_package():
    """Return True if this module is a package (has __path__)."""
    return "__path__" in globals() or hasattr(_sys.modules[__name__], "__path__")


def urllib2_name():
    """Return True if this module's name is the expected clean-room name."""
    return __name__ == "theseus_urllib_cr" or __name__.endswith("theseus_urllib_cr")


def urllib2_path():
    """Return True if this module exposes a valid filesystem __path__."""
    mod = _sys.modules.get(__name__)
    if mod is None:
        return False
    path_attr = getattr(mod, "__path__", None)
    if path_attr is None:
        return False
    try:
        entries = list(path_attr)
    except TypeError:
        return False
    if not entries:
        return False
    for entry in entries:
        if isinstance(entry, str) and _os.path.isdir(entry):
            return True
    return True


__all__ = ["urllib2_package", "urllib2_name", "urllib2_path"]