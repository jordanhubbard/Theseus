"""Clean-room stub for the turtledemo namespace package.

This module provides a minimal namespace-style placeholder that exposes
the same package-shape predicates expected by the Theseus invariant
suite without importing or re-exporting anything from the original
`turtledemo` package.
"""

import os as _os
import sys as _sys

# Package metadata — declared locally so we never need to consult the
# original turtledemo package.
__version__ = "0.0.1"
__all__ = [
    "turtledemo2_package",
    "turtledemo2_name",
    "turtledemo2_path",
]

# A synthetic search path for this namespace stub.  We anchor it at the
# directory holding this file so behaviour mirrors a real package
# without depending on any external resource.
_PKG_DIR = _os.path.dirname(_os.path.abspath(__file__))
__path__ = [_PKG_DIR]
__name__ = __name__  # explicit, so the invariants below have a target


def turtledemo2_package():
    """Return True when this module behaves like a package.

    A package, by Python's own definition, is a module that carries a
    ``__path__`` attribute.  We assert that here without consulting the
    original turtledemo package.
    """
    mod = _sys.modules.get(__name__)
    if mod is None:
        return False
    return hasattr(mod, "__path__") and isinstance(getattr(mod, "__path__"), list)


def turtledemo2_name():
    """Return True when the module name is well-formed and non-empty."""
    name = __name__
    return isinstance(name, str) and len(name) > 0


def turtledemo2_path():
    """Return True when the package search path is a list of strings."""
    if not isinstance(__path__, list):
        return False
    if len(__path__) == 0:
        return False
    return all(isinstance(p, str) for p in __path__)