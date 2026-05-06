"""Clean-room implementation of theseus_xmlrpc_cr.

This is a namespace-style stub package providing minimal invariant
functions. It does NOT import or wrap the original xmlrpc package.
"""

import os as _os


__all__ = ["xmlrpc2_package", "xmlrpc2_name", "xmlrpc2_path"]


_PACKAGE_NAME = "theseus_xmlrpc_cr"


def xmlrpc2_package():
    """Return True — this module is a package (has __path__).

    A Python package is identified by having a ``__path__`` attribute.
    This function verifies that this module is structured as a package.
    """
    return "__path__" in globals() and isinstance(__path__, list)


def xmlrpc2_name():
    """Return True — the package name matches the expected name."""
    return __name__ == _PACKAGE_NAME


def xmlrpc2_path():
    """Return True — the package's __path__ points to an existing directory."""
    try:
        paths = list(__path__)
    except NameError:
        return False
    if not paths:
        return False
    for p in paths:
        if not isinstance(p, str):
            return False
        if not _os.path.isdir(p):
            return False
    return True