"""Clean-room implementation of theseus_xml_cr.

This is a namespace-style stub package providing the three invariant
functions required by the Theseus verification harness. No third-party
or replaced-package imports are used.
"""

import os as _os
import sys as _sys


__all__ = ["xml2_package", "xml2_name", "xml2_path"]


def xml2_package():
    """Return True — confirms this module is a proper Python package.

    A package has a ``__path__`` attribute and a dotted ``__name__``
    when imported as part of a namespace, or simply a non-empty name
    when loaded standalone. We assert both that this module is loaded
    in ``sys.modules`` and that it carries the package marker.
    """
    mod_name = __name__
    if mod_name in _sys.modules:
        mod = _sys.modules[mod_name]
        if hasattr(mod, "__path__"):
            return True
    # Fallback: presence of __path__ in our own globals indicates package
    return "__path__" in globals()


def xml2_name():
    """Return True — confirms the package name is well-formed."""
    name = __name__
    if not isinstance(name, str):
        return False
    if not name:
        return False
    # Validate identifier characters (letters, digits, underscores, dots)
    for ch in name:
        if not (ch.isalnum() or ch == "_" or ch == "."):
            return False
    return True


def xml2_path():
    """Return True — confirms the package has a resolvable filesystem path."""
    path_attr = globals().get("__path__", None)
    if path_attr is None:
        return False
    # __path__ is typically a list-like of directory strings
    try:
        entries = list(path_attr)
    except TypeError:
        return False
    if not entries:
        return False
    for entry in entries:
        if not isinstance(entry, str):
            return False
        if not _os.path.isdir(entry):
            return False
    return True